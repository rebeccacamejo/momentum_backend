"""
Security tests for the Momentum backend.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import jwt
from datetime import datetime, timedelta


@pytest.mark.security
def test_jwt_token_validation(client: TestClient):
    """Test JWT token validation."""
    # Test with no token
    response = client.get("/auth/user")
    assert response.status_code == 403

    # Test with invalid token
    response = client.get("/auth/user", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401

    # Test with malformed token
    response = client.get("/auth/user", headers={"Authorization": "InvalidFormat"})
    assert response.status_code == 403


@pytest.mark.security
def test_expired_jwt_token(client: TestClient):
    """Test handling of expired JWT tokens."""
    # Create an expired token
    expired_payload = {
        "sub": "test-user-id",
        "email": "test@example.com",
        "exp": datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
        "iat": datetime.utcnow() - timedelta(hours=2),
        "aud": "authenticated"
    }
    expired_token = jwt.encode(expired_payload, "test-jwt-secret", algorithm="HS256")

    response = client.get("/auth/user", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.security
def test_jwt_token_tampering(client: TestClient):
    """Test detection of tampered JWT tokens."""
    # Create a valid token
    payload = {
        "sub": "test-user-id",
        "email": "test@example.com",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "aud": "authenticated"
    }
    valid_token = jwt.encode(payload, "test-jwt-secret", algorithm="HS256")

    # Tamper with the token
    tampered_token = valid_token[:-10] + "tampered123"

    response = client.get("/auth/user", headers={"Authorization": f"Bearer {tampered_token}"})
    assert response.status_code == 401


@pytest.mark.security
def test_sql_injection_protection(client: TestClient, mock_supabase, auth_headers):
    """Test protection against SQL injection attempts."""
    # Test SQL injection in organization ID
    malicious_org_id = "'; DROP TABLE organizations; --"
    response = client.get(f"/organizations/{malicious_org_id}", headers=auth_headers)
    # Should return 403 (access denied) or 404, not 500 (server error from SQL injection)
    assert response.status_code in [403, 404]

    # Test SQL injection in query parameters
    response = client.get("/deliverables?id='; DROP TABLE deliverables; --")
    # Should handle gracefully
    assert response.status_code in [200, 400, 422]


@pytest.mark.security
def test_file_upload_security(client: TestClient):
    """Test file upload security measures."""
    # Test oversized file (simulate)
    large_content = b"x" * (50 * 1024 * 1024)  # 50MB
    files = {"file": ("large.wav", large_content, "audio/wav")}
    data = {"client_name": "Security Test"}

    # Should handle gracefully (may timeout or reject)
    response = client.post("/upload", files=files, data=data)
    assert response.status_code in [200, 400, 413, 422]

    # Test malicious file type
    malicious_content = b"<?php system($_GET['cmd']); ?>"
    files = {"file": ("malicious.php", malicious_content, "application/x-php")}

    response = client.post("/upload", files=files, data=data)
    # Should reject or handle safely
    assert response.status_code in [200, 400, 415, 422]


@pytest.mark.security
def test_logo_upload_security(client: TestClient):
    """Test logo upload security measures."""
    # Test executable file disguised as image
    malicious_content = b"\x89PNG\r\n\x1a\n<?php system($_GET['cmd']); ?>"
    files = {"file": ("malicious.png", malicious_content, "image/png")}

    response = client.post("/brand/logo", files=files)
    # Should handle safely
    assert response.status_code in [200, 400, 415]

    # Test script injection in filename
    script_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    files = {"file": ("<script>alert('xss')</script>.png", script_content, "image/png")}

    response = client.post("/brand/logo", files=files)
    # Should sanitize filename or reject
    assert response.status_code in [200, 400]


@pytest.mark.security
def test_xss_protection(client: TestClient, mock_supabase):
    """Test XSS protection in user inputs."""
    # Test XSS in client name
    xss_payload = "<script>alert('xss')</script>"

    response = client.post(
        "/generate",
        json={
            "transcript": "Normal transcript",
            "client_name": xss_payload,
            "template_type": "action_plan"
        }
    )

    if response.status_code == 200:
        # Check that XSS payload is escaped in response
        response_html = response.json().get("html", "")
        assert "<script>" not in response_html or "&lt;script&gt;" in response_html


@pytest.mark.security
def test_directory_traversal_protection(client: TestClient, auth_headers):
    """Test protection against directory traversal attacks."""
    # Test path traversal in deliverable ID
    malicious_id = "../../../etc/passwd"
    response = client.get(f"/deliverables/{malicious_id}", headers=auth_headers)
    assert response.status_code in [404, 400]

    # Test path traversal in PDF generation
    response = client.get(f"/deliverables/{malicious_id}/pdf", headers=auth_headers)
    assert response.status_code in [404, 400]


@pytest.mark.security
def test_rate_limiting_simulation(client: TestClient):
    """Simulate rate limiting tests."""
    # Test rapid requests to magic link endpoint
    responses = []
    for i in range(10):
        response = client.post(
            "/auth/magic-link",
            json={"email": f"test{i}@example.com"}
        )
        responses.append(response.status_code)

    # Should handle gracefully (may implement rate limiting in production)
    assert all(code in [200, 400, 429] for code in responses)


@pytest.mark.security
def test_cors_headers(client: TestClient):
    """Test CORS configuration."""
    response = client.options("/")
    # Should have CORS headers configured
    assert "access-control-allow-origin" in [h.lower() for h in response.headers.keys()]


@pytest.mark.security
def test_information_disclosure(client: TestClient):
    """Test for information disclosure vulnerabilities."""
    # Test 404 responses don't leak information
    response = client.get("/nonexistent-endpoint")
    assert response.status_code == 404
    assert "stack trace" not in response.text.lower()
    assert "internal server error" not in response.text.lower()

    # Test error responses don't expose sensitive data
    response = client.post("/generate", json={})  # Invalid request
    if response.status_code >= 400:
        error_detail = response.json().get("detail", "")
        assert "password" not in error_detail.lower()
        assert "secret" not in error_detail.lower()
        assert "key" not in error_detail.lower()


@pytest.mark.security
def test_authorization_bypass_attempts(client: TestClient, mock_supabase):
    """Test authorization bypass attempts."""
    # Test accessing protected endpoints without proper authorization
    protected_endpoints = [
        "/auth/user",
        "/auth/signout",
        "/organizations",
        "/organizations/test-org-id",
        "/organizations/test-org-id/members"
    ]

    for endpoint in protected_endpoints:
        # No authorization
        response = client.get(endpoint)
        assert response.status_code in [401, 403]

        # Invalid authorization
        response = client.get(endpoint, headers={"Authorization": "Bearer fake-token"})
        assert response.status_code in [401, 403]


@pytest.mark.security
def test_organization_access_control(client: TestClient, mock_supabase, auth_headers):
    """Test organization-level access control."""
    # Mock no membership in organization
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(data=None)

    # Try to access organization without membership
    response = client.get("/organizations/unauthorized-org", headers=auth_headers)
    assert response.status_code == 403

    # Try to update organization without proper role
    mock_member = {
        "id": "member-id",
        "user_id": "test-user-id",
        "organization_id": "test-org",
        "role": "viewer"  # Insufficient permissions
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(data=mock_member)

    response = client.put("/organizations/test-org", headers=auth_headers, json={"name": "Hacked Org"})
    assert response.status_code == 403


@pytest.mark.security
def test_input_validation(client: TestClient):
    """Test input validation and sanitization."""
    # Test extremely long inputs
    long_string = "x" * 10000
    response = client.post(
        "/generate",
        json={
            "transcript": long_string,
            "client_name": long_string,
            "template_type": "action_plan"
        }
    )
    # Should handle gracefully
    assert response.status_code in [200, 400, 422]

    # Test invalid email formats
    invalid_emails = [
        "not-an-email",
        "@domain.com",
        "user@",
        "user@domain",
        "user..user@domain.com"
    ]

    for email in invalid_emails:
        response = client.post("/auth/magic-link", json={"email": email})
        assert response.status_code == 422  # Validation error


@pytest.mark.security
def test_content_type_validation(client: TestClient):
    """Test content type validation."""
    # Test uploading with wrong content type
    valid_audio = b"RIFF\x00\x00\x00\x00WAVE"
    files = {"file": ("test.wav", valid_audio, "image/png")}  # Wrong content type
    data = {"client_name": "Test"}

    response = client.post("/upload", files=files, data=data)
    # Should handle content type mismatch
    assert response.status_code in [200, 400, 415]


@pytest.mark.security
def test_session_security(client: TestClient, mock_supabase):
    """Test session security measures."""
    # Test that sessions are properly invalidated on logout
    # This would be tested more thoroughly with real Supabase integration

    # Mock successful login
    mock_user = {"id": "test-user", "email": "test@example.com"}
    mock_supabase.auth.set_session.return_value = Mock(user=mock_user)

    # Simulate login
    login_response = client.post(
        "/auth/callback",
        data={
            "access_token": "test-token",
            "refresh_token": "test-refresh",
            "expires_in": 3600,
            "token_type": "bearer"
        }
    )
    assert login_response.status_code == 200

    # Test session handling
    mock_supabase.auth.sign_out.return_value = None
    logout_response = client.post("/auth/signout", headers={"Authorization": "Bearer test-token"})
    assert logout_response.status_code == 200
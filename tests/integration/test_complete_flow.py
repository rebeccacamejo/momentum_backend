"""
Integration tests for complete deliverable creation flow.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import io


@pytest.mark.integration
@pytest.mark.slow
def test_complete_deliverable_creation_flow(client: TestClient, mock_supabase, mock_openai, sample_audio_file):
    """Test the complete flow from file upload to PDF generation."""
    # Step 1: Upload and process audio file
    mock_openai.audio.transcriptions.create.return_value = Mock(
        text="This is a comprehensive test of the deliverable creation system."
    )

    mock_openai.chat.completions.create.return_value = Mock(
        choices=[Mock(
            message=Mock(
                content='{"summary": "Test meeting summary", "action_items": [{"task": "Complete testing", "owner": "Test Team", "due_date": "2023-12-31"}], "key_insights": ["Testing is important", "Quality matters"]}'
            )
        )]
    )

    # Mock deliverable save
    test_deliverable_id = "test-deliverable-123"
    mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock(
        data=[{"id": test_deliverable_id}]
    )

    with patch("utils.deliverables.render_deliverable") as mock_render:
        mock_render.return_value = "<html><body><h1>Test Deliverable</h1><p>Content here</p></body></html>"

        # Upload file
        files = {"file": ("test.mp3", sample_audio_file, "audio/mpeg")}
        data = {
            "client_name": "Integration Test Client",
            "primary_color": "#2A3EB1",
            "secondary_color": "#4C6FE7",
            "template_type": "action_plan"
        }

        upload_response = client.post("/upload", files=files, data=data)

    assert upload_response.status_code == 200
    upload_data = upload_response.json()
    assert "id" in upload_data
    assert upload_data["html"] is not None
    deliverable_id = upload_data["id"]

    # Step 2: Retrieve the deliverable
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
        data={"id": deliverable_id, "html": upload_data["html"], "client_name": "Integration Test Client"}
    )

    get_response = client.get(f"/deliverables/{deliverable_id}")
    assert get_response.status_code == 200
    assert "Test Deliverable" in get_response.text

    # Step 3: Generate PDF
    with patch("main.get_deliverable_from_db") as mock_get_deliverable:
        mock_get_deliverable.return_value = {
            "id": deliverable_id,
            "html": upload_data["html"],
            "client_name": "Integration Test Client"
        }

        with patch("main.render_pdf_bytes_with_playwright") as mock_pdf:
            mock_pdf.return_value = b"Mock PDF content for integration test"

            mock_supabase.storage.from_.return_value.upload.return_value = {"error": None}
            mock_supabase.storage.from_.return_value.create_signed_url.return_value = {
                "signedURL": f"http://test.com/signed/{deliverable_id}.pdf"
            }

            pdf_response = client.get(f"/deliverables/{deliverable_id}/pdf")

    assert pdf_response.status_code == 200
    pdf_data = pdf_response.json()
    assert "url" in pdf_data
    assert deliverable_id in pdf_data["url"]

    # Step 4: List deliverables
    mock_supabase.table.return_value.select.return_value.order.return_value.execute.return_value = Mock(
        data=[{
            "id": deliverable_id,
            "client_name": "Integration Test Client",
            "created_at": "2023-01-01T00:00:00Z"
        }]
    )

    list_response = client.get("/deliverables")
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert len(list_data) >= 1
    assert any(d["id"] == deliverable_id for d in list_data)


@pytest.mark.integration
def test_brand_management_flow(client: TestClient, mock_supabase, sample_image_file):
    """Test complete brand management flow."""
    # Step 1: Upload logo
    mock_supabase.storage.from_.return_value.upload.return_value = {"error": None}
    mock_supabase.storage.from_.return_value.get_public_url.return_value = {
        "data": {"publicUrl": "http://test.com/logos/test-logo.png"}
    }

    files = {"file": ("logo.png", sample_image_file, "image/png")}
    logo_response = client.post("/brand/logo", files=files)

    assert logo_response.status_code == 200
    logo_data = logo_response.json()
    logo_url = logo_data["url"]

    # Step 2: Update brand settings with new logo
    brand_settings = {
        "primary_color": "#FF5722",
        "secondary_color": "#FFC107",
        "logo_url": logo_url
    }

    mock_supabase.table.return_value.upsert.return_value.execute.return_value = Mock(error=None)

    settings_response = client.put("/brand/settings", json=brand_settings)
    assert settings_response.status_code == 200

    # Step 3: Retrieve updated settings
    mock_supabase.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = Mock(
        data=[brand_settings]
    )

    get_settings_response = client.get("/brand/settings")
    assert get_settings_response.status_code == 200
    retrieved_settings = get_settings_response.json()
    assert retrieved_settings["primary_color"] == "#FF5722"
    assert retrieved_settings["logo_url"] == logo_url


@pytest.mark.integration
@pytest.mark.auth
def test_authentication_flow(client: TestClient, mock_supabase, auth_headers):
    """Test complete authentication flow."""
    # Step 1: Send magic link
    mock_supabase.auth.sign_in_with_otp.return_value = {"error": None}

    magic_link_response = client.post(
        "/auth/magic-link",
        json={"email": "integration@test.com"}
    )
    assert magic_link_response.status_code == 200

    # Step 2: Simulate auth callback
    mock_user = {"id": "integration-user-id", "email": "integration@test.com"}
    mock_supabase.auth.set_session.return_value = Mock(user=mock_user)

    callback_response = client.post(
        "/auth/callback",
        data={
            "access_token": "integration-access-token",
            "refresh_token": "integration-refresh-token",
            "expires_in": 3600,
            "token_type": "bearer"
        }
    )
    assert callback_response.status_code == 200
    callback_data = callback_response.json()
    assert callback_data["user"]["email"] == "integration@test.com"

    # Step 3: Get user profile
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
        data={
            "id": "integration-user-id",
            "email": "integration@test.com",
            "name": "Integration User",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z"
        }
    )

    profile_response = client.get("/auth/user", headers=auth_headers)
    assert profile_response.status_code == 200
    profile_data = profile_response.json()
    assert profile_data["email"] == "integration@test.com"

    # Step 4: Update profile
    mock_supabase.table.return_value.upsert.return_value.execute.return_value = Mock(
        data=[{
            "id": "integration-user-id",
            "email": "integration@test.com",
            "name": "Updated Integration User",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z"
        }]
    )

    update_response = client.put(
        "/auth/user",
        headers=auth_headers,
        json={"name": "Updated Integration User"}
    )
    assert update_response.status_code == 200
    update_data = update_response.json()
    assert update_data["name"] == "Updated Integration User"

    # Step 5: Sign out
    mock_supabase.auth.sign_out.return_value = None

    signout_response = client.post("/auth/signout", headers=auth_headers)
    assert signout_response.status_code == 200


@pytest.mark.integration
@pytest.mark.auth
def test_organization_management_flow(client: TestClient, mock_supabase, auth_headers):
    """Test complete organization management flow."""
    # Step 1: Create organization
    new_org = {
        "id": "integration-org-id",
        "name": "Integration Test Org",
        "slug": "integration-test-org",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z"
    }

    # Mock slug uniqueness check
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[])

    # Mock organization creation
    mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[new_org])

    create_response = client.post(
        "/organizations",
        headers=auth_headers,
        json={"name": "Integration Test Org"}
    )
    assert create_response.status_code == 200
    org_data = create_response.json()
    org_id = org_data["id"]

    # Step 2: Get organization details
    # Mock access check
    mock_member = {
        "id": "member-id",
        "user_id": "test-user-id",
        "organization_id": org_id,
        "role": "owner"
    }
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(data=mock_member)

    # Mock organization data
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(data=new_org)

    get_org_response = client.get(f"/organizations/{org_id}", headers=auth_headers)
    assert get_org_response.status_code == 200

    # Step 3: List organization members
    mock_members = [
        {
            "id": "member-1",
            "user_id": "test-user-id",
            "role": "owner",
            "profiles": {"id": "test-user-id", "email": "owner@test.com", "name": "Owner"}
        }
    ]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=mock_members)

    members_response = client.get(f"/organizations/{org_id}/members", headers=auth_headers)
    assert members_response.status_code == 200
    members_data = members_response.json()
    assert len(members_data) == 1
    assert members_data[0]["role"] == "owner"

    # Step 4: Update organization
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(
        data=[{**new_org, "name": "Updated Integration Org"}]
    )

    update_org_response = client.put(
        f"/organizations/{org_id}",
        headers=auth_headers,
        json={"name": "Updated Integration Org"}
    )
    assert update_org_response.status_code == 200


@pytest.mark.integration
@pytest.mark.slow
def test_error_handling_flow(client: TestClient, mock_supabase):
    """Test error handling across different scenarios."""
    # Test 1: Invalid file upload
    invalid_file = io.BytesIO(b"not a real audio file")
    files = {"file": ("invalid.txt", invalid_file, "text/plain")}
    data = {"client_name": "Error Test Client"}

    # This should either process gracefully or return appropriate error
    response = client.post("/upload", files=files, data=data)
    assert response.status_code in [200, 400, 422]

    # Test 2: Non-existent deliverable
    response = client.get("/deliverables/non-existent-id")
    assert response.status_code == 404

    # Test 3: Unauthorized access
    response = client.get("/auth/user")  # No auth headers
    assert response.status_code == 403

    # Test 4: Invalid organization access
    response = client.get("/organizations/no-access-org", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code in [401, 403]

    # Test 5: Malformed request data
    response = client.post("/generate", json={"invalid": "data"})
    assert response.status_code == 422
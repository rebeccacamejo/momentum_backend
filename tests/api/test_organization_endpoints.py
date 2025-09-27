"""
Test organization management endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock


@pytest.mark.api
@pytest.mark.auth
def test_get_user_organizations_success(client: TestClient, mock_supabase, auth_headers, test_organization_data):
    """Test successful user organizations retrieval."""
    mock_org_member = {
        "id": "member-id",
        "user_id": "test-user-id",
        "organization_id": test_organization_data["id"],
        "role": "owner",
        "created_at": "2023-01-01T00:00:00Z",
        "organizations": test_organization_data
    }

    mock_response = Mock()
    mock_response.data = [mock_org_member]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

    response = client.get("/organizations", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["organizations"]["name"] == test_organization_data["name"]
    assert data[0]["role"] == "owner"


@pytest.mark.api
@pytest.mark.auth
def test_create_organization_success(client: TestClient, mock_supabase, auth_headers):
    """Test successful organization creation."""
    # Mock organization creation
    new_org = {
        "id": "new-org-id",
        "name": "New Organization",
        "slug": "new-organization",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z"
    }

    # Mock slug uniqueness check
    mock_existing_response = Mock()
    mock_existing_response.data = []
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_existing_response

    # Mock organization insert
    mock_org_response = Mock()
    mock_org_response.data = [new_org]
    mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_org_response

    # Mock member insert
    mock_member_response = Mock()
    mock_member_response.data = [{"id": "member-id"}]
    mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_member_response

    response = client.post(
        "/organizations",
        headers=auth_headers,
        json={
            "name": "New Organization",
            "slug": "new-organization"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Organization"
    assert data["slug"] == "new-organization"


@pytest.mark.api
@pytest.mark.auth
def test_create_organization_duplicate_slug(client: TestClient, mock_supabase, auth_headers):
    """Test organization creation with duplicate slug."""
    # Mock existing organization with same slug
    mock_existing_response = Mock()
    mock_existing_response.data = [{"id": "existing-org-id"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_existing_response

    response = client.post(
        "/organizations",
        headers=auth_headers,
        json={
            "name": "Duplicate Organization",
            "slug": "existing-slug"
        }
    )

    assert response.status_code == 400
    assert "Organization slug already exists" in response.json()["detail"]


@pytest.mark.api
@pytest.mark.auth
def test_create_organization_auto_slug(client: TestClient, mock_supabase, auth_headers):
    """Test organization creation with auto-generated slug."""
    new_org = {
        "id": "new-org-id",
        "name": "Test Organization",
        "slug": "test-organization",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z"
    }

    # Mock slug uniqueness check
    mock_existing_response = Mock()
    mock_existing_response.data = []
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_existing_response

    # Mock organization insert
    mock_org_response = Mock()
    mock_org_response.data = [new_org]
    mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_org_response

    response = client.post(
        "/organizations",
        headers=auth_headers,
        json={"name": "Test Organization"}  # No slug provided
    )

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "test-organization"


@pytest.mark.api
@pytest.mark.auth
def test_get_organization_success(client: TestClient, mock_supabase, auth_headers, test_organization_data):
    """Test successful organization retrieval."""
    # Mock organization access check
    mock_member = {
        "id": "member-id",
        "user_id": "test-user-id",
        "organization_id": test_organization_data["id"],
        "role": "member"
    }
    mock_member_response = Mock()
    mock_member_response.data = mock_member
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_member_response

    # Mock organization data
    mock_org_response = Mock()
    mock_org_response.data = test_organization_data
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_org_response

    response = client.get(f"/organizations/{test_organization_data['id']}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == test_organization_data["name"]
    assert data["slug"] == test_organization_data["slug"]


@pytest.mark.api
@pytest.mark.auth
def test_get_organization_access_denied(client: TestClient, mock_supabase, auth_headers):
    """Test organization retrieval with no access."""
    # Mock no membership
    mock_member_response = Mock()
    mock_member_response.data = None
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_member_response

    response = client.get("/organizations/no-access-org-id", headers=auth_headers)

    assert response.status_code == 403
    assert "Access denied to organization" in response.json()["detail"]


@pytest.mark.api
@pytest.mark.auth
def test_update_organization_success(client: TestClient, mock_supabase, auth_headers, test_organization_data):
    """Test successful organization update."""
    # Mock admin access
    mock_member = {
        "id": "member-id",
        "user_id": "test-user-id",
        "organization_id": test_organization_data["id"],
        "role": "admin"
    }
    mock_member_response = Mock()
    mock_member_response.data = mock_member
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_member_response

    # Mock organization update
    updated_org = {**test_organization_data, "name": "Updated Organization"}
    mock_org_response = Mock()
    mock_org_response.data = [updated_org]
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_org_response

    response = client.put(
        f"/organizations/{test_organization_data['id']}",
        headers=auth_headers,
        json={"name": "Updated Organization"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Organization"


@pytest.mark.api
@pytest.mark.auth
def test_update_organization_insufficient_permissions(client: TestClient, mock_supabase, auth_headers, test_organization_data):
    """Test organization update with insufficient permissions."""
    # Mock member access (not admin)
    mock_member = {
        "id": "member-id",
        "user_id": "test-user-id",
        "organization_id": test_organization_data["id"],
        "role": "member"
    }
    mock_member_response = Mock()
    mock_member_response.data = mock_member
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_member_response

    response = client.put(
        f"/organizations/{test_organization_data['id']}",
        headers=auth_headers,
        json={"name": "Updated Organization"}
    )

    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]


@pytest.mark.api
@pytest.mark.auth
def test_get_organization_members_success(client: TestClient, mock_supabase, auth_headers, test_organization_data):
    """Test successful organization members retrieval."""
    # Mock organization access
    mock_member = {
        "id": "member-id",
        "user_id": "test-user-id",
        "organization_id": test_organization_data["id"],
        "role": "member"
    }
    mock_member_response = Mock()
    mock_member_response.data = mock_member
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_member_response

    # Mock members list
    mock_members = [
        {
            "id": "member-1",
            "user_id": "user-1",
            "role": "owner",
            "profiles": {"id": "user-1", "email": "owner@example.com", "name": "Owner User"}
        },
        {
            "id": "member-2",
            "user_id": "user-2",
            "role": "member",
            "profiles": {"id": "user-2", "email": "member@example.com", "name": "Member User"}
        }
    ]
    mock_members_response = Mock()
    mock_members_response.data = mock_members
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_members_response

    response = client.get(f"/organizations/{test_organization_data['id']}/members", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["role"] == "owner"
    assert data[1]["role"] == "member"


@pytest.mark.api
@pytest.mark.auth
def test_invite_member_success(client: TestClient, mock_supabase, auth_headers, test_organization_data):
    """Test successful member invitation."""
    # Mock admin access
    mock_member = {
        "id": "member-id",
        "user_id": "test-user-id",
        "organization_id": test_organization_data["id"],
        "role": "admin"
    }
    mock_member_response = Mock()
    mock_member_response.data = mock_member
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_member_response

    # Mock existing user check
    mock_user_response = Mock()
    mock_user_response.data = [{"id": "existing-user-id"}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_user_response

    # Mock existing member check
    mock_existing_member_response = Mock()
    mock_existing_member_response.data = []
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_existing_member_response

    # Mock member insert
    mock_insert_response = Mock()
    mock_insert_response.data = [{"id": "new-member-id"}]
    mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert_response

    response = client.post(
        f"/organizations/{test_organization_data['id']}/members",
        headers=auth_headers,
        json={
            "email": "newmember@example.com",
            "role": "member"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "successfully" in data["message"]


@pytest.mark.api
@pytest.mark.auth
def test_invite_member_already_exists(client: TestClient, mock_supabase, auth_headers, test_organization_data):
    """Test inviting a member who is already in the organization."""
    # Mock admin access
    mock_member = {
        "id": "member-id",
        "user_id": "test-user-id",
        "organization_id": test_organization_data["id"],
        "role": "admin"
    }
    mock_member_response = Mock()
    mock_member_response.data = mock_member
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_member_response

    # Mock existing user
    mock_user_response = Mock()
    mock_user_response.data = [{"id": "existing-user-id"}]

    # Mock existing member
    mock_existing_member_response = Mock()
    mock_existing_member_response.data = [{"id": "existing-member-id"}]

    # Set up the chain of calls
    mock_table = mock_supabase.table.return_value
    mock_table.select.return_value.eq.return_value.execute.side_effect = [
        mock_member_response,  # Access check
        mock_user_response,    # User exists check
        mock_existing_member_response  # Member exists check
    ]

    response = client.post(
        f"/organizations/{test_organization_data['id']}/members",
        headers=auth_headers,
        json={
            "email": "existing@example.com",
            "role": "member"
        }
    )

    assert response.status_code == 400
    assert "already a member" in response.json()["detail"]


@pytest.mark.api
@pytest.mark.auth
def test_remove_member_success(client: TestClient, mock_supabase, auth_headers, test_organization_data):
    """Test successful member removal."""
    # Mock admin access
    mock_member = {
        "id": "member-id",
        "user_id": "test-user-id",
        "organization_id": test_organization_data["id"],
        "role": "admin"
    }
    mock_member_response = Mock()
    mock_member_response.data = mock_member
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_member_response

    # Mock member deletion
    mock_delete_response = Mock()
    mock_delete_response.data = []
    mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_delete_response

    response = client.delete(
        f"/organizations/{test_organization_data['id']}/members/other-user-id",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "removed successfully" in data["message"]


@pytest.mark.api
@pytest.mark.auth
def test_remove_member_owner_self(client: TestClient, mock_supabase, auth_headers, test_organization_data):
    """Test owner trying to remove themselves."""
    # Mock owner access
    mock_member = {
        "id": "member-id",
        "user_id": "test-user-id",
        "organization_id": test_organization_data["id"],
        "role": "owner"
    }
    mock_member_response = Mock()
    mock_member_response.data = mock_member
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_member_response

    response = client.delete(
        f"/organizations/{test_organization_data['id']}/members/test-user-id",  # Self removal
        headers=auth_headers
    )

    assert response.status_code == 400
    assert "owner cannot remove themselves" in response.json()["detail"]


@pytest.mark.api
@pytest.mark.auth
def test_leave_organization_success(client: TestClient, mock_supabase, auth_headers, test_organization_data):
    """Test successful organization leave."""
    # Mock member access (not owner)
    mock_member = {
        "id": "member-id",
        "user_id": "test-user-id",
        "organization_id": test_organization_data["id"],
        "role": "member"
    }
    mock_member_response = Mock()
    mock_member_response.data = mock_member
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_member_response

    # Mock member deletion
    mock_delete_response = Mock()
    mock_delete_response.data = []
    mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_delete_response

    response = client.post(f"/organizations/{test_organization_data['id']}/leave", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "Successfully left organization" in data["message"]


@pytest.mark.api
@pytest.mark.auth
def test_leave_organization_owner(client: TestClient, mock_supabase, auth_headers, test_organization_data):
    """Test owner trying to leave organization."""
    # Mock owner access
    mock_member = {
        "id": "member-id",
        "user_id": "test-user-id",
        "organization_id": test_organization_data["id"],
        "role": "owner"
    }
    mock_member_response = Mock()
    mock_member_response.data = mock_member
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_member_response

    response = client.post(f"/organizations/{test_organization_data['id']}/leave", headers=auth_headers)

    assert response.status_code == 400
    assert "transfer ownership" in response.json()["detail"]
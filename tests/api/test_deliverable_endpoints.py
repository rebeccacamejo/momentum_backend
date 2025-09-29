"""
Test deliverable endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import io


@pytest.mark.api
def test_generate_deliverable_success(client: TestClient, mock_supabase, mock_openai):
    """Test successful deliverable generation."""
    # Mock OpenAI response
    mock_openai.chat.completions.create.return_value = Mock(
        choices=[Mock(
            message=Mock(
                content='{"summary": "Test summary", "action_items": [{"task": "Test task", "owner": "Test owner"}]}'
            )
        )]
    )

    # Mock Supabase save
    mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "test-id"}])

    with patch("utils.deliverables.render_deliverable") as mock_render:
        mock_render.return_value = "<html><body>Test HTML</body></html>"

        response = client.post(
            "/generate",
            json={
                "transcript": "This is a test transcript",
                "client_name": "Test Client",
                "user_id": "test-user-123",
                "template_type": "action_plan",
                "primary_color": "#2A3EB1",
                "secondary_color": "#4C6FE7"
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["html"] == "<html><body>Test HTML</body></html>"


@pytest.mark.api
def test_generate_deliverable_invalid_colors(client: TestClient):
    """Test deliverable generation with invalid colors."""
    response = client.post(
        "/generate",
        json={
            "transcript": "This is a test transcript",
            "client_name": "Test Client",
            "user_id": "test-user-123",
            "template_type": "action_plan",
            "primary_color": "invalid-color",  # Invalid hex color
            "secondary_color": "#4C6FE7"
        }
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.api
def test_upload_recording_success(client: TestClient, mock_supabase, mock_openai, sample_audio_file):
    """Test successful audio file upload and processing."""
    # Mock OpenAI transcription
    mock_openai.audio.transcriptions.create.return_value = Mock(
        text="This is a sample transcription"
    )

    # Mock OpenAI summarization
    mock_openai.chat.completions.create.return_value = Mock(
        choices=[Mock(
            message=Mock(
                content='{"summary": "Test summary", "action_items": [{"task": "Test task"}]}'
            )
        )]
    )

    # Mock Supabase save
    mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "test-id"}])

    with patch("utils.deliverables.render_deliverable") as mock_render:
        mock_render.return_value = "<html><body>Test HTML</body></html>"

        files = {"file": ("test.wav", sample_audio_file, "audio/wav")}
        data = {
            "client_name": "Test Client",
            "user_id": "test-user-123",
            "primary_color": "#2A3EB1",
            "secondary_color": "#4C6FE7",
            "template_type": "action_plan"
        }

        response = client.post("/upload", files=files, data=data)

    assert response.status_code == 200
    response_data = response.json()
    assert "id" in response_data
    assert response_data["html"] == "<html><body>Test HTML</body></html>"


@pytest.mark.api
def test_upload_recording_invalid_file_type(client: TestClient):
    """Test upload with invalid file type."""
    invalid_file = io.BytesIO(b"invalid content")
    files = {"file": ("test.txt", invalid_file, "text/plain")}
    data = {"client_name": "Test Client"}

    response = client.post("/upload", files=files, data=data)

    # Should still process but may have transcription issues
    # The actual validation depends on OpenAI's handling
    assert response.status_code in [200, 400, 422]


@pytest.mark.api
def test_upload_logo_success(client: TestClient, mock_supabase, sample_image_file):
    """Test successful logo upload."""
    mock_supabase.storage.from_.return_value.upload.return_value = {"error": None}
    mock_supabase.storage.from_.return_value.get_public_url.return_value = {
        "data": {"publicUrl": "http://test.com/logo.png"}
    }

    files = {"file": ("logo.png", sample_image_file, "image/png")}

    response = client.post("/brand/logo", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "logo.png" in data["url"]


@pytest.mark.api
def test_upload_logo_invalid_type(client: TestClient):
    """Test logo upload with invalid file type."""
    invalid_file = io.BytesIO(b"invalid content")
    files = {"file": ("invalid.txt", invalid_file, "text/plain")}

    response = client.post("/brand/logo", files=files)

    assert response.status_code == 415
    assert "Unsupported logo type" in response.json()["detail"]


@pytest.mark.api
def test_get_brand_settings_success(client: TestClient, mock_supabase):
    """Test successful brand settings retrieval."""
    mock_settings = {
        "primary_color": "#2A3EB1",
        "secondary_color": "#4C6FE7",
        "logo_url": "http://test.com/logo.png"
    }
    mock_response = Mock()
    mock_response.data = [mock_settings]
    mock_supabase.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

    response = client.get("/brand/settings")

    assert response.status_code == 200
    data = response.json()
    assert data["primary_color"] == "#2A3EB1"
    assert data["secondary_color"] == "#4C6FE7"


@pytest.mark.api
def test_get_brand_settings_no_data(client: TestClient, mock_supabase):
    """Test brand settings retrieval with no existing data."""
    mock_response = Mock()
    mock_response.data = []
    mock_supabase.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

    response = client.get("/brand/settings")

    assert response.status_code == 200
    data = response.json()
    assert data["primary_color"] == "#2A3EB1"  # Default values
    assert data["secondary_color"] == "#4C6FE7"
    assert data["logo_url"] is None


@pytest.mark.api
def test_update_brand_settings_success(client: TestClient, mock_supabase):
    """Test successful brand settings update."""
    new_settings = {
        "primary_color": "#FF0000",
        "secondary_color": "#00FF00",
        "logo_url": "http://test.com/new-logo.png"
    }

    mock_response = Mock()
    mock_response.error = None
    mock_supabase.table.return_value.upsert.return_value.execute.return_value = mock_response

    response = client.put("/brand/settings", json=new_settings)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.api
def test_list_deliverables_success(client: TestClient, mock_supabase, test_deliverable_data):
    """Test successful deliverables listing."""
    mock_response = Mock()
    mock_response.data = [test_deliverable_data]
    mock_supabase.table.return_value.select.return_value.order.return_value.execute.return_value = mock_response

    response = client.get("/deliverables?user_id=test-user-123")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == test_deliverable_data["id"]
    assert data[0]["client_name"] == test_deliverable_data["client_name"]


@pytest.mark.api
def test_get_deliverable_success(client: TestClient, mock_supabase, test_deliverable_data):
    """Test successful single deliverable retrieval."""
    mock_response = Mock()
    mock_response.data = test_deliverable_data
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

    response = client.get(f"/deliverables/{test_deliverable_data['id']}?user_id=test-user-123")

    assert response.status_code == 200
    assert test_deliverable_data["html"] in response.text


@pytest.mark.api
def test_get_deliverable_not_found(client: TestClient, mock_supabase):
    """Test deliverable retrieval when not found."""
    mock_response = Mock()
    mock_response.data = None
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

    response = client.get("/deliverables/nonexistent-id?user_id=test-user-123")

    assert response.status_code == 404
    assert "Deliverable not found" in response.json()["detail"]


@pytest.mark.api
def test_get_deliverable_pdf_success(client: TestClient, mock_supabase, test_deliverable_data, mock_playwright):
    """Test successful PDF generation."""
    # Mock Supabase query
    mock_response = Mock()
    mock_response.data = test_deliverable_data
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

    # Mock PDF generation
    with patch("main.render_pdf_bytes_with_playwright") as mock_pdf:
        mock_pdf.return_value = b"Mock PDF content"

        mock_supabase.storage.from_.return_value.upload.return_value = {"error": None}
        mock_supabase.storage.from_.return_value.create_signed_url.return_value = {
            "signedURL": "http://test.com/signed/deliverable.pdf"
        }

        response = client.get(f"/deliverables/{test_deliverable_data['id']}/pdf?user_id=test-user-123")

    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "signed" in data["url"]


@pytest.mark.api
def test_get_deliverable_pdf_not_found(client: TestClient, mock_supabase):
    """Test PDF generation for non-existent deliverable."""
    # Mock Supabase query to return None
    mock_response = Mock()
    mock_response.data = None
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

    response = client.get("/deliverables/nonexistent-id/pdf?user_id=test-user-123")

    assert response.status_code == 404
    assert "Deliverable not found" in response.json()["detail"]


@pytest.mark.api
def test_get_deliverable_pdf_no_html(client: TestClient, mock_supabase):
    """Test PDF generation for deliverable without HTML."""
    # Mock Supabase query to return deliverable with no HTML
    mock_response = Mock()
    mock_response.data = {"id": "test-id", "html": ""}
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

    response = client.get("/deliverables/test-id/pdf?user_id=test-user-123")

    assert response.status_code == 422
    assert "Deliverable has no HTML" in response.json()["detail"]
"""
Test configuration and fixtures for the Momentum backend.
"""
import io
import os
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
import jwt
from datetime import datetime, timedelta

# Set testing environment
os.environ["TESTING"] = "1"

from main import app
from utils.supabase_client import get_supabase, get_supabase_admin


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    mock_client = Mock()

    # Mock auth
    mock_client.auth = Mock()
    def mock_sign_in_with_otp(*args, **kwargs):
        print(f"Mock sign_in_with_otp called with args: {args}, kwargs: {kwargs}")
        return {"error": None}
    mock_client.auth.sign_in_with_otp = mock_sign_in_with_otp
    mock_client.auth.sign_in_with_oauth = AsyncMock(return_value={"error": None})
    mock_client.auth.sign_out = AsyncMock(return_value={"error": None})
    mock_client.auth.refresh_session = AsyncMock(return_value={
        "session": {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600
        },
        "user": {"id": "test-user-id", "email": "test@example.com"}
    })
    mock_client.auth.set_session = AsyncMock(return_value={
        "user": {"id": "test-user-id", "email": "test@example.com"}
    })
    mock_client.auth.get_session = AsyncMock(return_value={
        "data": {
            "session": {
                "access_token": "test-token",
                "refresh_token": "test-refresh-token"
            }
        }
    })

    # Mock table operations
    mock_table = Mock()
    mock_table.select = Mock(return_value=mock_table)
    mock_table.insert = Mock(return_value=mock_table)
    mock_table.update = Mock(return_value=mock_table)
    mock_table.delete = Mock(return_value=mock_table)
    mock_table.upsert = Mock(return_value=mock_table)
    mock_table.eq = Mock(return_value=mock_table)
    mock_table.single = Mock(return_value=mock_table)
    mock_table.order = Mock(return_value=mock_table)
    mock_table.limit = Mock(return_value=mock_table)
    mock_table.execute = AsyncMock(return_value=Mock(data=[]))

    mock_client.table = Mock(return_value=mock_table)

    # Mock storage
    mock_storage = Mock()
    mock_storage.upload = Mock(return_value={"error": None})
    mock_storage.get_public_url = Mock(return_value={
        "data": {"publicUrl": "http://test.com/file.png"}
    })
    mock_storage.create_signed_url = Mock(return_value={
        "signedURL": "http://test.com/signed-file.pdf"
    })

    mock_client.storage.from_ = Mock(return_value=mock_storage)

    return mock_client


@pytest.fixture
def mock_openai():
    """Mock OpenAI client."""
    mock_client = Mock()

    # Mock transcription
    mock_client.audio = Mock()
    mock_client.audio.transcriptions = Mock()
    mock_client.audio.transcriptions.create = Mock(return_value=Mock(
        text="This is a sample transcription of the audio file."
    ))

    # Mock chat completion
    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()
    mock_client.chat.completions.create = Mock(return_value=Mock(
        choices=[Mock(
            message=Mock(
                content='{"summary": "Test summary", "action_items": [{"task": "Test task", "owner": "Test owner"}]}'
            )
        )]
    ))

    return mock_client


@pytest.fixture
def sample_audio_file():
    """Sample audio file for testing."""
    # Create a minimal WAV file content
    wav_header = b'RIFF' + b'\x00' * 4 + b'WAVE' + b'fmt ' + b'\x10\x00\x00\x00'
    wav_header += b'\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00'
    wav_header += b'data' + b'\x00' * 4

    return io.BytesIO(wav_header)


@pytest.fixture
def sample_image_file():
    """Sample image file for testing."""
    # Minimal PNG file
    png_content = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13'
        b'\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8'
        b'\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return io.BytesIO(png_content)


@pytest.fixture
def jwt_token():
    """Generate a test JWT token."""
    payload = {
        "sub": "test-user-id",
        "email": "test@example.com",
        "role": "authenticated",
        "aud": "authenticated",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "iss": "supabase",
        "user_metadata": {"name": "Test User"},
        "app_metadata": {}
    }
    return jwt.encode(payload, "test-jwt-secret", algorithm="HS256")


@pytest.fixture
def auth_headers(jwt_token):
    """Authentication headers for tests."""
    return {"Authorization": f"Bearer {jwt_token}"}


@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    return {
        "id": "test-user-id",
        "email": "test@example.com",
        "name": "Test User",
        "avatar_url": "http://example.com/avatar.jpg",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z"
    }


@pytest.fixture
def test_organization_data():
    """Sample organization data for testing."""
    return {
        "id": "test-org-id",
        "name": "Test Organization",
        "slug": "test-organization",
        "logo_url": "http://example.com/logo.png",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z"
    }


@pytest.fixture
def test_deliverable_data():
    """Sample deliverable data for testing."""
    return {
        "id": "test-deliverable-id",
        "client_name": "Test Client",
        "html": "<html><body><h1>Test Deliverable</h1></body></html>",
        "created_at": "2023-01-01T00:00:00Z",
        "user_id": "test-user-id"
    }


@pytest.fixture(autouse=True)
def mock_dependencies(monkeypatch, mock_supabase, mock_openai):
    """Mock all external dependencies."""
    monkeypatch.setattr("utils.supabase_client.get_supabase", lambda: mock_supabase)
    monkeypatch.setattr("utils.supabase_client.get_supabase_admin", lambda: mock_supabase)
    monkeypatch.setattr("utils.deliverables.get_supabase", lambda: mock_supabase)

    # Mock OpenAI
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_openai)

    # Mock file operations
    monkeypatch.setattr("os.getenv", lambda key, default=None: {
        "SUPABASE_URL": "http://localhost:54321",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "SUPABASE_JWT_SECRET": "test-jwt-secret",
        "OPENAI_API_KEY": "test-openai-key",
        "FRONTEND_URL": "http://localhost:3000"
    }.get(key, default))

    # Mock email validation to avoid strict validation in tests
    import email_validator
    def mock_validate_email(email: str, **kwargs):
        return {"email": email, "local": email.split("@")[0], "domain": email.split("@")[1]}
    monkeypatch.setattr(email_validator, "validate_email", mock_validate_email)


@pytest.fixture
def mock_playwright():
    """Mock Playwright for PDF generation."""
    mock_page = AsyncMock()
    mock_page.set_content = AsyncMock()
    mock_page.pdf = AsyncMock(return_value=b"Mock PDF content")
    mock_page.close = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    mock_browser.close = AsyncMock()

    mock_playwright_instance = AsyncMock()
    mock_playwright_instance.chromium = Mock()
    mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)

    return mock_playwright_instance
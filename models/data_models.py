from pydantic import BaseModel, Field, EmailStr
from typing import Any, Dict, List, Optional
from enum import Enum

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class UserRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

class MagicLinkRequest(BaseModel):
    email: EmailStr
    redirect_to: Optional[str] = None

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: Dict[str, Any]
    expires_in: int

class UserProfile(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: str
    updated_at: str

class Organization(BaseModel):
    id: str
    name: str
    slug: str
    logo_url: Optional[str] = None
    created_at: str
    updated_at: str

class OrganizationMember(BaseModel):
    id: str
    user_id: str
    organization_id: str
    role: UserRole
    created_at: str
    updated_at: str

class CreateOrganizationRequest(BaseModel):
    name: str
    slug: Optional[str] = None

class UpdateOrganizationRequest(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None

class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.MEMBER

class UpdateMemberRoleRequest(BaseModel):
    role: UserRole

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None

class ActionItem(BaseModel):
    task: str
    owner: Optional[str] = None
    due_date: Optional[str] = None


class GenerateRequest(BaseModel):
    """Payload for the /generate endpoint."""

    transcript: str = Field(..., description="The raw transcript of the session")
    client_name: str = Field(..., description="Name of the client or session")
    user_id: str = Field(..., description="ID of the user creating the deliverable")
    template_type: str = Field(
        default="action_plan",
        description="The type of deliverable to generate",
    )
    primary_color: str = Field(
    default="#2A3EB1",
    description="Primary brand colour in HEX",
    pattern=r"^#(?:[0-9a-fA-F]{3}){1,2}$",
)
    secondary_color: str = Field(
    default="#4C6FE7",
    description="Secondary brand colour in HEX",
    pattern=r"^#(?:[0-9a-fA-F]{3}){1,2}$",
)
    logo_url: Optional[str] = Field(
        default=None,
        description="Publicly accessible URL of the company/coach logo",
    )


class GenerateResponse(BaseModel):
    id: str
    html: str

class BrandSettings(BaseModel):
    primary_color: Optional[str] = "#2A3EB1"
    secondary_color: Optional[str] = "#4C6FE7"
    logo_url: Optional[str] = None

# ---------------------------------------------------------------------------
# Zoom Integration Models
# ---------------------------------------------------------------------------

class ZoomAuthRequest(BaseModel):
    code: str
    state: Optional[str] = None

class ZoomAuthResponse(BaseModel):
    success: bool
    message: str
    zoom_user_id: Optional[str] = None
    zoom_email: Optional[str] = None

class ZoomMeetingFile(BaseModel):
    id: str
    meeting_id: str
    file_type: str  # MP4, M4A, etc.
    file_size: int
    download_url: str
    recording_type: str  # shared_screen_with_speaker_view, audio_only, etc.

class ZoomMeeting(BaseModel):
    id: str
    uuid: str
    topic: str
    start_time: str
    duration: int  # in minutes
    total_size: int  # total size of all recordings
    recording_count: int
    recording_files: List[ZoomMeetingFile]

class ZoomMeetingsResponse(BaseModel):
    meetings: List[ZoomMeeting]
    page_count: int
    page_number: int
    page_size: int
    total_records: int

class ZoomDownloadRequest(BaseModel):
    file_id: str
    process_immediately: bool = True

class ZoomDownloadResponse(BaseModel):
    success: bool
    message: str
    deliverable_id: Optional[str] = None
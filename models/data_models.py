from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ActionItem(BaseModel):
    task: str
    owner: Optional[str] = None
    due_date: Optional[str] = None


class GenerateRequest(BaseModel):
    """Payload for the /generate endpoint."""

    transcript: str = Field(..., description="The raw transcript of the session")
    client_name: str = Field(..., description="Name of the client or session")
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
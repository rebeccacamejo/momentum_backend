"""
Momentum Backend API

This FastAPI application serves as the backend for the Momentum MVP. It provides
endpoints for uploading session recordings, generating structured session
deliverables, and retrieving previously generated deliverables. The backend
leverages OpenAI for transcription and summarization, Jinja2 for rendering
HTML templates, and Supabase for persistent data storage. To run this
application you must supply the appropriate environment variables and install
the dependencies listed in ``requirements.txt``.

Endpoints
---------

``GET /``
    Health check endpoint returning a simple message.

``POST /generate``
    Generate a deliverable from a raw transcript. Expects JSON payload
    containing the transcript text, client name, optional brand colours,
    logo URL, and desired template type. Returns a unique identifier and
    rendered HTML for the deliverable.

``POST /upload``
    Upload an audio or video file (e.g. MP3/MP4/M4A). The backend will
    transcribe the recording using OpenAI Whisper, summarise the
    conversation into a structured deliverable, render it as HTML, and
    store it in Supabase. Returns a unique identifier and the rendered
    HTML.

``GET /deliverables``
    List previously generated deliverables. In a production system this
    would require user authentication and would return only deliverables
    belonging to the authenticated user.

``GET /deliverables/{deliverable_id}``
    Retrieve a single deliverable by ID. Returns the stored HTML.

"""

import io
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

from models.data_models import (
    BrandSettings, GenerateRequest, GenerateResponse,
    MagicLinkRequest, AuthResponse, UserProfile, Organization,
    CreateOrganizationRequest, UpdateOrganizationRequest,
    InviteMemberRequest, UpdateMemberRoleRequest, UpdateProfileRequest
)

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form, Body, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from utils.deliverables import ALLOWED_IMAGE_MIME_TYPES, save_deliverable, get_deliverable_from_db, call_openai_summary, render_deliverable, render_pdf_bytes_with_playwright, _infer_mime, generate_audio_transcript
from utils.supabase_client import get_supabase, get_supabase_admin
from utils.auth import get_current_user, get_optional_user, get_user_organizations, check_organization_access

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
supa = get_supabase()

app = FastAPI(title="Momentum API", version="0.1.0")

# Configure CORS to allow local development on different origins. In
# production restrict this to your frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> Dict[str, str]:
    """Health check endpoint."""
    return {"message": "Momentum backend is running"}


@app.post("/generate", response_model=GenerateResponse)
async def generate_deliverable(req: GenerateRequest) -> GenerateResponse:
    """Generate a structured deliverable from raw transcript text."""
    # Call OpenAI to summarise the transcript
    summary_data = call_openai_summary(req.transcript)
    # Render HTML using provided brand colours and logo
    html = render_deliverable(
        client_name=req.client_name,
        data=summary_data,
        primary_color=req.primary_color,
        secondary_color=req.secondary_color,
        logo_url=req.logo_url,
        template_type=req.template_type,
    )
    deliverable_id = uuid.uuid4().hex
    await save_deliverable(deliverable_id, req.client_name, html, user_id=None)
    return GenerateResponse(id=deliverable_id, html=html)


@app.post("/upload", response_model=GenerateResponse)
async def upload_recording(
    file: UploadFile = File(...),
    client_name: str = Form(...),
    primary_color: str = Form("#2A3EB1"),
    secondary_color: str = Form("#4C6FE7"),
    logo_url: Optional[str] = Form(None),
    template_type: str = Form("action_plan"),
) -> GenerateResponse:
    """Upload an audio/video file and generate a deliverable.

    Parameters
    ----------
    file : UploadFile
        The uploaded audio or video file (MP3, MP4, M4A, etc.).
    client_name : str
        Name of the client/session.
    primary_color, secondary_color, logo_url, template_type
        Branding options identical to the ``/generate`` endpoint.

    Returns
    -------
    GenerateResponse
        Unique deliverable ID and the rendered HTML.
    """
    # Read the entire file into memory. For large files consider streaming
    # directly to OpenAI's API.
    contents = await file.read()
    file_bytes = io.BytesIO(contents)
    # Transcribe using OpenAI Whisper
    transcript_text = generate_audio_transcript(file_bytes)
    # Summarise and render deliverable
    summary_data = call_openai_summary(transcript_text)
    html = render_deliverable(
        client_name=client_name,
        data=summary_data,
        primary_color=primary_color,
        secondary_color=secondary_color,
        logo_url=logo_url,
        template_type=template_type,
    )
    deliverable_id = uuid.uuid4().hex
    await save_deliverable(deliverable_id, client_name, html, user_id=None, supa=supa)
    return GenerateResponse(id=deliverable_id, html=html)

@app.post("/brand/logo")
async def upload_logo(file: UploadFile = File(...)) -> Dict[str, str]:
    """
    Upload a brand logo (PNG/JPEG/SVG) to Supabase Storage and return a URL.
    For MVP we assume LOGO_BUCKET is public; otherwise we return a signed URL.
    """
    filename = file.filename or "logo"
    mime = file.content_type or _infer_mime(filename)
    if mime not in ALLOWED_IMAGE_MIME_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported logo type. Use PNG/JPEG/SVG.")

    # Read bytes
    content = await file.read()
    # Compose unique path: logos/<uuid>.<ext>
    _, ext = os.path.splitext(filename)
    ext = (ext or "").lower() or ".png"
    path = f"logos/{uuid.uuid4()}{ext}"

    try:
        # Upload; allow overwrite = upsert, set content-type
        supa.storage.from_("logos").upload(
            path=path,
            file=content,
            file_options={
                "content-type": mime,
                "cache-control": "public, max-age=31536000",
                "upsert": "true",
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to upload logo: {exc}")

    # If bucket is public, get a stable public URL; else create a long-lived signed URL.
    try:
        public_url_resp = supa.storage.from_("logos").get_public_url(path)
        # supabase v2 returns {'data': {'publicUrl': '...'}}
        public_url = None
        if isinstance(public_url_resp, dict):
            data = public_url_resp.get("data") or {}
            public_url = data.get("publicUrl")
        if public_url:
            return {"url": public_url}

        # Fallback to signed URL (e.g., if bucket is private)
        signed = supa.storage.from_("logos").create_signed_url(path, expires_in=60 * 60 * 24 * 7)  # 7 days
        url = signed.get("signedURL") if isinstance(signed, dict) else signed["signedURL"]
        return {"url": url}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create logo URL: {exc}")
    

@app.get("/brand/settings")
async def get_brand_settings() -> Dict[str, Any]:
    resp = supa.table("brand_settings").select("*").order("created_at", desc=True).limit(1).execute()
    data = resp.get("data") if isinstance(resp, dict) else getattr(resp, "data", [])
    if not data:
        return {"primary_color": "#2A3EB1", "secondary_color": "#4C6FE7", "logo_url": None}
    return data[0]

@app.put("/brand/settings")
async def update_brand_settings(settings: BrandSettings = Body(...)) -> Dict[str, Any]:
    payload = {
        "primary_color": settings.primary_color,
        "secondary_color": settings.secondary_color,
        "logo_url": settings.logo_url,
        "updated_at": datetime.utcnow().isoformat(),
    }
    resp = supa.table("brand_settings").upsert(payload).execute()
    if "error" in resp and resp["error"]:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {resp['error']}")
    return {"success": True, "settings": payload}


@app.get("/deliverables")
async def list_deliverables() -> List[Dict[str, Any]]:
    """Return a list of all deliverables stored in Supabase.

    This endpoint is unauthenticated for the MVP. In a production
    environment you must restrict this query to the current user via
    row level security or by filtering by ``user_id``.
    """
    response = supa.table("deliverables").select("id, client_name, created_at").order("created_at", desc=True).execute()
    data = response.get("data", []) if isinstance(response, dict) else []
    return data


@app.get("/deliverables/{deliverable_id}", response_class=HTMLResponse)
async def get_deliverable(deliverable_id: str) -> HTMLResponse:
    """Retrieve a single deliverable by ID and return the stored HTML."""
    response = supa.table("deliverables").select("html").eq("id", deliverable_id).single().execute()
    record = response.get("data") if isinstance(response, dict) else None
    if not record:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    return HTMLResponse(content=record["html"])


@app.get("/deliverables/{id}/pdf")
async def get_deliverable_pdf(id: str):
    """
    Generate (or regenerate) a PDF for a deliverable and return a signed URL.
    Saves the PDF to Supabase Storage in the configured bucket.
    """
    deliverable = get_deliverable_from_db(id)
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    html = deliverable.get("html", "")
    if not html:
        raise HTTPException(status_code=422, detail="Deliverable has no HTML")

    pdf_bytes = await render_pdf_bytes_with_playwright(html)
    path = f"deliverables/{id}.pdf"
    supa.storage.from_("private").upload(path, pdf_bytes, {"content-type": "application/pdf"})
    signed = supa.storage.from_("private").create_signed_url(path, 3600)  # 1h
    return {"url": signed["signedURL"]}


# ---------------------------------------------------------------------------
# Authentication Routes
# ---------------------------------------------------------------------------

@app.post("/auth/magic-link")
async def send_magic_link(request: MagicLinkRequest) -> Dict[str, Any]:
    """Send a magic link to the user's email for authentication."""
    supa = get_supabase()

    try:
        response = supa.auth.sign_in_with_otp({
            "email": request.email,
            "options": {
                "email_redirect_to": request.redirect_to or f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/auth/callback"
            }
        })

        return {
            "success": True,
            "message": "Magic link sent to your email"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to send magic link: {str(e)}"
        )

@app.post("/auth/callback")
async def auth_callback(
    access_token: str = Form(...),
    refresh_token: str = Form(...),
    expires_in: int = Form(...),
    token_type: str = Form(...)
) -> AuthResponse:
    """Handle authentication callback and return user session."""
    supa = get_supabase()

    try:
        # Set the session in Supabase client
        response = supa.auth.set_session(access_token, refresh_token)

        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tokens"
            )

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=response.user.model_dump(),
            expires_in=expires_in
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {str(e)}"
        )

@app.post("/auth/refresh")
async def refresh_token(refresh_token: str = Body(..., embed=True)) -> AuthResponse:
    """Refresh an access token using a refresh token."""
    supa = get_supabase()

    try:
        response = supa.auth.refresh_session(refresh_token)

        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        return AuthResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user=response.user.model_dump(),
            expires_in=response.session.expires_in or 3600
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token refresh failed: {str(e)}"
        )

@app.post("/auth/signout")
async def signout(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, str]:
    """Sign out the current user."""
    supa = get_supabase()

    try:
        supa.auth.sign_out()
        return {"message": "Successfully signed out"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sign out failed: {str(e)}"
        )

@app.get("/auth/user")
async def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)) -> UserProfile:
    """Get the current user's profile."""
    supa = get_supabase()

    try:
        response = supa.table("profiles")\
            .select("*")\
            .eq("id", current_user["id"])\
            .single()\
            .execute()

        profile_data = response.data if hasattr(response, 'data') else response.get('data')

        if not profile_data:
            # Create a basic profile if it doesn't exist
            profile_data = {
                "id": current_user["id"],
                "email": current_user["email"],
                "name": current_user.get("user_metadata", {}).get("name"),
                "avatar_url": current_user.get("user_metadata", {}).get("avatar_url"),
                "created_at": current_user.get("created_at"),
                "updated_at": current_user.get("updated_at")
            }

        return UserProfile(**profile_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get user profile: {str(e)}"
        )

@app.put("/auth/user")
async def update_user_profile(
    profile_update: UpdateProfileRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> UserProfile:
    """Update the current user's profile."""
    supa = get_supabase()

    try:
        update_data = profile_update.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow().isoformat()

        response = supa.table("profiles")\
            .upsert({
                "id": current_user["id"],
                "email": current_user["email"],
                **update_data
            })\
            .execute()

        profile_data = response.data[0] if hasattr(response, 'data') and response.data else response.get('data', [{}])[0]

        return UserProfile(**profile_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update profile: {str(e)}"
        )


# ---------------------------------------------------------------------------
# Organization Routes
# ---------------------------------------------------------------------------

@app.get("/organizations")
async def get_user_organizations_endpoint(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """Get all organizations for the current user."""
    return await get_user_organizations(current_user["id"])

@app.post("/organizations")
async def create_organization(
    org_request: CreateOrganizationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Organization:
    """Create a new organization."""
    supa = get_supabase()

    try:
        # Generate slug if not provided
        slug = org_request.slug or org_request.name.lower().replace(" ", "-").replace("_", "-")

        # Check if slug is unique
        existing = supa.table("organizations")\
            .select("id")\
            .eq("slug", slug)\
            .execute()

        if hasattr(existing, 'data') and existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization slug already exists"
            )

        # Create organization
        org_data = {
            "name": org_request.name,
            "slug": slug,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        response = supa.table("organizations")\
            .insert(org_data)\
            .execute()

        org = response.data[0] if hasattr(response, 'data') and response.data else response.get('data', [{}])[0]

        # Add user as owner
        member_data = {
            "user_id": current_user["id"],
            "organization_id": org["id"],
            "role": "owner",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        supa.table("organization_members")\
            .insert(member_data)\
            .execute()

        return Organization(**org)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create organization: {str(e)}"
        )

@app.get("/organizations/{org_id}")
async def get_organization(
    org_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Organization:
    """Get organization details."""
    await check_organization_access(current_user["id"], org_id)

    supa = get_supabase()
    response = supa.table("organizations")\
        .select("*")\
        .eq("id", org_id)\
        .single()\
        .execute()

    org_data = response.data if hasattr(response, 'data') else response.get('data')

    if not org_data:
        raise HTTPException(status_code=404, detail="Organization not found")

    return Organization(**org_data)

@app.put("/organizations/{org_id}")
async def update_organization(
    org_id: str,
    org_update: UpdateOrganizationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Organization:
    """Update organization settings (admin+ only)."""
    await check_organization_access(current_user["id"], org_id, "admin")

    supa = get_supabase()

    try:
        update_data = org_update.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow().isoformat()

        response = supa.table("organizations")\
            .update(update_data)\
            .eq("id", org_id)\
            .execute()

        org_data = response.data[0] if hasattr(response, 'data') and response.data else response.get('data', [{}])[0]

        return Organization(**org_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update organization: {str(e)}"
        )

@app.get("/organizations/{org_id}/members")
async def get_organization_members(
    org_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get organization members."""
    await check_organization_access(current_user["id"], org_id)

    supa = get_supabase()
    response = supa.table("organization_members")\
        .select("*, profiles(*)")\
        .eq("organization_id", org_id)\
        .execute()

    return response.data if hasattr(response, 'data') else response.get('data', [])

@app.post("/organizations/{org_id}/members")
async def invite_member(
    org_id: str,
    invite_request: InviteMemberRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, str]:
    """Invite a new member to the organization (admin+ only)."""
    await check_organization_access(current_user["id"], org_id, "admin")

    supa = get_supabase_admin()

    try:
        # Check if user already exists
        user_response = supa.table("profiles")\
            .select("id")\
            .eq("email", invite_request.email)\
            .execute()

        user_data = user_response.data if hasattr(user_response, 'data') else user_response.get('data', [])

        if user_data:
            user_id = user_data[0]["id"]

            # Check if already a member
            existing_member = supa.table("organization_members")\
                .select("id")\
                .eq("user_id", user_id)\
                .eq("organization_id", org_id)\
                .execute()

            if hasattr(existing_member, 'data') and existing_member.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User is already a member of this organization"
                )

            # Add as member
            member_data = {
                "user_id": user_id,
                "organization_id": org_id,
                "role": invite_request.role.value,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            supa.table("organization_members")\
                .insert(member_data)\
                .execute()

            return {"message": "User added to organization successfully"}
        else:
            # Send invitation email (implement email sending logic here)
            # For now, just return a message
            return {"message": f"Invitation sent to {invite_request.email}"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to invite member: {str(e)}"
        )

@app.delete("/organizations/{org_id}/members/{user_id}")
async def remove_member(
    org_id: str,
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, str]:
    """Remove a member from the organization (admin+ only)."""
    membership = await check_organization_access(current_user["id"], org_id, "admin")

    # Can't remove yourself if you're the owner
    if user_id == current_user["id"] and membership["role"] == "owner":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization owner cannot remove themselves"
        )

    supa = get_supabase()

    try:
        supa.table("organization_members")\
            .delete()\
            .eq("user_id", user_id)\
            .eq("organization_id", org_id)\
            .execute()

        return {"message": "Member removed successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to remove member: {str(e)}"
        )

@app.put("/organizations/{org_id}/members/{user_id}/role")
async def update_member_role(
    org_id: str,
    user_id: str,
    role_update: UpdateMemberRoleRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, str]:
    """Update a member's role (admin+ only)."""
    membership = await check_organization_access(current_user["id"], org_id, "admin")

    # Only owner can change roles to/from owner
    if (role_update.role == "owner" or membership["role"] == "owner") and membership["role"] != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owner can manage owner role"
        )

    supa = get_supabase()

    try:
        update_data = {
            "role": role_update.role.value,
            "updated_at": datetime.utcnow().isoformat()
        }

        supa.table("organization_members")\
            .update(update_data)\
            .eq("user_id", user_id)\
            .eq("organization_id", org_id)\
            .execute()

        return {"message": "Member role updated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update member role: {str(e)}"
        )

@app.post("/organizations/{org_id}/leave")
async def leave_organization(
    org_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, str]:
    """Leave an organization."""
    membership = await check_organization_access(current_user["id"], org_id)

    # Owner cannot leave unless they transfer ownership
    if membership["role"] == "owner":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization owner must transfer ownership before leaving"
        )

    supa = get_supabase()

    try:
        supa.table("organization_members")\
            .delete()\
            .eq("user_id", current_user["id"])\
            .eq("organization_id", org_id)\
            .execute()

        return {"message": "Successfully left organization"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to leave organization: {str(e)}"
        )


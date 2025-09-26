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

from models.data_models import BrandSettings, GenerateRequest, GenerateResponse

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from utils.deliverables import ALLOWED_IMAGE_MIME_TYPES, save_deliverable, get_deliverable_from_db, call_openai_summary, render_deliverable, render_pdf_bytes_with_playwright, _infer_mime, generate_audio_transcript
from .utils.supabase_client import get_supabase

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


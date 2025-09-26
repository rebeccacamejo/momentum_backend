import json
import os
import datetime
from typing import Any, Dict, List, Optional
import mimetypes
from fastapi import HTTPException
from playwright.async_api import async_playwright

from openai import OpenAI
from supabase import Client
from .supabase_client import get_supabase
from jinja2 import Environment, FileSystemLoader, select_autoescape

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY must be provided")
client = OpenAI(api_key=OPENAI_API_KEY)

# Set up Jinja2 environment to load templates from the ``templates``
# directory. Autoescape HTML to prevent injection attacks.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)

ALLOWED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/svg+xml"}

# ---------------------------------------------------------------------------
# Helper Methods
# ---------------------------------------------------------------------------

def call_openai_summary(transcript: str) -> Dict[str, Any]:
    """Call the OpenAI Chat API to generate a structured summary.

    The prompt instructs the model to return JSON containing highlights,
    goals, action items and next steps. This function will raise an
    exception on failure. In a real system you should wrap this call
    with retry logic and error handling.

    Parameters
    ----------
    transcript : str
        The session transcript.

    Returns
    -------
    dict
        Parsed JSON with keys ``highlights``, ``goals``, ``action_items``, and
        ``next_steps``.
    """
    system_prompt = (
        "You are a helpful assistant that summarises coaching or consulting "
        "sessions. You will receive a raw transcript and should return a "
        "JSON object with the following keys:\n"
        "- highlights: a list of the most important takeaways from the session\n"
        "- goals: a list of goals discussed or agreed upon\n"
        "- action_items: an array of objects with 'task', 'owner', and "
        "'due_date' fields\n"
        "- next_steps: a list of suggested next steps or follow-ups\n"
        "Respond only with valid JSON. Do not wrap the JSON in code fences."
    )
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript},
            ],
            temperature=0.2,
            max_tokens=512,
        )
        content = completion.choices[0].message.content
        # Attempt to parse JSON; if parsing fails an exception will propagate
        data = json.loads(content)
        return data
    except Exception as exc:
        raise RuntimeError(f"OpenAI summary generation failed: {exc}") from exc
    
def generate_audio_transcript(file_bytes):
    try:
        audio = client.audio.transcriptions.create(
            model="whisper-1", 
            file=("recording.m4a", file_bytes, "audio/m4a")
        )
        transcript_text = audio["text"]
        return transcript_text
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}")


def render_deliverable(
    client_name: str,
    data: Dict[str, Any],
    primary_color: str,
    secondary_color: str,
    logo_url: Optional[str],
    template_type: str,
) -> str:
    """Render the deliverable HTML using Jinja2.

    Parameters
    ----------
    client_name: str
        Name of the client/session used in the header.
    data: dict
        Parsed content with keys: highlights, goals, action_items, next_steps.
    primary_color: str
        HEX colour applied to headings and primary accents.
    secondary_color: str
        HEX colour applied to table headers.
    logo_url: str or None
        URL of the logo to display. If None no logo is shown.
    template_type: str
        Type of template requested (currently unused but reserved for future).

    Returns
    -------
    str
        Rendered HTML string.
    """
    template = jinja_env.get_template("deliverable.html")
    # Normalise action items. Ensure each entry has keys task/owner/due_date.
    action_items: List[Dict[str, str]] = []
    for item in data.get("action_items", []):
        if isinstance(item, dict):
            action_items.append(
                {
                    "task": item.get("task", ""),
                    "owner": item.get("owner", ""),
                    "due_date": item.get("due_date", ""),
                }
            )
        else:
            # If the API returned a plain string list we convert into tasks
            action_items.append({"task": str(item), "owner": "", "due_date": ""})
    html = template.render(
        title=f"{client_name} Session Report",
        highlights=data.get("highlights", []),
        goals=data.get("goals", []),
        action_items=action_items,
        next_steps=data.get("next_steps", []),
        primary_color=primary_color,
        secondary_color=secondary_color,
        logo_url=logo_url,
    )
    return html


async def save_deliverable(
    deliverable_id: str,
    client_name: str,
    html: str,
    user_id: Optional[str] = None,
    supa: Optional[Client] = None,
) -> None:
    """Persist the deliverable HTML to Supabase.

    In this MVP implementation we store the HTML along with metadata into
    a table named ``deliverables``. You must create this table in your
    Supabase project with columns: id (uuid), user_id (text), client_name (text),
    html (text), created_at (timestamp). Adjust this function to store
    additional metadata or to use RLS policies for multi-user isolation.
    """
    supa = supa or get_supabase()
    payload = {
        "id": deliverable_id,
        "user_id": user_id,
        "client_name": client_name,
        "html": html,
        "created_at": datetime.utcnow().isoformat(),
    }
    response = supa.table("deliverables").insert(payload).execute()
    if response.get("status_code") not in (200, 201):
        # Log error; for now we simply print
        print("Failed to insert deliverable into Supabase", response)

def get_deliverable_from_db(deliverable_id: str, supa: Optional[Client] = None) -> Optional[Dict[str, Any]]:
    """
    Return a single deliverable row from Supabase or None if not found.
    Expected columns: id, client_name, html, created_at (and any brand fields you store).
    """
    supa = supa or get_supabase()
    resp = supa.table("deliverables").select("*").eq("id", deliverable_id).single().execute()
    data = None
    if isinstance(resp, dict):
        data = resp.get("data")
    else:
        data = getattr(resp, "data", None)
    return data

async def render_pdf_bytes_with_playwright(html: str) -> bytes:
    """
    Render the provided HTML string to a PDF using Playwright (Chromium).
    Returns raw PDF bytes. 
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # set HTML content and wait for network to settle so webfonts/images load
        await page.set_content(html, wait_until="networkidle")

        pdf_bytes: bytes = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "18mm", "right": "14mm", "bottom": "18mm", "left": "14mm"},
        )
        await browser.close()
        return pdf_bytes
    
def _infer_mime(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"
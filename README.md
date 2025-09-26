# Momentum Backend

This repository contains the Python backend service for **Momentum**, an
application designed to help coaches and consultants quickly transform
session recordings and rough notes into polished, branded deliverables. The
backend exposes a REST API using FastAPI, performs transcription and
summarisation using OpenAI, renders HTML using Jinja2, and persists
deliverables to Supabase.

## Features

* **Audio and video upload** — Accepts MP3, MP4 or M4A files and uses OpenAI
  Whisper to transcribe speech to text.
* **Transcript summarisation** — Generates structured summaries from raw
  transcripts via the OpenAI Chat API, returning highlights, goals, action
  items and next steps.
* **Branded deliverables** — Renders summaries into beautiful HTML using a
  Jinja2 template that accepts custom colours and logos. The resulting
  documents are ready to export as PDF or share via a private link.
* **Persistence** — Stores generated deliverables in Supabase for later
  retrieval. The MVP assumes a single user; row level security can be
  enabled for multi‑tenant deployments.

## Getting Started Locally

1. **Clone the repository** and change into the `momentum_backend` directory:

   ```bash
   git clone <this-repo> momentum_backend
   cd momentum_backend
   ```

2. **Create a virtual environment** and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure your environment**. Create a `.env` and fill in
   your own OpenAI and Supabase credentials.

4. **Start the development server**:

   ```bash
   uvicorn main:app --reload --port 8000
   ```

   The API will now be accessible at `http://localhost:8000`. You can
   browse the interactive Swagger UI at `http://localhost:8000/docs`.

## Deploying to the Cloud

There are many options for deploying FastAPI applications. One simple
approach is to use [Railway](https://railway.app), [Fly.io](https://fly.io) or
[Render](https://render.com). Below is a high‑level overview for deployment
using Render:

1. **Create a new web service** on Render and point it at this repository.
2. **Add your environment variables** (the same ones listed in `.env`). Make
   sure to set `OPENAI_API_KEY`, `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
3. **Set the build command** to `pip install -r requirements.txt` and the
   start command to `uvicorn main:app --host 0.0.0.0 --port 10000`.
4. **Expose port 10000** (or whichever port you configure). Render will
   automatically provide an HTTPS endpoint.

## Testing

You can test the API locally using `curl` or any HTTP client. For example,
posting a transcript directly:

```bash
curl -X POST http://localhost:8000/generate \
    -H "Content-Type: application/json" \
    -d '{
        "transcript": "Coach: We discussed marketing strategies...", 
        "client_name": "Acme Corp",
        "primary_color": "#2A3EB1",
        "secondary_color": "#4C6FE7"
    }'
```

The response will include a unique `id` and the rendered `html` string.

To upload an audio file:

```bash
curl -X POST http://localhost:8000/upload \
    -F "file=@session.mp3" \
    -F "client_name=Acme Corp" \
    -F "primary_color=#2A3EB1" \
    -F "secondary_color=#4C6FE7"
```

## Notes

* The current implementation does **not** include authentication. In a
  production system you should authenticate requests (e.g. via Supabase
  Auth) and restrict data access based on the user.
* For large audio files consider streaming the file directly to OpenAI
  rather than loading the entire file into memory.

# Zoom Integration API

The Zoom integration allows users to connect their Zoom accounts and automatically process meeting recordings to generate deliverables.

## Overview

The Zoom integration provides:
- OAuth 2.0 authentication with Zoom
- Automatic token refresh and credential management
- Meeting recording discovery and download
- Automatic transcription and deliverable generation
- Rate limiting and error handling

## Required Zoom Scopes

The application requires the following Zoom OAuth scopes:
- `recording:read` - Read cloud recordings
- `recording:write` - Manage cloud recordings
- `meeting:read` - Read meeting information
- `user:read` - Read user profile information

## Authentication Flow

### 1. Get Authorization URL

```http
GET /api/zoom/auth-url
Authorization: Bearer <token>
```

**Response:**
```json
{
  "auth_url": "https://zoom.us/oauth/authorize?response_type=code&client_id=...&redirect_uri=...&scope=..."
}
```

### 2. User Authorization
- Redirect user to the `auth_url`
- User grants permissions in Zoom
- Zoom redirects back with authorization code

### 3. Complete OAuth Flow

```http
POST /api/zoom/auth
Authorization: Bearer <token>
Content-Type: application/json

{
  "code": "authorization_code_from_zoom",
  "state": "optional_state_parameter"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Zoom account connected successfully",
  "zoom_user_id": "zoom_user_id",
  "zoom_email": "user@example.com"
}
```

## Meeting Management

### List Available Recordings

```http
GET /api/zoom/meetings?from_date=2024-01-01&to_date=2024-01-31&page_size=30&page_number=1
Authorization: Bearer <token>
```

**Query Parameters:**
- `from_date` (optional): Start date in YYYY-MM-DD format (default: 30 days ago)
- `to_date` (optional): End date in YYYY-MM-DD format (default: today)
- `page_size` (optional): Number of meetings per page (default: 30, max: 300)
- `page_number` (optional): Page number (default: 1)

**Response:**
```json
{
  "meetings": [
    {
      "id": "meeting_id",
      "uuid": "meeting_uuid",
      "topic": "Weekly Team Standup",
      "start_time": "2024-01-15T10:00:00Z",
      "duration": 45,
      "total_size": 124857600,
      "recording_count": 2,
      "recording_files": [
        {
          "id": "file_id_1",
          "meeting_id": "meeting_id",
          "file_type": "MP4",
          "file_size": 89123456,
          "download_url": "https://...",
          "recording_type": "shared_screen_with_speaker_view"
        },
        {
          "id": "file_id_2",
          "meeting_id": "meeting_id",
          "file_type": "M4A",
          "file_size": 35734144,
          "download_url": "https://...",
          "recording_type": "audio_only"
        }
      ]
    }
  ],
  "page_count": 3,
  "page_number": 1,
  "page_size": 30,
  "total_records": 87
}
```

### Download and Process Recording

```http
POST /api/zoom/download/{meeting_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "file_id": "recording_file_id",
  "process_immediately": true
}
```

**Path Parameters:**
- `meeting_id`: The Zoom meeting ID

**Request Body:**
- `file_id`: ID of the specific recording file to download
- `process_immediately`: Whether to transcribe and generate deliverable immediately (default: true)

**Response (with processing):**
```json
{
  "success": true,
  "message": "Recording downloaded and processed successfully. Deliverable created.",
  "deliverable_id": "generated_deliverable_id"
}
```

**Response (without processing):**
```json
{
  "success": true,
  "message": "Recording downloaded successfully"
}
```

## Account Management

### Check Connection Status

```http
GET /api/zoom/status
Authorization: Bearer <token>
```

**Response (connected):**
```json
{
  "connected": true,
  "token_expired": false,
  "zoom_email": "user@example.com",
  "connected_at": "2024-01-15T10:30:00Z"
}
```

**Response (not connected):**
```json
{
  "connected": false,
  "message": "No Zoom account connected"
}
```

### Disconnect Account

```http
DELETE /api/zoom/disconnect
Authorization: Bearer <token>
```

**Response:**
```json
{
  "message": "Zoom account disconnected successfully"
}
```

## Error Handling

### Common Error Responses

**No Zoom Account Connected (401):**
```json
{
  "detail": "No valid Zoom credentials found. Please connect your Zoom account."
}
```

**Token Expired (401):**
```json
{
  "detail": "Zoom credentials expired. Please reconnect your account."
}
```

**Rate Limit Exceeded (429):**
```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```

**Recording Not Found (404):**
```json
{
  "detail": "Recording file not found"
}
```

**Zoom API Error (400):**
```json
{
  "detail": "Zoom API error: Invalid meeting ID"
}
```

## Rate Limiting

The Zoom integration implements rate limiting to respect Zoom's API limits:

- **Request Rate**: 50 requests per second (conservative limit)
- **Automatic Backoff**: Built-in delays when approaching limits
- **Token Management**: Automatic token refresh when needed
- **Error Handling**: Graceful handling of rate limit responses

## Data Processing

### Supported File Types

The system can process the following Zoom recording types:
- `audio_only` - Audio-only recordings (M4A, MP3)
- `shared_screen_with_speaker_view` - Video with audio (MP4)
- `gallery_view` - Gallery view recordings (MP4)

### Processing Pipeline

1. **Download**: Secure download of recording file from Zoom
2. **Transcription**: OpenAI Whisper transcription for audio content
3. **Summarization**: GPT-4 analysis to extract insights
4. **Deliverable Generation**: HTML deliverable with meeting insights
5. **Storage**: Secure storage in user's account

### Generated Deliverables

Automatically generated deliverables include:
- Meeting highlights and key takeaways
- Action items with owners and due dates
- Goals and objectives discussed
- Next steps and follow-up items
- Meeting metadata (participants, duration, etc.)

## Security Considerations

### Credential Storage
- Zoom credentials encrypted in Supabase
- Automatic token refresh to maintain access
- Secure credential deletion on disconnect

### Data Access
- User-scoped access to recordings
- No cross-user data access
- Secure file downloads with temporary URLs

### API Security
- All endpoints require authentication
- Rate limiting to prevent abuse
- Input validation and sanitization
- Secure error handling without information leakage
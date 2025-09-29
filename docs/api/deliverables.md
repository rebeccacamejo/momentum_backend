# Deliverables API

The core functionality of Momentum is generating structured deliverables from session recordings. This API handles file uploads, transcript processing, and deliverable management.

## Overview

The deliverables system provides:
- Audio/video file upload and transcription
- Direct transcript processing
- Deliverable storage and retrieval
- PDF generation and export
- Brand customization

## Generate from Transcript

Create a deliverable from a raw transcript text.

```http
POST /generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "transcript": "This is the raw transcript of our coaching session...",
  "client_name": "Acme Corp Strategy Session",
  "user_id": "user_uuid",
  "template_type": "action_plan",
  "primary_color": "#2A3EB1",
  "secondary_color": "#4C6FE7",
  "logo_url": "https://example.com/logo.png"
}
```

**Response:**
```json
{
  "id": "deliverable_uuid",
  "html": "<html><body>...rendered deliverable...</body></html>"
}
```

## Upload and Process File

Upload an audio or video file for automatic transcription and processing.

```http
POST /upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=@recording.mp3
client_name=Team Standup
user_id=user_uuid
primary_color=#2A3EB1
secondary_color=#4C6FE7
logo_url=https://example.com/logo.png
template_type=action_plan
```

**Supported File Types:**
- Audio: MP3, M4A, WAV, FLAC
- Video: MP4, MOV, AVI (audio track extracted)
- Maximum size: 25MB per file

**Response:**
```json
{
  "id": "deliverable_uuid",
  "html": "<html><body>...rendered deliverable...</body></html>"
}
```

## List Deliverables

Retrieve a list of user's deliverables with pagination.

```http
GET /deliverables?user_id=user_uuid
Authorization: Bearer <token>
```

**Query Parameters:**
- `user_id` (required): User UUID for data filtering

**Response:**
```json
[
  {
    "id": "deliverable_uuid",
    "client_name": "Team Standup",
    "created_at": "2024-01-15T10:00:00Z"
  },
  {
    "id": "another_uuid",
    "client_name": "Client Strategy Session",
    "created_at": "2024-01-14T15:30:00Z"
  }
]
```

## Get Single Deliverable

Retrieve a specific deliverable's HTML content.

```http
GET /deliverables/{deliverable_id}?user_id=user_uuid
Authorization: Bearer <token>
```

**Path Parameters:**
- `deliverable_id`: The deliverable UUID

**Query Parameters:**
- `user_id` (required): User UUID for ownership verification

**Response:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Team Standup Session Report</title>
    <style>
        /* Styled with brand colors */
    </style>
</head>
<body>
    <!-- Structured deliverable content -->
</body>
</html>
```

## Generate PDF

Generate and download a PDF version of a deliverable.

```http
GET /deliverables/{deliverable_id}/pdf?user_id=user_uuid
Authorization: Bearer <token>
```

**Response:**
```json
{
  "url": "https://signed-url-to-pdf-file"
}
```

The signed URL is valid for 1 hour and provides direct access to the PDF file.

## Deliverable Structure

### Generated Content

Each deliverable contains:

1. **Session Header**
   - Client/session name
   - Date and time
   - Duration (if available)
   - Custom branding

2. **Key Highlights**
   - Most important takeaways
   - Critical insights
   - Key decisions made

3. **Goals & Objectives**
   - Goals discussed during session
   - Objectives identified
   - Success metrics defined

4. **Action Items**
   - Specific tasks to complete
   - Assigned owners
   - Due dates (if mentioned)

5. **Next Steps**
   - Follow-up actions
   - Future planning items
   - Recommendations

### Example Deliverable Content

```json
{
  "highlights": [
    "Team velocity has increased 20% this quarter",
    "New onboarding process reduces time-to-productivity",
    "Customer satisfaction scores at all-time high"
  ],
  "goals": [
    "Launch beta version by end of month",
    "Achieve 95% uptime for Q1",
    "Expand team by 3 developers"
  ],
  "action_items": [
    {
      "task": "Complete API documentation",
      "owner": "John Smith",
      "due_date": "2024-01-20"
    },
    {
      "task": "Set up monitoring dashboards",
      "owner": "Sarah Johnson",
      "due_date": "2024-01-25"
    }
  ],
  "next_steps": [
    "Schedule follow-up meeting for next week",
    "Review beta feedback and iterate",
    "Prepare for customer demo presentations"
  ]
}
```

## Brand Customization

### Brand Settings

Manage global brand settings for deliverables.

```http
GET /brand/settings
Authorization: Bearer <token>
```

**Response:**
```json
{
  "primary_color": "#2A3EB1",
  "secondary_color": "#4C6FE7",
  "logo_url": "https://example.com/logo.png"
}
```

### Update Brand Settings

```http
PUT /brand/settings
Authorization: Bearer <token>
Content-Type: application/json

{
  "primary_color": "#FF6B35",
  "secondary_color": "#F7931E",
  "logo_url": "https://example.com/new-logo.png"
}
```

### Logo Upload

```http
POST /brand/logo
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=@company-logo.png
```

**Supported Formats:**
- PNG, JPEG, SVG
- Maximum size: 5MB
- Recommended: 200x200px minimum

**Response:**
```json
{
  "url": "https://signed-url-to-uploaded-logo"
}
```

## Template Types

### Available Templates

1. **Action Plan** (`action_plan`)
   - Focus on actionable outcomes
   - Clear task assignments
   - Progress tracking elements

2. **Meeting Summary** (`meeting_summary`)
   - Comprehensive meeting recap
   - Decision documentation
   - Attendee summaries

3. **Coaching Session** (`coaching_session`)
   - Personal development focus
   - Goal setting framework
   - Progress milestones

### Template Customization

Templates can be customized with:
- Brand colors (primary and secondary)
- Company logo
- Custom fonts (future feature)
- Layout preferences (future feature)

## AI Processing Pipeline

### Transcription

Audio files are processed using OpenAI Whisper:
- Automatic language detection
- High accuracy transcription
- Noise reduction and cleanup
- Speaker identification (basic)

### Content Analysis

Transcripts are analyzed using GPT-4:
- Intelligent content extraction
- Context-aware summarization
- Action item identification
- Goal and objective recognition

### Quality Assurance

- Validation of extracted content
- Fallback handling for incomplete data
- Error detection and correction
- Content completeness verification

## Error Handling

### File Upload Errors

**File Too Large (413):**
```json
{
  "detail": "File size exceeds 25MB limit"
}
```

**Unsupported Format (415):**
```json
{
  "detail": "Unsupported file type. Use MP3, MP4, M4A, or WAV"
}
```

**Transcription Failed (500):**
```json
{
  "detail": "Transcription failed: audio quality too low"
}
```

### Processing Errors

**Invalid Transcript (400):**
```json
{
  "detail": "Transcript is too short or empty"
}
```

**AI Processing Failed (500):**
```json
{
  "detail": "Failed to process transcript: service temporarily unavailable"
}
```

### Access Errors

**Deliverable Not Found (404):**
```json
{
  "detail": "Deliverable not found"
}
```

**Access Denied (403):**
```json
{
  "detail": "Access denied: deliverable belongs to another user"
}
```

## Performance Considerations

### File Processing

- **Async Processing**: Large files processed asynchronously
- **Progress Tracking**: Real-time processing status (future feature)
- **Queue Management**: Fair processing queue for concurrent uploads

### Caching

- **Template Caching**: Rendered templates cached for performance
- **Asset Caching**: Logos and static assets cached with CDN
- **Database Optimization**: Efficient queries with proper indexing

### Rate Limiting

- **Upload Limits**: 10 uploads per hour per user
- **Processing Limits**: 5 concurrent processing jobs per user
- **API Limits**: Standard rate limiting on all endpoints

## Data Privacy & Security

### Data Handling

- **Secure Storage**: All files encrypted at rest
- **User Isolation**: Complete data separation between users
- **Retention Policy**: Files deleted after processing (optional retention)
- **Privacy Compliance**: GDPR and SOC2 compliant processing

### Access Control

- **User Authentication**: Required for all operations
- **Ownership Verification**: Strict user ID validation
- **Secure URLs**: Time-limited signed URLs for file access

### Audit Trail

- **Processing Logs**: Complete audit trail of all operations
- **Access Logs**: Tracking of all data access
- **Error Monitoring**: Comprehensive error tracking and alerting
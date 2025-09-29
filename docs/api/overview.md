# API Overview

The Momentum backend provides a comprehensive REST API for session management, deliverable generation, and third-party integrations.

## Base URL

```
http://localhost:8000  # Development
https://api.momentum.com  # Production
```

## API Design Principles

### RESTful Design
- Uses standard HTTP methods (GET, POST, PUT, DELETE)
- Meaningful resource URLs with clear hierarchies
- Consistent response formats

### Authentication
- JWT-based authentication using Supabase Auth
- User-scoped data access with proper isolation
- Optional authentication for some endpoints

### Error Handling
- Standard HTTP status codes
- Consistent error response format:
```json
{
  "detail": "Error description"
}
```

### Response Format
- JSON responses for all endpoints
- Consistent data structure using Pydantic models
- Proper HTTP status codes

## API Categories

### Core Endpoints
- **Health Check**: `GET /` - Service health status
- **File Upload**: `POST /upload` - Process audio/video files
- **Generate**: `POST /generate` - Generate deliverables from transcript
- **Deliverables**: `GET /deliverables` - List and retrieve deliverables

### Authentication Endpoints
- **Magic Link**: `POST /auth/magic-link` - Send authentication email
- **Callback**: `POST /auth/callback` - Handle auth callback
- **Refresh**: `POST /auth/refresh` - Refresh access tokens
- **Sign Out**: `POST /auth/signout` - User sign out
- **Profile**: `GET/PUT /auth/user` - User profile management

### Organization Endpoints
- **List**: `GET /organizations` - User's organizations
- **Create**: `POST /organizations` - Create new organization
- **Manage**: `GET/PUT /organizations/{id}` - Organization management
- **Members**: CRUD operations for organization members

### Zoom Integration Endpoints
- **Auth URL**: `GET /api/zoom/auth-url` - Get OAuth URL
- **Authenticate**: `POST /api/zoom/auth` - Complete OAuth flow
- **Meetings**: `GET /api/zoom/meetings` - List available recordings
- **Download**: `POST /api/zoom/download/{meeting_id}` - Download and process
- **Status**: `GET /api/zoom/status` - Connection status
- **Disconnect**: `DELETE /api/zoom/disconnect` - Remove integration

### Brand Management
- **Settings**: `GET/PUT /brand/settings` - Brand customization
- **Logo Upload**: `POST /brand/logo` - Upload brand logo

## Authentication

Most endpoints require authentication using Bearer tokens:

```http
Authorization: Bearer <jwt_token>
```

### User Context
Authenticated endpoints automatically receive user context through dependency injection. The user's ID is used for data filtering and access control.

## Rate Limiting

### External API Rate Limiting
- Zoom API: 80 requests/second (conservative: 50/second)
- OpenAI API: Built-in retry logic with exponential backoff

### Error Handling
- 429 status code for rate limit exceeded
- Automatic retry with appropriate delays
- Graceful degradation when services are unavailable

## Data Validation

### Request Validation
- Pydantic models for request/response validation
- Automatic validation error responses (422 status)
- Type safety with proper error messages

### Response Models
All endpoints use Pydantic response models for consistent data structure:

```python
class GenerateResponse(BaseModel):
    id: str
    html: str
```

## Pagination

List endpoints support pagination:

```http
GET /api/zoom/meetings?page_size=30&page_number=1
```

Response includes pagination metadata:
```json
{
  "meetings": [...],
  "page_count": 5,
  "page_number": 1,
  "page_size": 30,
  "total_records": 150
}
```

## CORS Policy

Configured for cross-origin requests:
- Allows all origins in development
- Restricted to specific domains in production
- Supports credentials for authenticated requests

## Content Types

### Supported Input
- `application/json` for API requests
- `multipart/form-data` for file uploads
- `application/x-www-form-urlencoded` for OAuth callbacks

### Response Types
- `application/json` for API responses
- `text/html` for deliverable content
- `application/pdf` for PDF exports
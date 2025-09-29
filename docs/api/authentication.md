# Authentication API

The Momentum backend uses Supabase Auth for user authentication with magic link support and JWT token management.

## Authentication Flow

### Magic Link Authentication

The system uses passwordless authentication via magic links sent to user email addresses.

```http
POST /auth/magic-link
Content-Type: application/json

{
  "email": "user@example.com",
  "redirect_to": "http://localhost:3000/auth/callback"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Magic link sent to your email"
}
```

### Authentication Callback

After clicking the magic link, users are redirected to handle the authentication callback:

```http
POST /auth/callback
Content-Type: application/x-www-form-urlencoded

access_token=jwt_token&refresh_token=refresh_token&expires_in=3600&token_type=bearer
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "refresh_token_string",
  "user": {
    "id": "user_uuid",
    "email": "user@example.com",
    "created_at": "2024-01-15T10:00:00Z"
  },
  "expires_in": 3600
}
```

### Token Refresh

Refresh expired access tokens using the refresh token:

```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "refresh_token_string"
}
```

**Response:**
```json
{
  "access_token": "new_jwt_token",
  "refresh_token": "new_refresh_token",
  "user": {
    "id": "user_uuid",
    "email": "user@example.com"
  },
  "expires_in": 3600
}
```

## User Profile Management

### Get User Profile

```http
GET /auth/user
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "user_uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "avatar_url": "https://example.com/avatar.jpg",
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

### Update User Profile

```http
PUT /auth/user
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "John Doe",
  "avatar_url": "https://example.com/new-avatar.jpg"
}
```

**Response:**
```json
{
  "id": "user_uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "avatar_url": "https://example.com/new-avatar.jpg",
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T14:30:00Z"
}
```

## Sign Out

```http
POST /auth/signout
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "message": "Successfully signed out"
}
```

## JWT Token Structure

### Token Claims

The JWT access token contains the following claims:

```json
{
  "aud": "authenticated",
  "exp": 1705401600,
  "iat": 1705398000,
  "iss": "https://your-project.supabase.co/auth/v1",
  "sub": "user_uuid",
  "email": "user@example.com",
  "role": "authenticated",
  "session_id": "session_uuid"
}
```

### Token Validation

All protected endpoints validate JWT tokens automatically through FastAPI dependency injection:

```python
@app.get("/protected-endpoint")
async def protected_endpoint(current_user: Dict[str, Any] = Depends(get_current_user)):
    # current_user contains validated user information
    return {"user_id": current_user["id"]}
```

## Protected Endpoints

Most endpoints require authentication. The authentication dependency provides:

- **User ID**: `current_user["id"]` - UUID of authenticated user
- **Email**: `current_user["email"]` - User's email address
- **Metadata**: Additional user metadata from Supabase Auth

### Example Protected Endpoint Usage

```python
async def some_endpoint(current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id = current_user["id"]
    # All data operations are scoped to this user_id
    deliverables = get_user_deliverables(user_id)
    return deliverables
```

## Error Handling

### Authentication Errors

**Invalid Token (401):**
```json
{
  "detail": "Invalid authentication credentials"
}
```

**Expired Token (401):**
```json
{
  "detail": "Token has expired"
}
```

**Missing Token (401):**
```json
{
  "detail": "Not authenticated"
}
```

**Magic Link Send Failed (400):**
```json
{
  "detail": "Failed to send magic link: invalid email"
}
```

**Profile Update Failed (400):**
```json
{
  "detail": "Failed to update profile: validation error"
}
```

## Security Features

### Row Level Security (RLS)

All user data is protected by PostgreSQL Row Level Security policies:

```sql
-- Users can only access their own deliverables
CREATE POLICY "Users can access own deliverables" ON deliverables
    FOR ALL USING (auth.uid() = user_id);
```

### Token Security

- **JWT Signing**: Tokens signed with secure secret key
- **Short Expiration**: Access tokens expire in 1 hour
- **Automatic Refresh**: Refresh tokens for seamless experience
- **Secure Storage**: Tokens should be stored securely on client side

### Data Isolation

Every authenticated request automatically filters data by user ID:

```python
# All deliverables endpoints filter by user
@app.get("/deliverables")
async def list_deliverables(user_id: str, current_user = Depends(get_current_user)):
    # user_id parameter is required and validated against current_user
    if user_id != current_user["id"]:
        raise HTTPException(403, "Access denied")
```

## Development vs Production

### Development Configuration

```python
# Allow any origin for CORS during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Production Configuration

```python
# Restrict CORS to known domains in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.momentum.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

## Integration with Frontend

### Authentication Flow

1. **Frontend** sends email to `/auth/magic-link`
2. **User** clicks magic link in email
3. **Supabase** redirects to frontend callback URL
4. **Frontend** extracts tokens from URL and sends to `/auth/callback`
5. **Backend** validates tokens and returns user session
6. **Frontend** stores tokens and makes authenticated requests

### Token Storage

Recommended token storage on frontend:

```javascript
// Store tokens securely
localStorage.setItem('access_token', response.access_token);
localStorage.setItem('refresh_token', response.refresh_token);

// Include in API requests
const headers = {
  'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
  'Content-Type': 'application/json'
};
```

### Automatic Token Refresh

Frontend should implement automatic token refresh:

```javascript
// Check if token is expired before requests
if (isTokenExpired(accessToken)) {
  const newTokens = await refreshTokens(refreshToken);
  // Update stored tokens
  localStorage.setItem('access_token', newTokens.access_token);
  localStorage.setItem('refresh_token', newTokens.refresh_token);
}
```

## Rate Limiting

Authentication endpoints have rate limiting to prevent abuse:

- **Magic Link**: 5 requests per minute per IP
- **Token Refresh**: 10 requests per minute per user
- **Profile Updates**: 20 requests per minute per user

Rate limit exceeded responses:
```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```
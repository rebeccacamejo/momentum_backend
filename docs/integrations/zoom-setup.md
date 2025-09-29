# Zoom Integration Setup Guide

This guide walks through setting up the Zoom OAuth integration for the Momentum backend.

## Prerequisites

- Zoom Developer Account
- Admin access to Zoom account (for app approval)
- Momentum backend deployed with accessible URL

## Step 1: Create Zoom OAuth App

### 1.1 Access Zoom Marketplace

1. Go to [Zoom Marketplace](https://marketplace.zoom.us/)
2. Sign in with your Zoom developer account
3. Click "Develop" → "Build App"

### 1.2 Create OAuth App

1. Select "OAuth" app type
2. Choose "User-managed app" (not account-level)
3. Fill in basic app information:

   ```
   App Name: Momentum Session Processor
   Short Description: AI-powered meeting recording processor
   Company Name: Your Company
   Developer Email: your-email@company.com
   ```

### 1.3 Configure App Details

**App Information:**
- Add app logo (optional)
- Add detailed description
- Select appropriate category (e.g., "Productivity")

**OAuth Information:**
- Redirect URL for OAuth: `https://your-domain.com/api/zoom/auth`
- Add development URL: `http://localhost:8000/api/zoom/auth`
- OAuth scopes (see Step 2)

## Step 2: Configure OAuth Scopes

Add the following scopes to your Zoom OAuth app:

### Required Scopes

| Scope | Description | Why Needed |
|-------|-------------|------------|
| `recording:read` | View cloud recordings | Download meeting recordings |
| `recording:write` | Manage cloud recordings | Access recording metadata |
| `meeting:read` | View meeting information | Get meeting details and participants |
| `user:read` | View user profile | Get user information for account linking |

### Scope Configuration

1. In your Zoom app dashboard, go to "Scopes"
2. Add each required scope
3. Provide justification for each scope:
   - Recording access: "To download and process meeting recordings"
   - Meeting access: "To retrieve meeting metadata and participant information"
   - User access: "To identify the connected user account"

## Step 3: App Review and Publishing

### 3.1 Development Phase

For development, your app can be used immediately with:
- Test users only
- Limited to your Zoom account
- No public distribution

### 3.2 Production Publishing

For production use:

1. **Complete App Information:**
   - Detailed app description
   - Privacy policy URL
   - Terms of service URL
   - Support contact information

2. **Submit for Review:**
   - Zoom reviews OAuth apps before public availability
   - Review process typically takes 3-5 business days
   - May require additional documentation

3. **App Approval:**
   - Once approved, app is available to all Zoom users
   - Can be listed in Zoom App Marketplace (optional)

## Step 4: Get App Credentials

### 4.1 Obtain Credentials

1. Go to your Zoom app dashboard
2. Navigate to "App Credentials" section
3. Copy the following:
   - **Client ID**: Public identifier for your app
   - **Client Secret**: Private key for OAuth flow (keep secure!)

### 4.2 Environment Configuration

Add credentials to your environment configuration:

```bash
# .env
ZOOM_CLIENT_ID=your-client-id-here
ZOOM_CLIENT_SECRET=your-client-secret-here
ZOOM_REDIRECT_URI=http://localhost:8000/api/zoom/auth
```

### 4.3 Production Configuration

For production, update the redirect URI:

```bash
# .env.production
ZOOM_CLIENT_ID=your-production-client-id
ZOOM_CLIENT_SECRET=your-production-client-secret
ZOOM_REDIRECT_URI=https://api.momentum.com/api/zoom/auth
```

## Step 5: Test Integration

### 5.1 Test OAuth Flow

1. Start your backend server:
   ```bash
   uvicorn main:app --reload
   ```

2. Test the auth URL endpoint:
   ```bash
   curl -H "Authorization: Bearer YOUR_JWT" \
        http://localhost:8000/api/zoom/auth-url
   ```

3. Visit the returned auth URL in browser
4. Grant permissions in Zoom
5. Verify successful callback handling

### 5.2 Test API Access

After authentication, test recording access:

```bash
# List recordings
curl -H "Authorization: Bearer YOUR_JWT" \
     "http://localhost:8000/api/zoom/meetings"

# Check connection status
curl -H "Authorization: Bearer YOUR_JWT" \
     "http://localhost:8000/api/zoom/status"
```

## Step 6: Production Deployment

### 6.1 Update Redirect URIs

In Zoom app settings, add production URLs:
- Production: `https://api.momentum.com/api/zoom/auth`
- Staging: `https://api-staging.momentum.com/api/zoom/auth`

### 6.2 Environment Variables

Ensure production environment has correct variables:

```bash
# Production
ZOOM_CLIENT_ID=prod-client-id
ZOOM_CLIENT_SECRET=prod-client-secret
ZOOM_REDIRECT_URI=https://api.momentum.com/api/zoom/auth
FRONTEND_URL=https://app.momentum.com
```

### 6.3 SSL Certificate

Ensure your production domain has valid SSL certificate:
- Zoom requires HTTPS for production OAuth apps
- Use Let's Encrypt, CloudFlare, or commercial certificate
- Verify certificate is trusted by major browsers

## Security Considerations

### 6.1 Client Secret Protection

- **Never expose client secret in frontend code**
- Store securely in environment variables
- Rotate regularly (every 6-12 months)
- Use different secrets for different environments

### 6.2 Scope Minimization

- Only request scopes your app actually needs
- Review and remove unused scopes regularly
- Document why each scope is required

### 6.3 Token Management

- Store OAuth tokens encrypted in database
- Implement automatic token refresh
- Set appropriate token expiration times
- Provide easy disconnection for users

## Troubleshooting

### Common Issues

**Invalid Redirect URI:**
```
Error: redirect_uri_mismatch
```
- Verify redirect URI exactly matches Zoom app config
- Check for trailing slashes, HTTP vs HTTPS
- Ensure environment variable is correct

**Insufficient Scopes:**
```
Error: insufficient_scope
```
- Check required scopes are added to Zoom app
- Verify scopes in OAuth URL match app configuration
- Re-authenticate if scopes were added after initial auth

**App Not Approved:**
```
Error: app_not_approved
```
- Complete app review process in Zoom dashboard
- Ensure all required fields are filled
- Contact Zoom support if review is delayed

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In zoom_service.py
logger.debug(f"OAuth URL: {auth_url}")
logger.debug(f"Token response: {response.json()}")
```

### Rate Limiting

Monitor Zoom API rate limits:
- 80 requests per second per app
- Daily limits based on app type
- Implement exponential backoff for 429 responses

## Support and Resources

### Zoom Documentation

- [OAuth App Development](https://developers.zoom.us/docs/integrations/oauth/)
- [Recording API Reference](https://developers.zoom.us/docs/api/rest/reference/cloud-recording/)
- [Rate Limiting Guidelines](https://developers.zoom.us/docs/api/rest/rate-limits/)

### Zoom Support

- [Developer Forum](https://devforum.zoom.us/)
- [Support Tickets](https://support.zoom.us/hc/en-us/requests/new)
- [Status Page](https://status.zoom.us/)

### Testing Tools

- [Zoom API Explorer](https://developers.zoom.us/playground/)
- [OAuth Testing Tool](https://oauth.tools/)
- [JWT Debugger](https://jwt.io/)

## Compliance and Legal

### Data Usage

- Review Zoom's data usage policies
- Implement appropriate data retention policies
- Ensure compliance with GDPR, CCPA, etc.
- Provide clear privacy policy to users

### Terms of Service

- Follow Zoom's API Terms of Service
- Don't store unnecessary user data
- Respect user privacy and consent
- Implement proper data deletion workflows
# Environment Configuration

This document outlines all environment variables required for the Momentum backend and their configuration across different environments.

## Required Environment Variables

### Supabase Configuration

```bash
# Supabase project URL
SUPABASE_URL=https://your-project-id.supabase.co

# Supabase anonymous key (public)
SUPABASE_ANON_KEY=your-anon-key

# Supabase service role key (private, full access)
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# JWT secret for token validation
SUPABASE_JWT_SECRET=your-jwt-secret
```

**Notes:**
- `SUPABASE_URL` is your project's API endpoint
- `SUPABASE_ANON_KEY` is safe to use in client-side code
- `SUPABASE_SERVICE_ROLE_KEY` bypasses RLS - use carefully
- `SUPABASE_JWT_SECRET` is used to verify JWT tokens

### OpenAI Configuration

```bash
# OpenAI API key for transcription and summarization
OPENAI_API_KEY=sk-your-openai-api-key
```

**Notes:**
- Required for Whisper transcription and GPT-4 summarization
- Get from: https://platform.openai.com/api-keys
- Monitor usage to avoid unexpected charges

### Zoom Integration

```bash
# Zoom OAuth app credentials
ZOOM_CLIENT_ID=your-zoom-client-id
ZOOM_CLIENT_SECRET=your-zoom-client-secret

# OAuth redirect URI (must match Zoom app config)
ZOOM_REDIRECT_URI=http://localhost:8000/api/zoom/auth
```

**Notes:**
- Create Zoom OAuth app at: https://marketplace.zoom.us/
- `ZOOM_REDIRECT_URI` must be registered in Zoom app settings
- Use appropriate URL for each environment

### Frontend Configuration

```bash
# Frontend URL for CORS and redirects
FRONTEND_URL=http://localhost:3000
```

**Notes:**
- Used for CORS policy configuration
- Used in magic link redirects
- Update for each environment

## Environment-Specific Configurations

### Development Environment

**File**: `.env.development`

```bash
# Supabase (Development Project)
SUPABASE_URL=https://dev-project-id.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_JWT_SECRET=your-dev-jwt-secret

# OpenAI (Development/Testing)
OPENAI_API_KEY=sk-dev-key-with-rate-limits

# Zoom (Development App)
ZOOM_CLIENT_ID=dev-zoom-client-id
ZOOM_CLIENT_SECRET=dev-zoom-client-secret
ZOOM_REDIRECT_URI=http://localhost:8000/api/zoom/auth

# Frontend
FRONTEND_URL=http://localhost:3000

# Debug Settings
DEBUG=true
LOG_LEVEL=debug
```

### Staging Environment

**File**: `.env.staging`

```bash
# Supabase (Staging Project)
SUPABASE_URL=https://staging-project-id.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_JWT_SECRET=your-staging-jwt-secret

# OpenAI (Production Key with Monitoring)
OPENAI_API_KEY=sk-staging-key

# Zoom (Staging App)
ZOOM_CLIENT_ID=staging-zoom-client-id
ZOOM_CLIENT_SECRET=staging-zoom-client-secret
ZOOM_REDIRECT_URI=https://api-staging.momentum.com/api/zoom/auth

# Frontend
FRONTEND_URL=https://app-staging.momentum.com

# Production-like Settings
DEBUG=false
LOG_LEVEL=info
```

### Production Environment

**File**: `.env.production`

```bash
# Supabase (Production Project)
SUPABASE_URL=https://prod-project-id.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_JWT_SECRET=your-production-jwt-secret

# OpenAI (Production Key with Monitoring)
OPENAI_API_KEY=sk-production-key

# Zoom (Production App)
ZOOM_CLIENT_ID=prod-zoom-client-id
ZOOM_CLIENT_SECRET=prod-zoom-client-secret
ZOOM_REDIRECT_URI=https://api.momentum.com/api/zoom/auth

# Frontend
FRONTEND_URL=https://app.momentum.com

# Production Settings
DEBUG=false
LOG_LEVEL=warning
SENTRY_DSN=https://your-sentry-dsn
```

## Loading Environment Variables

### Local Development

1. **Copy example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your values:**
   ```bash
   nano .env
   ```

3. **Variables are loaded automatically:**
   ```python
   from dotenv import load_dotenv
   load_dotenv()  # Loads .env file
   ```

### Docker Deployment

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  momentum-backend:
    build: .
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ZOOM_CLIENT_ID=${ZOOM_CLIENT_ID}
      - ZOOM_CLIENT_SECRET=${ZOOM_CLIENT_SECRET}
      - ZOOM_REDIRECT_URI=${ZOOM_REDIRECT_URI}
      - FRONTEND_URL=${FRONTEND_URL}
    env_file:
      - .env.production
```

### Cloud Deployment

#### Heroku
```bash
# Set environment variables
heroku config:set SUPABASE_URL=https://your-project.supabase.co
heroku config:set SUPABASE_ANON_KEY=your-anon-key
heroku config:set OPENAI_API_KEY=sk-your-key
# ... set all required variables
```

#### Vercel
```bash
# Using Vercel CLI
vercel env add SUPABASE_URL
vercel env add SUPABASE_ANON_KEY
# ... add all required variables
```

#### AWS/Google Cloud
Set environment variables through the cloud provider's interface or configuration files.

## Security Best Practices

### Sensitive Data Handling

1. **Never commit `.env` files to version control**
   ```bash
   # Add to .gitignore
   echo ".env*" >> .gitignore
   echo "!.env.example" >> .gitignore
   ```

2. **Use different keys for each environment**
   - Development: Limited permissions/quotas
   - Staging: Production-like but separate
   - Production: Full permissions, monitored

3. **Rotate keys regularly**
   - Set calendar reminders for key rotation
   - Have backup keys ready for zero-downtime rotation
   - Monitor key usage for anomalies

### Environment Isolation

```python
# Validate environment on startup
def validate_environment():
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'OPENAI_API_KEY'
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing required environment variables: {missing}")
```

## Configuration Validation

### Startup Checks

```python
# config.py
import os
from typing import Optional

class Config:
    # Supabase
    SUPABASE_URL: str = os.getenv('SUPABASE_URL', '')
    SUPABASE_ANON_KEY: str = os.getenv('SUPABASE_ANON_KEY', '')
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')

    # OpenAI
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')

    # Zoom
    ZOOM_CLIENT_ID: Optional[str] = os.getenv('ZOOM_CLIENT_ID')
    ZOOM_CLIENT_SECRET: Optional[str] = os.getenv('ZOOM_CLIENT_SECRET')
    ZOOM_REDIRECT_URI: Optional[str] = os.getenv('ZOOM_REDIRECT_URI')

    # Frontend
    FRONTEND_URL: str = os.getenv('FRONTEND_URL', 'http://localhost:3000')

    # Optional
    DEBUG: bool = os.getenv('DEBUG', 'false').lower() == 'true'
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'info').lower()

    def validate(self):
        """Validate required configuration"""
        errors = []

        if not self.SUPABASE_URL:
            errors.append("SUPABASE_URL is required")
        if not self.SUPABASE_ANON_KEY:
            errors.append("SUPABASE_ANON_KEY is required")
        if not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required")

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

# Usage in main.py
config = Config()
config.validate()
```

## Monitoring and Logging

### Environment-Specific Logging

```python
import logging
import os

# Configure logging based on environment
log_level = os.getenv('LOG_LEVEL', 'info').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if os.getenv('DEBUG', 'false').lower() == 'true':
    # Enable debug logging for development
    logging.getLogger('httpx').setLevel(logging.DEBUG)
    logging.getLogger('supabase').setLevel(logging.DEBUG)
```

### Health Check Endpoint

```python
@app.get("/health")
async def health_check():
    """Health check with environment validation"""
    try:
        # Test Supabase connection
        supabase = get_supabase()
        supabase.table('profiles').select('count').limit(1).execute()

        return {
            "status": "healthy",
            "environment": os.getenv('ENVIRONMENT', 'development'),
            "version": "1.0.0",
            "services": {
                "supabase": "connected",
                "openai": "configured" if os.getenv('OPENAI_API_KEY') else "missing",
                "zoom": "configured" if os.getenv('ZOOM_CLIENT_ID') else "missing"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

## Troubleshooting

### Common Issues

**Supabase Connection Errors:**
```bash
# Check URL format
echo $SUPABASE_URL
# Should be: https://project-id.supabase.co

# Verify keys are not empty
echo ${#SUPABASE_ANON_KEY}  # Should be > 100 characters
```

**OpenAI API Errors:**
```bash
# Test API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models
```

**Zoom OAuth Errors:**
```bash
# Verify redirect URI matches exactly
echo $ZOOM_REDIRECT_URI
# Must match Zoom app configuration exactly
```

### Debug Mode

Enable debug mode for verbose logging:
```bash
export DEBUG=true
export LOG_LEVEL=debug
```

This will provide detailed logging for troubleshooting configuration issues.
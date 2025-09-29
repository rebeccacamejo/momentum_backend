"""
Zoom API Service

This service handles all Zoom API interactions including OAuth 2.0 authentication,
fetching meeting recordings, downloading media files, and managing user credentials.
It implements rate limiting, error handling, and secure credential storage.
"""

import os
import time
import logging
import asyncio
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlencode, parse_qs, urlparse

import httpx
from fastapi import HTTPException

from utils.supabase_client import get_supabase

# Configure logging
logger = logging.getLogger(__name__)


class ZoomRateLimiter:
    """Rate limiter for Zoom API calls to respect their limits."""

    def __init__(self):
        self.last_call = 0
        self.call_count = 0
        self.reset_time = 0

    async def wait_if_needed(self):
        """Wait if we're hitting rate limits."""
        current_time = time.time()

        # Reset counter every hour
        if current_time > self.reset_time:
            self.call_count = 0
            self.reset_time = current_time + 3600  # 1 hour

        # Zoom allows 80 requests per second, we'll be conservative with 50
        time_since_last = current_time - self.last_call
        if time_since_last < 0.02:  # 50 requests per second
            await asyncio.sleep(0.02 - time_since_last)

        self.last_call = time.time()
        self.call_count += 1


class ZoomAPIError(Exception):
    """Custom exception for Zoom API errors."""

    def __init__(self, message: str, status_code: int = None, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class ZoomService:
    """Service for interacting with Zoom APIs."""

    def __init__(self):
        self.client_id = os.getenv('ZOOM_CLIENT_ID')
        self.client_secret = os.getenv('ZOOM_CLIENT_SECRET')
        self.redirect_uri = os.getenv('ZOOM_REDIRECT_URI')
        self.base_url = 'https://api.zoom.us/v2'
        self.oauth_base_url = 'https://zoom.us/oauth'
        self.rate_limiter = ZoomRateLimiter()

        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("Missing required Zoom configuration. Check ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET, and ZOOM_REDIRECT_URI environment variables.")

    def get_authorization_url(self, state: str = None) -> str:
        """Generate Zoom OAuth authorization URL."""
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'recording:read recording:write meeting:read user:read'
        }

        if state:
            params['state'] = state

        return f"{self.oauth_base_url}/authorize?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        await self.rate_limiter.wait_if_needed()

        # Prepare credentials for Basic Auth
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.oauth_base_url}/token",
                headers=headers,
                data=data
            )

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
            raise ZoomAPIError(
                f"Failed to exchange code for tokens: {response.text}",
                status_code=response.status_code
            )

        return response.json()

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        await self.rate_limiter.wait_if_needed()

        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.oauth_base_url}/token",
                headers=headers,
                data=data
            )

        if response.status_code != 200:
            logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
            raise ZoomAPIError(
                f"Failed to refresh token: {response.text}",
                status_code=response.status_code
            )

        return response.json()

    async def _make_authenticated_request(
        self,
        method: str,
        endpoint: str,
        access_token: str,
        params: Dict = None,
        json_data: Dict = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Zoom API with automatic token refresh."""
        await self.rate_limiter.wait_if_needed()

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data
            )

        if response.status_code == 401:
            raise ZoomAPIError(
                "Access token expired or invalid",
                status_code=401,
                error_code="token_expired"
            )
        elif response.status_code == 429:
            logger.warning("Rate limit exceeded, waiting...")
            await asyncio.sleep(60)  # Wait 1 minute
            return await self._make_authenticated_request(method, endpoint, access_token, params, json_data)
        elif response.status_code >= 400:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            raise ZoomAPIError(
                f"Zoom API error: {error_data.get('message', response.text)}",
                status_code=response.status_code,
                error_code=error_data.get('code')
            )

        return response.json()

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get current user information."""
        return await self._make_authenticated_request('GET', '/users/me', access_token)

    async def list_recordings(
        self,
        access_token: str,
        user_id: str = 'me',
        from_date: datetime = None,
        to_date: datetime = None,
        page_size: int = 30,
        page_number: int = 1
    ) -> Dict[str, Any]:
        """List cloud recordings for a user."""
        params = {
            'page_size': page_size,
            'page_number': page_number
        }

        # Default to last 30 days if no dates provided
        if not from_date:
            from_date = datetime.now() - timedelta(days=30)
        if not to_date:
            to_date = datetime.now()

        params['from'] = from_date.strftime('%Y-%m-%d')
        params['to'] = to_date.strftime('%Y-%m-%d')

        return await self._make_authenticated_request(
            'GET',
            f'/users/{user_id}/recordings',
            access_token,
            params=params
        )

    async def get_meeting_recordings(self, access_token: str, meeting_id: str) -> Dict[str, Any]:
        """Get recordings for a specific meeting."""
        return await self._make_authenticated_request(
            'GET',
            f'/meetings/{meeting_id}/recordings',
            access_token
        )

    async def download_recording_file(
        self,
        access_token: str,
        download_url: str
    ) -> bytes:
        """Download a recording file from Zoom."""
        await self.rate_limiter.wait_if_needed()

        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minute timeout for downloads
            response = await client.get(download_url, headers=headers)

        if response.status_code != 200:
            raise ZoomAPIError(
                f"Failed to download recording: {response.status_code}",
                status_code=response.status_code
            )

        return response.content

    async def get_meeting_participants(self, access_token: str, meeting_uuid: str) -> Dict[str, Any]:
        """Get participants for a meeting."""
        # URL encode the meeting UUID as it may contain special characters
        encoded_uuid = meeting_uuid.replace('/', '%2F').replace('+', '%2B').replace('=', '%3D')

        return await self._make_authenticated_request(
            'GET',
            f'/meetings/{encoded_uuid}/participants',
            access_token
        )


class ZoomCredentialService:
    """Service for managing Zoom credentials in Supabase."""

    def __init__(self):
        self.supabase = get_supabase()

    async def store_credentials(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        zoom_user_id: str = None,
        zoom_email: str = None
    ) -> bool:
        """Store Zoom credentials for a user."""
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        data = {
            'user_id': user_id,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_at': expires_at.isoformat(),
            'zoom_user_id': zoom_user_id,
            'zoom_email': zoom_email,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        try:
            # Use upsert to handle updates
            response = self.supabase.table('zoom_credentials').upsert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to store Zoom credentials: {e}")
            return False

    async def get_credentials(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get Zoom credentials for a user."""
        try:
            response = self.supabase.table('zoom_credentials')\
                .select('*')\
                .eq('user_id', user_id)\
                .single()\
                .execute()

            return response.data if hasattr(response, 'data') and response.data else None
        except Exception as e:
            logger.error(f"Failed to get Zoom credentials: {e}")
            return None

    async def update_tokens(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int
    ) -> bool:
        """Update tokens for a user."""
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        try:
            response = self.supabase.table('zoom_credentials')\
                .update({
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'expires_at': expires_at.isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                })\
                .eq('user_id', user_id)\
                .execute()

            return True
        except Exception as e:
            logger.error(f"Failed to update Zoom tokens: {e}")
            return False

    async def delete_credentials(self, user_id: str) -> bool:
        """Delete Zoom credentials for a user."""
        try:
            response = self.supabase.table('zoom_credentials')\
                .delete()\
                .eq('user_id', user_id)\
                .execute()

            return True
        except Exception as e:
            logger.error(f"Failed to delete Zoom credentials: {e}")
            return False

    async def is_token_expired(self, user_id: str) -> bool:
        """Check if access token is expired."""
        credentials = await self.get_credentials(user_id)
        if not credentials or not credentials.get('expires_at'):
            return True

        expires_at = datetime.fromisoformat(credentials['expires_at'].replace('Z', '+00:00'))
        return datetime.utcnow() > expires_at

    async def get_valid_access_token(self, user_id: str) -> Optional[str]:
        """Get a valid access token, refreshing if necessary."""
        credentials = await self.get_credentials(user_id)
        if not credentials:
            return None

        # Check if token is expired
        if await self.is_token_expired(user_id):
            # Try to refresh the token
            zoom_service = ZoomService()
            try:
                token_data = await zoom_service.refresh_access_token(credentials['refresh_token'])

                # Update stored credentials
                await self.update_tokens(
                    user_id,
                    token_data['access_token'],
                    token_data['refresh_token'],
                    token_data['expires_in']
                )

                return token_data['access_token']
            except ZoomAPIError:
                logger.error(f"Failed to refresh token for user {user_id}")
                return None

        return credentials['access_token']
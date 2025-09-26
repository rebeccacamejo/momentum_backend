import os
import jwt
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .supabase_client import get_supabase, get_supabase_admin

security = HTTPBearer()

def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify a Supabase JWT token."""
    try:
        # Get the JWT secret from environment
        jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        if not jwt_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWT secret not configured"
            )

        # Decode and verify the JWT token
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )

        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get the current authenticated user from JWT token."""
    token = credentials.credentials
    payload = verify_jwt_token(token)

    # Extract user information from the JWT payload
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    return {
        "id": user_id,
        "email": payload.get("email"),
        "role": payload.get("role"),
        "aud": payload.get("aud"),
        "exp": payload.get("exp"),
        "iat": payload.get("iat"),
        "iss": payload.get("iss"),
        "sub": payload.get("sub"),
        "user_metadata": payload.get("user_metadata", {}),
        "app_metadata": payload.get("app_metadata", {})
    }

def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[Dict[str, Any]]:
    """Get the current user if authenticated, otherwise return None."""
    if not credentials:
        return None

    try:
        return get_current_user(credentials)
    except HTTPException:
        return None

async def get_user_organizations(user_id: str) -> list:
    """Get all organizations for a user."""
    supa = get_supabase()

    response = supa.table("organization_members")\
        .select("*, organizations(*)")\
        .eq("user_id", user_id)\
        .execute()

    if hasattr(response, 'data'):
        return response.data
    elif isinstance(response, dict) and 'data' in response:
        return response['data']
    else:
        return []

async def check_organization_access(user_id: str, org_id: str, required_role: Optional[str] = None) -> Dict[str, Any]:
    """Check if user has access to an organization and optionally a specific role."""
    supa = get_supabase()

    response = supa.table("organization_members")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("organization_id", org_id)\
        .single()\
        .execute()

    membership = None
    if hasattr(response, 'data'):
        membership = response.data
    elif isinstance(response, dict) and 'data' in response:
        membership = response['data']

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to organization"
        )

    # Check if user has required role
    if required_role:
        role_hierarchy = ["viewer", "member", "admin", "owner"]
        user_role_level = role_hierarchy.index(membership["role"])
        required_role_level = role_hierarchy.index(required_role)

        if user_role_level < required_role_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_role}"
            )

    return membership
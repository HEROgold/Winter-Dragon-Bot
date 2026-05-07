"""OAuth and user data API endpoints for WinterDragon frontend."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel


router = APIRouter(prefix="/api", tags=["oauth"])


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request payload."""

    code: str
    state: str


class OAuthCallbackResponse(BaseModel):
    """OAuth callback response payload."""

    accessToken: str
    discordId: str
    username: str


class UserDataResponse(BaseModel):
    """User data response payload."""

    id: str
    username: str
    joinedAt: str
    recordCount: int


class DeleteDataRequest(BaseModel):
    """Delete data request payload."""

    reason: str


class DeleteDataResponse(BaseModel):
    """Delete data response payload."""

    success: bool
    message: str


# In-memory session store (use Redis in production)
_sessions: dict[str, dict[str, Any]] = {}


def _verify_token(authorization: str | None) -> str:
    """Verify Bearer token and return Discord ID."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = authorization[7:]

    # Simple token validation (in production, verify against Discord API or JWT)
    if token not in _sessions:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return _sessions[token]["discordId"]


@router.post("/auth/discord/callback")
async def discord_callback(
    request: OAuthCallbackRequest,
) -> OAuthCallbackResponse:
    """Handle Discord OAuth callback.

    In production, exchange code for token via Discord API.
    """
    # TODO: Exchange code for Discord token
    # For now, mock the response
    discord_id = "123456789"
    username = "TestUser"
    access_token = f"token_{discord_id}_{int(datetime.now().timestamp())}"

    _sessions[access_token] = {
        "discordId": discord_id,
        "username": username,
        "expiresAt": datetime.now() + timedelta(hours=24),
    }

    return OAuthCallbackResponse(
        accessToken=access_token,
        discordId=discord_id,
        username=username,
    )


@router.get("/auth/discord/login")
async def discord_login() -> dict[str, str]:
    """Redirect to Discord OAuth authorization."""
    client_id = os.getenv("DISCORD_CLIENT_ID", "your-client-id")
    redirect_uri = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:3000")
    oauth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=identify%20email"
    )
    return {"url": oauth_url}


@router.get("/user/{discord_id}")
async def get_user(
    discord_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> UserDataResponse:
    """Fetch user profile and data summary."""
    user_id = _verify_token(authorization)

    if user_id != discord_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other user's data",
        )

    # TODO: Fetch from database
    return UserDataResponse(
        id=discord_id,
        username="TestUser",
        joinedAt="2025-01-15T10:30:00Z",
        recordCount=42,
    )


@router.delete("/user/{discord_id}/data")
async def delete_user_data(
    discord_id: str,
    request: DeleteDataRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> DeleteDataResponse:
    """Soft delete user data with audit trail."""
    user_id = _verify_token(authorization)

    if user_id != discord_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete other user's data",
        )

    # TODO: Soft delete from database and create audit entry
    return DeleteDataResponse(
        success=True,
        message="Your data has been marked for deletion",
    )


@router.get("/user/{discord_id}/audit")
async def get_user_audit(
    discord_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Fetch user data deletion audit trail."""
    user_id = _verify_token(authorization)

    if user_id != discord_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other user's audit logs",
        )

    # TODO: Fetch from database
    return {
        "deletions": [
            {
                "timestamp": "2025-01-20T14:22:00Z",
                "reason": "User requested deletion",
            }
        ]
    }

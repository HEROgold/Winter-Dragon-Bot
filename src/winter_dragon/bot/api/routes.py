"""OAuth and user data API endpoints for WinterDragon frontend."""

from __future__ import annotations

import secrets
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any, TypedDict
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Form, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlmodel import Session, select

from winter_dragon.database.constants import engine
from winter_dragon.database.tables.user import Users
from winter_dragon.database.tables.user_data_deletion import UserDataDeletion


router = APIRouter(prefix="/api", tags=["oauth"])
templates = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))
SESSION_COOKIE = "wd_session"
SESSION_DURATION = timedelta(hours=24)
OAUTH_STATE_DURATION = timedelta(minutes=10)


class SessionData(TypedDict):
    discord_id: str
    username: str
    discord_access_token: str
    signed_in_at: datetime
    expires_at: datetime


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


class DiscordUser(BaseModel):
    """Discord user payload."""

    id: str
    username: str


# In-memory stores for local/dev use only; use Redis or another shared store in production.
_sessions: dict[str, SessionData] = {}
_oauth_states: dict[str, datetime] = {}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _cleanup_expired_sessions() -> None:
    now = _utc_now()
    for token, session_data in list(_sessions.items()):
        if session_data["expires_at"] <= now:
            del _sessions[token]


def _cookie_secure_enabled() -> bool:
    configured = os.environ.get("COOKIE_SECURE")
    if configured is not None:
        return configured.lower() == "true"
    redirect_uri = os.environ.get("DISCORD_REDIRECT_URI", "http://localhost:8001/api/auth/discord/callback")
    return redirect_uri.startswith("https://")


def _cleanup_expired_oauth_states() -> None:
    now = _utc_now()
    for state, expires_at in list(_oauth_states.items()):
        if expires_at <= now:
            del _oauth_states[state]


def _get_oauth_settings() -> tuple[str, str, str]:
    client_id = os.environ.get("DISCORD_CLIENT_ID", "")
    client_secret = os.environ.get("DISCORD_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("DISCORD_REDIRECT_URI", "http://localhost:8001/api/auth/discord/callback")
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DISCORD_CLIENT_ID is not configured",
        )
    if not client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DISCORD_CLIENT_SECRET is not configured",
        )
    return client_id, client_secret, redirect_uri


def _build_discord_auth_url(state: str, client_id: str, redirect_uri: str) -> str:
    params = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "identify",
            "state": state,
            "prompt": "consent",
        },
    )
    return f"https://discord.com/api/oauth2/authorize?{params}"


def _exchange_code_for_token(code: str, state: str) -> str:
    _cleanup_expired_oauth_states()
    if state not in _oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        )
    _oauth_states.pop(state, None)
    client_id, client_secret, redirect_uri = _get_oauth_settings()
    try:
        response = requests.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
    except requests.Timeout as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Discord OAuth service timed out",
        ) from exc
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discord OAuth service unavailable",
        ) from exc
    if not response.ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Discord OAuth token exchange failed",
        )
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Discord OAuth token missing in response",
        )
    return token


def _get_discord_user(discord_access_token: str) -> DiscordUser:
    try:
        response = requests.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {discord_access_token}"},
            timeout=15,
        )
    except requests.Timeout as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Discord user profile request timed out",
        ) from exc
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discord user profile request failed",
        ) from exc
    if not response.ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to fetch Discord user profile",
        )
    payload = response.json()
    user_id = payload.get("id")
    username = payload.get("username")
    if not user_id or not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Discord user profile response",
        )
    return DiscordUser(id=user_id, username=username)


def _create_session(discord_user: DiscordUser, discord_access_token: str) -> str:
    _cleanup_expired_sessions()
    token = secrets.token_urlsafe(32)
    _sessions[token] = SessionData(
        discord_id=discord_user.id,
        username=discord_user.username,
        discord_access_token=discord_access_token,
        signed_in_at=_utc_now(),
        expires_at=_utc_now() + SESSION_DURATION,
    )
    return token


def _get_session_from_cookie(request: Request) -> SessionData:
    _cleanup_expired_sessions()
    token = request.cookies.get(SESSION_COOKIE)
    if not token or token not in _sessions:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please sign in with Discord first",
        )
    return _sessions[token]


def _verify_token(authorization: str | None) -> SessionData:
    """Verify Bearer token and return session data."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = authorization[7:]
    _cleanup_expired_sessions()
    if token not in _sessions:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return _sessions[token]


def _ensure_user_row(discord_id: str) -> None:
    with Session(engine) as session:
        if not session.exec(select(Users).where(Users.id == int(discord_id))).first():
            session.add(Users(id=int(discord_id)))
            session.commit()


def _get_deletions(discord_id: str) -> list[UserDataDeletion]:
    with Session(engine) as session:
        return session.exec(
            select(UserDataDeletion)
            .where(UserDataDeletion.user_id == int(discord_id))
            .order_by(UserDataDeletion.deleted_at.desc()),
        ).all()


def _record_deletion(discord_id: str, reason: str) -> None:
    with Session(engine) as session:
        session.add(UserDataDeletion(user_id=int(discord_id), reason=reason))
        session.commit()


def _build_user_data(discord_id: str, username: str, joined_at: datetime) -> UserDataResponse:
    _ensure_user_row(discord_id)
    deletions = _get_deletions(discord_id)
    return UserDataResponse(
        id=discord_id,
        username=username,
        joinedAt=joined_at.isoformat(),
        recordCount=len(deletions),
    )


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request) -> HTMLResponse:
    """Render the login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard_page(request: Request) -> HTMLResponse:
    """Render the HTMX dashboard."""
    session_data = _get_session_from_cookie(request)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "username": session_data["username"],
            "discord_id": session_data["discord_id"],
        },
    )


@router.post("/auth/logout", include_in_schema=False)
def logout(request: Request) -> RedirectResponse:
    """Clear auth session and return to login."""
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        _sessions.pop(token, None)
    response = RedirectResponse(url="/api/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/auth/discord/login")
def discord_login(mode: str | None = None) -> RedirectResponse | dict[str, str]:
    """Start Discord OAuth flow."""
    client_id, _, redirect_uri = _get_oauth_settings()
    state = secrets.token_urlsafe(24)
    _cleanup_expired_oauth_states()
    _oauth_states[state] = _utc_now() + OAUTH_STATE_DURATION
    oauth_url = _build_discord_auth_url(state=state, client_id=client_id, redirect_uri=redirect_uri)
    if mode == "url":
        return {"url": oauth_url}
    return RedirectResponse(url=oauth_url, status_code=status.HTTP_302_FOUND)


@router.get("/auth/discord/callback", include_in_schema=False)
def discord_callback_web(code: str, state: str) -> RedirectResponse:
    """Handle browser Discord OAuth callback."""
    discord_access_token = _exchange_code_for_token(code=code, state=state)
    discord_user = _get_discord_user(discord_access_token)
    token = _create_session(discord_user=discord_user, discord_access_token=discord_access_token)
    response = RedirectResponse(url="/api/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_DURATION.total_seconds()),
        httponly=True,
        secure=_cookie_secure_enabled(),
        samesite="lax",
    )
    return response


@router.post("/auth/discord/callback")
def discord_callback_api(request: OAuthCallbackRequest) -> OAuthCallbackResponse:
    """Handle API Discord OAuth callback."""
    discord_access_token = _exchange_code_for_token(code=request.code, state=request.state)
    discord_user = _get_discord_user(discord_access_token)
    token = _create_session(discord_user=discord_user, discord_access_token=discord_access_token)
    return OAuthCallbackResponse(
        accessToken=token,
        discordId=discord_user.id,
        username=discord_user.username,
    )


@router.get("/htmx/user-data", response_class=HTMLResponse, include_in_schema=False)
def htmx_user_data(request: Request) -> HTMLResponse:
    """Render authenticated user data panel."""
    session_data = _get_session_from_cookie(request)
    user_data = _build_user_data(
        discord_id=session_data["discord_id"],
        username=session_data["username"],
        joined_at=session_data["signed_in_at"],
    )
    return templates.TemplateResponse(
        "partials/user_data.html",
        {"request": request, "user_data": user_data},
    )


@router.get("/htmx/user-audit", response_class=HTMLResponse, include_in_schema=False)
def htmx_user_audit(request: Request) -> HTMLResponse:
    """Render audit history panel."""
    session_data = _get_session_from_cookie(request)
    deletions = _get_deletions(session_data["discord_id"])
    return templates.TemplateResponse(
        "partials/audit.html",
        {"request": request, "deletions": deletions},
    )


@router.post("/htmx/delete-data", response_class=HTMLResponse, include_in_schema=False)
def htmx_delete_data(
    request: Request,
    reason: Annotated[str, Form()] = "User requested deletion",
) -> HTMLResponse:
    """Record a user data deletion request."""
    session_data = _get_session_from_cookie(request)
    _record_deletion(session_data["discord_id"], reason.strip() or "User requested deletion")
    return templates.TemplateResponse(
        "partials/delete_result.html",
        {"request": request, "message": "Deletion request submitted and audited."},
    )


@router.get("/user/{discord_id}")
def get_user(
    discord_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> UserDataResponse:
    """Fetch user profile and data summary."""
    session_data = _verify_token(authorization)
    if session_data["discord_id"] != discord_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other user's data",
        )
    return _build_user_data(
        discord_id=discord_id,
        username=session_data["username"],
        joined_at=session_data["signed_in_at"],
    )


@router.delete("/user/{discord_id}/data")
def delete_user_data(
    discord_id: str,
    request: DeleteDataRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> DeleteDataResponse:
    """Soft delete user data with audit trail."""
    session_data = _verify_token(authorization)
    if session_data["discord_id"] != discord_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete other user's data",
        )
    _record_deletion(discord_id, request.reason.strip() or "User requested deletion")
    return DeleteDataResponse(
        success=True,
        message="Your data deletion request has been recorded",
    )


@router.get("/user/{discord_id}/audit")
def get_user_audit(
    discord_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Fetch user data deletion audit trail."""
    session_data = _verify_token(authorization)
    if session_data["discord_id"] != discord_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other user's audit logs",
        )
    deletions = _get_deletions(discord_id)
    return {
        "deletions": [
            {
                "timestamp": deletion.deleted_at.isoformat(),
                "reason": deletion.reason,
            }
            for deletion in deletions
        ]
    }

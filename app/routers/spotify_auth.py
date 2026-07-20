import secrets
from typing import Optional
from urllib.parse import urlencode, urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import Settings, get_settings
from app.dependencies import get_spotify_client
from app.spotify_client import SpotifyClient, SpotifyOAuthError


router = APIRouter(prefix="/spotify", tags=["spotify-auth"])
security = HTTPBasic(auto_error=False)
STATE_COOKIE = "spotify_oauth_state"
STATE_MAX_AGE_SECONDS = 600


def _secure_equals(left: str, right: str) -> bool:
    return secrets.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def require_oauth_admin(
    credentials: Optional[HTTPBasicCredentials] = Depends(security),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.spotify_oauth_admin_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Spotify reauthorization is disabled until SPOTIFY_OAUTH_ADMIN_PASSWORD is configured.",
        )

    valid = bool(
        credentials
        and _secure_equals(credentials.username, settings.spotify_oauth_admin_username)
        and _secure_equals(credentials.password, settings.spotify_oauth_admin_password)
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Spotify reauthorization credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )


@router.get("/login", dependencies=[Depends(require_oauth_admin)])
async def spotify_login(settings: Settings = Depends(get_settings)) -> RedirectResponse:
    state_token = secrets.token_urlsafe(32)
    query = urlencode(
        {
            "client_id": settings.client_id,
            "response_type": "code",
            "redirect_uri": settings.spotify_redirect_uri,
            "scope": settings.spotify_scopes,
            "state": state_token,
            "show_dialog": "true",
        }
    )
    response = RedirectResponse(url=f"{settings.authorize_url}?{query}", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        STATE_COOKIE,
        state_token,
        max_age=STATE_MAX_AGE_SECONDS,
        httponly=True,
        secure=urlparse(settings.spotify_redirect_uri).scheme == "https",
        samesite="lax",
        path="/spotify",
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/callback")
async def spotify_callback(
    request: Request,
    code: Optional[str] = Query(None),
    state_token: Optional[str] = Query(None, alias="state"),
    error: Optional[str] = Query(None),
    client: SpotifyClient = Depends(get_spotify_client),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    expected_state = request.cookies.get(STATE_COOKIE)
    if not expected_state or not state_token or not _secure_equals(expected_state, state_token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state.")
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Spotify authorization failed: {error}")
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Spotify did not return an authorization code.")

    try:
        await client.exchange_authorization_code(code)
    except SpotifyOAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    response = RedirectResponse(url=settings.spotify_post_auth_redirect, status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(STATE_COOKIE, path="/spotify")
    response.headers["Cache-Control"] = "no-store"
    return response

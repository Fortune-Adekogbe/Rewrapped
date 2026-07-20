from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import get_settings
from app.routers import card, spotify_auth, wrapped
from app.spotify_client import SpotifyReauthorizationRequired


settings = get_settings()
app = FastAPI(
    title="Rewrapped API",
    version="0.1.0",
    description="Generate Spotify Wrapped-style summaries using the Spotify Web API.",
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/card/rewrapped")


@app.exception_handler(SpotifyReauthorizationRequired)
async def spotify_reauthorization_required(
    _request: Request, exc: SpotifyReauthorizationRequired
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": str(exc), "reauthorization_url": settings.spotify_reauth_url},
    )


app.include_router(wrapped.router)
app.include_router(card.router)
app.include_router(spotify_auth.router)

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.routers import card, wrapped


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


app.include_router(wrapped.router)
app.include_router(card.router)

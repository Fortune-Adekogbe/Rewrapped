import asyncio
import logging
import os

from app.config import get_settings
from app.playback_store import PlaybackStore
from app.spotify_client import SpotifyClient, SpotifyReauthorizationRequired
from app.token_store import SpotifyTokenStore


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def ingest_once() -> None:
    settings = get_settings()
    if not settings.mongo_uri:
        raise ValueError("MONGODB_URI is required to ingest Spotify plays.")

    token_store = SpotifyTokenStore.from_settings(settings)
    client = SpotifyClient(settings, token_store)
    store = PlaybackStore.from_settings(settings)
    await store.ensure_indexes()

    try:
        recent = await client.get_recently_played(max_items=50)
        logger.info("Fetched %s recent plays from Spotify", len(recent))
        counts = await store.save_recently_played(recent)
        logger.info("Stored recent plays - inserted: %s, skipped (already present): %s", counts["inserted"], counts["skipped"])
    finally:
        await client.close()
        await token_store.close()
        await store.close()


if __name__ == "__main__":
    try:
        asyncio.run(ingest_once())
    except SpotifyReauthorizationRequired as exc:
        logger.error(str(exc))
        if os.getenv("GITHUB_ACTIONS") == "true":
            print(f"::error title=Spotify reauthorization required::{exc}")
        raise SystemExit(2) from exc

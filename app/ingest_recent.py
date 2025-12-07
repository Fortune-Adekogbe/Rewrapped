import asyncio
import logging

from app.config import get_settings
from app.playback_store import PlaybackStore
from app.spotify_client import SpotifyClient


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def ingest_once() -> None:
    settings = get_settings()
    if not settings.mongo_uri:
        raise ValueError("MONGODB_URI is required to ingest Spotify plays.")

    client = SpotifyClient(settings)
    store = PlaybackStore.from_settings(settings)
    await store.ensure_indexes()

    try:
        recent = await client.get_recently_played(max_items=50)
        logger.info("Fetched %s recent plays from Spotify", len(recent))
        counts = await store.save_recently_played(recent)
        logger.info("Stored recent plays - inserted: %s, skipped (already present): %s", counts["inserted"], counts["skipped"])
    finally:
        await client.close()
        await store.close()


if __name__ == "__main__":
    asyncio.run(ingest_once())

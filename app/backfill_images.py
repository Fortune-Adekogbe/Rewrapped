import asyncio
import logging
from typing import List

from tqdm import tqdm

from app.config import get_settings
from app.playback_store import PlaybackStore
from app.spotify_client import SpotifyClient


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def backfill_images(batch_limit: int = 500) -> None:
    settings = get_settings()
    if not settings.mongo_uri:
        raise ValueError("MONGODB_URI is required to backfill images.")

    store = PlaybackStore.from_settings(settings)
    client = SpotifyClient(settings)
    await store.ensure_indexes()

    try:
        missing_ids = await store.track_ids_missing_images(limit=batch_limit)
        if not missing_ids:
            logger.info("No tracks missing images.")
            return

        logger.info("Found %s track IDs missing images", len(missing_ids))
        details = await client.get_tracks_details(missing_ids)
        updated = 0
        for track_id, track in tqdm(details.items(), desc="Updating images", unit="track"):
            images: List[dict] = track.get("album", {}).get("images", [])
            if not images:
                continue
            await store.update_album_images(track_id, images)
            updated += 1
        logger.info("Updated %s tracks with album images", updated)
    finally:
        await client.close()
        await store.close()


if __name__ == "__main__":
    import sys

    limit_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    asyncio.run(backfill_images(batch_limit=limit_arg))

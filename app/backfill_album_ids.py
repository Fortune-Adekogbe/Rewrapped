import asyncio
import logging

from tqdm import tqdm

from app.config import get_settings
from app.playback_store import PlaybackStore
from app.spotify_client import SpotifyClient, SpotifyReauthorizationRequired
from app.token_store import SpotifyTokenStore


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def backfill_album_ids(batch_limit: int = 500, pause_seconds: float = 1.0) -> None:
    settings = get_settings()
    if not settings.mongo_uri:
        raise ValueError("MONGODB_URI is required to backfill album ids.")

    store = PlaybackStore.from_settings(settings)
    token_store = SpotifyTokenStore.from_settings(settings)
    client = SpotifyClient(settings, token_store)
    await store.ensure_indexes()

    total_updated = 0
    try:
        missing_ids = await store.track_ids_missing_album_id(limit=None)
        if not missing_ids:
            logger.info("No tracks missing album ids.")
        else:
            logger.info("Found %s track IDs missing album ids", len(missing_ids))
            for start in range(0, len(missing_ids), batch_limit):
                batch = missing_ids[start : start + batch_limit]
                details = await client.get_tracks_details(batch)
                if len(details) < len(batch):
                    logger.info("Spotify returned %s/%s track details", len(details), len(batch))

                updated_in_batch = 0
                skipped_in_batch = 0
                for track_id, track in tqdm(details.items(), desc="Updating album ids", unit="track"):
                    album = track.get("album") or {}
                    album_id = album.get("id")
                    if not album_id:
                        skipped_in_batch += 1
                        continue
                    album_name = album.get("name")
                    await store.update_album_id(track_id, album_id, album_name)
                    updated_in_batch += 1

                total_updated += updated_in_batch
                logger.info(
                    "Batch complete. Updated: %s, skipped: %s, total updated: %s",
                    updated_in_batch,
                    skipped_in_batch,
                    total_updated,
                )

                if pause_seconds and (start + batch_limit) < len(missing_ids):
                    logger.info("Sleeping %ss before next batch.", pause_seconds)
                    await asyncio.sleep(pause_seconds)

        remaining_ids = await store.track_ids_missing_album_id(limit=None)
        if remaining_ids:
            logger.warning("Remaining track IDs missing album ids: %s", len(remaining_ids))
        else:
            logger.info("Album id backfill complete; no missing album ids remaining.")
    finally:
        await client.close()
        await token_store.close()
        await store.close()


if __name__ == "__main__":
    import sys

    batch_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    pause_arg = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    try:
        asyncio.run(backfill_album_ids(batch_limit=batch_arg, pause_seconds=pause_arg))
    except SpotifyReauthorizationRequired as exc:
        logger.error(str(exc))
        raise SystemExit(2) from exc

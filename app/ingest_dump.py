import asyncio, json, glob
from datetime import datetime, timezone
from pathlib import Path

from tqdm import tqdm

from app.config import get_settings
from app.playback_store import PlaybackStore, _coerce_utc_datetime

def normalize(row):
    # drop podcasts/episodes
    if row.get("spotify_episode_uri") or str(row.get("spotify_track_uri", "")).startswith("spotify:episode"):
        return None
    if row.get("episode_name"):
        return None
    # “endsong” style
    if "ts" in row:
        uri = row.get("spotify_track_uri") or ""
        _id = uri.split(":")[-1] if uri else None
        played_dt = _coerce_utc_datetime(row["ts"])
        track_name = row.get("master_metadata_track_name")
        artist = row.get("master_metadata_album_artist_name")
        album = row.get("master_metadata_album_album_name")
        duration_ms = row.get("ms_played")
    else:
        return None

    return {
        "played_at": played_dt.isoformat(),
        "track": {
            "id": _id,
            "name": track_name,
            "duration_ms": duration_ms,
            "artists": [{"name": artist}] if artist else [],
            "album": {"name": album} if album else {},
        },
        "context": {"source": "history_dump"},
    }

async def ingest_dump(path_glob: str, batch_size: int = 500):
    settings = get_settings()
    store = PlaybackStore.from_settings(settings)
    await store.ensure_indexes()

    inserted = skipped = 0
    try:
        files = [Path(p) for p in glob.glob(path_glob)]
        for file_path in tqdm(files, desc="Files", unit="file"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            batch = []
            for row in tqdm(data, desc=file_path.name, unit="row"):
                item = normalize(row)
                if not item:
                    continue
                batch.append(item)
                if len(batch) >= batch_size:
                    counts = await store.save_recently_played(batch)
                    inserted += counts["inserted"]
                    skipped += counts["skipped"]
                    batch.clear()
            if batch:
                counts = await store.save_recently_played(batch)
                inserted += counts["inserted"]
                skipped += counts["skipped"]

        print(f"Done. Inserted: {inserted}, skipped (already present): {skipped}")
    finally:
        await store.close()

if __name__ == "__main__":
    import sys
    glob_arg = sys.argv[1] if len(sys.argv) > 1 else "Streaming_History_Audio*.json"
    asyncio.run(ingest_dump(glob_arg))

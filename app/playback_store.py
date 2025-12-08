from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from app.config import Settings


class PlaybackStore:
    """
    Thin wrapper around a MongoDB collection that stores recent Spotify plays.
    Documents are keyed by the precise played_at timestamp to prevent overlap.
    """

    def __init__(self, mongo_uri: str, db_name: str, collection_name: str) -> None:
        if not mongo_uri:
            raise ValueError("MONGODB_URI is required to use the playback store.")
        self._client = AsyncIOMotorClient(mongo_uri)
        self._collection: AsyncIOMotorCollection = self._client[db_name][collection_name]

    @classmethod
    def from_settings(cls, settings: Settings) -> "PlaybackStore":
        return cls(settings.mongo_uri, settings.mongo_db, settings.mongo_collection)

    async def close(self) -> None:
        self._client.close()

    async def ensure_indexes(self) -> None:
        # Guarantee uniqueness and allow efficient time-bounded queries.
        await self._collection.create_index("played_at", unique=True)
        await self._collection.create_index("track.id")
        await self._collection.create_index([("played_at", -1)])

    async def save_recently_played(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Upsert each play by played_at timestamp to avoid overlap/duplicates.
        """
        counts = {"inserted": 0, "skipped": 0}
        for item in items:
            doc = self._to_document(item)
            if not doc:
                continue
            result = await self._collection.update_one({"_id": doc["_id"]}, {"$setOnInsert": doc}, upsert=True)
            if result.upserted_id:
                counts["inserted"] += 1
            else:
                counts["skipped"] += 1
        return counts

    async def fetch_between(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        cursor = self._collection.find({"played_at": {"$gte": start, "$lt": end}}).sort("played_at", 1)
        return await cursor.to_list(length=None)

    async def track_ids_missing_images(self, limit: int = 500) -> List[str]:
        query = {
            "track.id": {"$ne": None, "$exists": True},
            "$or": [
                {"track.album.images": {"$exists": False}},
                {"track.album.images": {"$size": 0}},
                {"track.album.images": []},
            ],
        }
        ids = await self._collection.distinct("track.id", filter=query)
        return list(ids)[:limit]

    async def update_album_images(self, track_id: str, images: List[Dict[str, Any]]) -> None:
        await self._collection.update_many(
            {"track.id": track_id},
            {"$set": {"track.album.images": images}},
        )

    @staticmethod
    def _to_document(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        track = item.get("track") or {}
        played_at = item.get("played_at")
        if not track or not played_at:
            return None

        played_dt = _coerce_utc_datetime(played_at)
        album = track.get("album") or {}

        return {
            "_id": played_dt.isoformat(),
            "played_at": played_dt,
            "played_at_iso": played_dt.isoformat(),
            "track": {
                "id": track.get("id"),
                "name": track.get("name"),
                "duration_ms": track.get("duration_ms"),
                "artists": [artist.get("name") for artist in track.get("artists", []) if artist.get("name")],
                "album": {
                    "id": album.get("id"),
                    "name": album.get("name"),
                    "images": album.get("images", []),
                },
                "popularity": track.get("popularity"),
                "external_urls": track.get("external_urls"),
                "explicit": track.get("explicit"),
            },
            "context": item.get("context"),
        }


def _coerce_utc_datetime(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo:
        return dt.astimezone(timezone.utc)
    return dt.replace(tzinfo=timezone.utc)

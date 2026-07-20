from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from app.config import Settings


class SpotifyTokenStore:
    """Mongo-backed storage for the single Spotify user's refresh token."""

    TOKEN_DOCUMENT_ID = "primary"

    def __init__(self, mongo_uri: str, db_name: str, collection_name: str) -> None:
        if not mongo_uri:
            raise ValueError("MONGODB_URI is required to store Spotify authorization.")
        self._client = AsyncIOMotorClient(mongo_uri)
        self._collection: AsyncIOMotorCollection = self._client[db_name][collection_name]

    @classmethod
    def from_settings(cls, settings: Settings) -> "SpotifyTokenStore":
        return cls(settings.mongo_uri, settings.mongo_db, settings.spotify_token_collection)

    async def close(self) -> None:
        self._client.close()

    async def get_refresh_token(self) -> Optional[str]:
        document = await self._collection.find_one(
            {"_id": self.TOKEN_DOCUMENT_ID},
            {"refresh_token": 1},
        )
        if not document:
            return None
        token = document.get("refresh_token")
        return token if isinstance(token, str) and token else None

    async def save_refresh_token(self, refresh_token: str, scope: Optional[str] = None) -> None:
        if not refresh_token:
            raise ValueError("A non-empty Spotify refresh token is required.")

        now = datetime.now(timezone.utc)
        update = {
            "refresh_token": refresh_token,
            "updated_at": now,
        }
        if scope is not None:
            update["scope"] = scope

        await self._collection.update_one(
            {"_id": self.TOKEN_DOCUMENT_ID},
            {
                "$set": update,
                "$setOnInsert": {"created_at": now},
                "$unset": {"invalidated_at": "", "invalidated_reason": ""},
            },
            upsert=True,
        )

    async def delete_refresh_token(self, reason: str = "invalid_grant") -> None:
        await self._collection.update_one(
            {"_id": self.TOKEN_DOCUMENT_ID},
            {
                "$unset": {"refresh_token": ""},
                "$set": {
                    "invalidated_at": datetime.now(timezone.utc),
                    "invalidated_reason": reason,
                },
            },
        )

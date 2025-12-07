import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    client_id: str
    client_secret: str
    refresh_token: str
    api_base: str = "https://api.spotify.com/v1"
    auth_base: str = "https://accounts.spotify.com/api"
    request_timeout: int = 15
    mongo_uri: str = ""
    mongo_db: str = "rewrapped"
    mongo_collection: str = "plays"

    @classmethod
    def from_env(cls) -> "Settings":
        missing = [key for key in ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REFRESH_TOKEN") if not os.getenv(key)]
        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")

        return cls(
            client_id=os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
            refresh_token=os.environ["SPOTIFY_REFRESH_TOKEN"],
            api_base=os.getenv("SPOTIFY_API_BASE", cls.api_base),
            auth_base=os.getenv("SPOTIFY_AUTH_BASE", cls.auth_base),
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", cls.request_timeout)),
            mongo_uri=os.getenv("MONGODB_URI", ""),
            mongo_db=os.getenv("MONGODB_DB", cls.mongo_db),
            mongo_collection=os.getenv("MONGODB_COLLECTION", cls.mongo_collection),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()

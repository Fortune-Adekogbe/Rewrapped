import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    client_id: str
    client_secret: str
    api_base: str = "https://api.spotify.com/v1"
    auth_base: str = "https://accounts.spotify.com/api"
    authorize_url: str = "https://accounts.spotify.com/authorize"
    request_timeout: int = 15
    mongo_uri: str = ""
    mongo_db: str = "rewrapped"
    mongo_collection: str = "plays"
    spotify_token_collection: str = "spotify_tokens"
    spotify_redirect_uri: str = "http://localhost:8000/spotify/callback"
    spotify_scopes: str = "user-top-read user-read-recently-played user-read-private"
    spotify_oauth_admin_username: str = "admin"
    spotify_oauth_admin_password: str = ""
    spotify_post_auth_redirect: str = "/card/rewrapped"
    spotify_reauth_url: str = "/spotify/login"

    @classmethod
    def from_env(cls) -> "Settings":
        missing = [key for key in ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET") if not os.getenv(key)]
        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")

        return cls(
            client_id=os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
            api_base=os.getenv("SPOTIFY_API_BASE") or cls.api_base,
            auth_base=os.getenv("SPOTIFY_AUTH_BASE") or cls.auth_base,
            authorize_url=os.getenv("SPOTIFY_AUTHORIZE_URL") or cls.authorize_url,
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", cls.request_timeout)),
            mongo_uri=os.getenv("MONGODB_URI", ""),
            mongo_db=os.getenv("MONGODB_DB") or cls.mongo_db,
            mongo_collection=os.getenv("MONGODB_COLLECTION") or cls.mongo_collection,
            spotify_token_collection=os.getenv("SPOTIFY_TOKEN_COLLECTION") or cls.spotify_token_collection,
            spotify_redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI") or cls.spotify_redirect_uri,
            spotify_scopes=os.getenv("SPOTIFY_SCOPES") or cls.spotify_scopes,
            spotify_oauth_admin_username=os.getenv(
                "SPOTIFY_OAUTH_ADMIN_USERNAME", cls.spotify_oauth_admin_username
            )
            or cls.spotify_oauth_admin_username,
            spotify_oauth_admin_password=os.getenv("SPOTIFY_OAUTH_ADMIN_PASSWORD", ""),
            spotify_post_auth_redirect=os.getenv(
                "SPOTIFY_POST_AUTH_REDIRECT", cls.spotify_post_auth_redirect
            )
            or cls.spotify_post_auth_redirect,
            spotify_reauth_url=os.getenv("SPOTIFY_REAUTH_URL") or cls.spotify_reauth_url,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()

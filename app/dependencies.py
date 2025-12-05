from typing import AsyncGenerator

from app.config import get_settings
from app.spotify_client import SpotifyClient


async def get_spotify_client() -> AsyncGenerator[SpotifyClient, None]:
    client = SpotifyClient(get_settings())
    try:
        yield client
    finally:
        await client.close()

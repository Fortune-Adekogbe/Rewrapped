from typing import AsyncGenerator

from app.config import get_settings
from app.playback_store import PlaybackStore
from app.spotify_client import SpotifyClient


async def get_spotify_client() -> AsyncGenerator[SpotifyClient, None]:
    client = SpotifyClient(get_settings())
    try:
        yield client
    finally:
        await client.close()


async def get_playback_store() -> AsyncGenerator[PlaybackStore, None]:
    store = PlaybackStore.from_settings(get_settings())
    await store.ensure_indexes()
    try:
        yield store
    finally:
        await store.close()

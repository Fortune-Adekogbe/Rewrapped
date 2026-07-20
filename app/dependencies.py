from typing import AsyncGenerator

from app.config import get_settings
from app.playback_store import PlaybackStore
from app.spotify_client import SpotifyClient
from app.token_store import SpotifyTokenStore


async def get_spotify_client() -> AsyncGenerator[SpotifyClient, None]:
    settings = get_settings()
    token_store = SpotifyTokenStore.from_settings(settings)
    client = SpotifyClient(settings, token_store)
    try:
        yield client
    finally:
        await client.close()
        await token_store.close()


async def get_playback_store() -> AsyncGenerator[PlaybackStore, None]:
    store = PlaybackStore.from_settings(get_settings())
    await store.ensure_indexes()
    try:
        yield store
    finally:
        await store.close()

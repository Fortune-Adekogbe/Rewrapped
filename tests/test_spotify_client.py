import asyncio
from typing import Optional

import httpx
import pytest

from app.config import Settings
from app.spotify_client import SpotifyClient, SpotifyReauthorizationRequired


class MemoryTokenStore:
    def __init__(self, refresh_token: Optional[str]) -> None:
        self.refresh_token = refresh_token
        self.saved = []
        self.deleted_reason = None

    async def get_refresh_token(self) -> Optional[str]:
        return self.refresh_token

    async def save_refresh_token(self, refresh_token: str, scope: Optional[str] = None) -> None:
        self.refresh_token = refresh_token
        self.saved.append((refresh_token, scope))

    async def delete_refresh_token(self, reason: str = "invalid_grant") -> None:
        self.refresh_token = None
        self.deleted_reason = reason


def make_client(store: MemoryTokenStore, handler) -> SpotifyClient:
    settings = Settings(client_id="client", client_secret="secret")
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return SpotifyClient(settings, store, http_client=http_client)


def test_missing_refresh_token_requires_reauthorization() -> None:
    async def scenario() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("Spotify should not be called without a refresh token")

        client = make_client(MemoryTokenStore(None), handler)
        try:
            with pytest.raises(SpotifyReauthorizationRequired):
                await client.get_user_profile()
        finally:
            await client.close()

    asyncio.run(scenario())


def test_invalid_grant_discards_refresh_token() -> None:
    async def scenario() -> None:
        store = MemoryTokenStore("expired")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"error": "invalid_grant"})

        client = make_client(store, handler)
        try:
            with pytest.raises(SpotifyReauthorizationRequired):
                await client._refresh_access_token()
            assert store.refresh_token is None
            assert store.deleted_reason == "invalid_grant"
        finally:
            await client.close()

    asyncio.run(scenario())


def test_rotated_refresh_token_is_saved() -> None:
    async def scenario() -> None:
        store = MemoryTokenStore("old-token")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "access_token": "access-token",
                    "expires_in": 3600,
                    "refresh_token": "new-token",
                    "scope": "user-top-read",
                },
            )

        client = make_client(store, handler)
        try:
            await client._refresh_access_token()
            assert store.saved == [("new-token", "user-top-read")]
        finally:
            await client.close()

    asyncio.run(scenario())


def test_authorization_code_exchange_saves_refresh_token() -> None:
    async def scenario() -> None:
        store = MemoryTokenStore(None)

        def handler(request: httpx.Request) -> httpx.Response:
            assert b"grant_type=authorization_code" in request.content
            return httpx.Response(
                200,
                json={
                    "access_token": "access-token",
                    "expires_in": 3600,
                    "refresh_token": "authorized-token",
                    "scope": "user-top-read",
                },
            )

        client = make_client(store, handler)
        try:
            await client.exchange_authorization_code("authorization-code")
            assert store.saved == [("authorized-token", "user-top-read")]
        finally:
            await client.close()

    asyncio.run(scenario())

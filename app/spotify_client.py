import base64
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

import httpx

from app.config import Settings


class RefreshTokenStore(Protocol):
    async def get_refresh_token(self) -> Optional[str]: ...

    async def save_refresh_token(self, refresh_token: str, scope: Optional[str] = None) -> None: ...

    async def delete_refresh_token(self, reason: str = "invalid_grant") -> None: ...


class SpotifyReauthorizationRequired(RuntimeError):
    pass


class SpotifyOAuthError(RuntimeError):
    pass


class SpotifyClient:
    def __init__(
        self,
        settings: Settings,
        token_store: RefreshTokenStore,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.settings = settings
        self._token_store = token_store
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._http = http_client or httpx.AsyncClient(timeout=self.settings.request_timeout)

    async def close(self) -> None:
        await self._http.aclose()

    def _basic_auth_headers(self) -> Dict[str, str]:
        credentials = f"{self.settings.client_id}:{self.settings.client_secret}".encode()
        basic = base64.b64encode(credentials).decode()
        return {"Authorization": f"Basic {basic}"}

    def _reauthorization_error(self) -> SpotifyReauthorizationRequired:
        return SpotifyReauthorizationRequired(
            f"Spotify authorization is missing or expired. Reauthorize at {self.settings.spotify_reauth_url}"
        )

    async def _refresh_access_token(self) -> None:
        refresh_token = await self._token_store.get_refresh_token()
        if not refresh_token:
            raise self._reauthorization_error()

        data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
        response = await self._http.post(
            f"{self.settings.auth_base}/token",
            headers=self._basic_auth_headers(),
            data=data,
        )
        if response.status_code == 400 and self._oauth_error_code(response) == "invalid_grant":
            await self._token_store.delete_refresh_token(reason="invalid_grant")
            self._access_token = None
            self._token_expires_at = 0
            raise self._reauthorization_error()

        response.raise_for_status()
        payload = response.json()
        self._access_token = payload["access_token"]
        expires_in = payload.get("expires_in", 3600)
        self._token_expires_at = time.time() + expires_in - 60  # refresh slightly early

        rotated_refresh_token = payload.get("refresh_token")
        if rotated_refresh_token:
            await self._token_store.save_refresh_token(
                rotated_refresh_token,
                scope=payload.get("scope"),
            )

    async def exchange_authorization_code(self, code: str) -> None:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.settings.spotify_redirect_uri,
        }
        response = await self._http.post(
            f"{self.settings.auth_base}/token",
            headers=self._basic_auth_headers(),
            data=data,
        )
        if response.is_error:
            error_code = self._oauth_error_code(response) or f"HTTP {response.status_code}"
            raise SpotifyOAuthError(f"Spotify authorization code exchange failed: {error_code}")

        payload = response.json()
        refresh_token = payload.get("refresh_token")
        access_token = payload.get("access_token")
        if not refresh_token or not access_token:
            raise SpotifyOAuthError("Spotify did not return the required authorization tokens.")

        await self._token_store.save_refresh_token(refresh_token, scope=payload.get("scope"))
        self._access_token = access_token
        self._token_expires_at = time.time() + payload.get("expires_in", 3600) - 60

    @staticmethod
    def _oauth_error_code(response: httpx.Response) -> Optional[str]:
        try:
            payload = response.json()
        except ValueError:
            return None
        if not isinstance(payload, dict):
            return None
        error = payload.get("error")
        if isinstance(error, dict):
            error = error.get("status") or error.get("message")
        return str(error) if error else None

    async def _ensure_token(self) -> None:
        if not self._access_token or time.time() >= self._token_expires_at:
            await self._refresh_access_token()

    async def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        await self._ensure_token()
        headers = {"Authorization": f"Bearer {self._access_token}"}
        url = f"{self.settings.api_base}{path}"
        response = await self._http.request(method, url, headers=headers, params=params)
        if response.status_code == 401:
            await self._refresh_access_token()
            headers["Authorization"] = f"Bearer {self._access_token}"
            response = await self._http.request(method, url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    async def _paginate(
        self, path: str, params: Optional[Dict[str, Any]] = None, max_items: int = 150
    ) -> List[Dict[str, Any]]:
        params = params.copy() if params else {}
        results: List[Dict[str, Any]] = []
        offset = 0
        while len(results) < max_items:
            limit = min(50, max_items - len(results))
            page_params = {**params, "limit": limit, "offset": offset}
            data = await self._request("GET", path, params=page_params)
            items = data.get("items", [])
            results.extend(items)
            if len(items) < limit:
                break
            offset += limit
        return results

    async def get_user_profile(self) -> Dict[str, Any]:
        return await self._request("GET", "/me")

    async def get_top_tracks(self, time_range: str = "long_term", max_items: int = 50) -> List[Dict[str, Any]]:
        params = {"time_range": time_range}
        return await self._paginate("/me/top/tracks", params=params, max_items=max_items)

    async def get_top_artists(self, time_range: str = "long_term", max_items: int = 50) -> List[Dict[str, Any]]:
        params = {"time_range": time_range}
        return await self._paginate("/me/top/artists", params=params, max_items=max_items)

    async def get_recently_played(
        self,
        max_items: int = 200,
        after_ms: Optional[int] = None,
        before_ms: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": 50}
        if after_ms:
            params["after"] = after_ms
        if before_ms:
            params["before"] = before_ms

        collected: List[Dict[str, Any]] = []
        next_before = before_ms

        while len(collected) < max_items:
            if next_before:
                params["before"] = next_before
            data = await self._request("GET", "/me/player/recently-played", params=params)
            items = data.get("items", [])
            if not items:
                break
            collected.extend(items)
            if len(items) < params["limit"]:
                break
            last_played = items[-1]["played_at"]
            next_before = self._played_at_to_ms(last_played) - 1

        return collected[:max_items]

    async def get_audio_features(self, track_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        features: Dict[str, Dict[str, Any]] = {}
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i : i + 100]
            params = {"ids": ",".join(batch)}
            data = await self._request("GET", "/audio-features", params=params)
            for item in data.get("audio_features", []):
                if item and item.get("id"):
                    features[item["id"]] = item
        return features

    async def get_tracks_details(self, track_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch track details (including album images) for up to 50 IDs per request.
        """
        details: Dict[str, Dict[str, Any]] = {}
        for i in range(0, len(track_ids), 50):
            batch = track_ids[i : i + 50]
            params = {"ids": ",".join(batch)}
            data = await self._request("GET", "/tracks", params=params)
            for item in data.get("tracks", []):
                if item and item.get("id"):
                    details[item["id"]] = item
        return details

    @staticmethod
    def _played_at_to_ms(played_at: str) -> int:
        dt = datetime.fromisoformat(played_at.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)

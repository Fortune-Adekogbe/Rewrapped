import base64
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from app.config import Settings


class SpotifyClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._http = httpx.AsyncClient(timeout=self.settings.request_timeout)

    async def close(self) -> None:
        await self._http.aclose()

    async def _refresh_access_token(self) -> None:
        credentials = f"{self.settings.client_id}:{self.settings.client_secret}".encode()
        basic = base64.b64encode(credentials).decode()
        headers = {"Authorization": f"Basic {basic}"}
        data = {"grant_type": "refresh_token", "refresh_token": self.settings.refresh_token}
        response = await self._http.post(f"{self.settings.auth_base}/token", headers=headers, data=data)
        response.raise_for_status()
        payload = response.json()
        self._access_token = payload["access_token"]
        expires_in = payload.get("expires_in", 3600)
        self._token_expires_at = time.time() + expires_in - 60  # refresh slightly early

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

    @staticmethod
    def _played_at_to_ms(played_at: str) -> int:
        dt = datetime.fromisoformat(played_at.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)

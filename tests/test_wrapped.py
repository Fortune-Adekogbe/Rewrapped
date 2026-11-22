from datetime import datetime
from typing import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from app.dependencies import get_playback_store
from app.routers.wrapped import router


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    history = [
        ("2024-09-30T23:59:59+00:00", "outside"),
        ("2024-10-01T00:00:00+00:00", "repeat"),
        ("2024-11-15T12:00:00+00:00", "other"),
        ("2024-12-31T23:59:59+00:00", "repeat"),
        ("2025-01-01T00:00:00+00:00", "outside"),
    ]
    plays = [
        {
            "played_at": datetime.fromisoformat(timestamp),
            "track": {
                "id": track_id,
                "name": track_id,
                "duration_ms": 120_000,
                "artists": [track_id],
                "album": {"id": track_id, "name": track_id},
            },
        }
        for timestamp, track_id in history
    ]

    class MemoryPlaybackStore:
        async def fetch_between(self, start: datetime, end: datetime) -> list[dict]:
            return [play for play in plays if start <= play["played_at"] < end]

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_playback_store] = MemoryPlaybackStore
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def test_month_range_combines_plays_and_stops_at_the_year_boundary(client: httpx.AsyncClient) -> None:
    response = await client.get("/wrapped/month-range?year=2024&start_month=10&end_month=12&limit=1")

    assert response.status_code == 200
    summary = response.json()
    assert summary["year"] == 2024
    assert summary["start_month"] == 10
    assert summary["end_month"] == 12
    assert summary["start"] == "2024-10-01T00:00:00+00:00"
    assert summary["end"] == "2025-01-01T00:00:00+00:00"
    assert summary["play_count"] == 3
    assert summary["total_minutes"] == 6
    assert summary["days_active"] == 3
    assert summary["unique_tracks"] == summary["unique_artists"] == summary["unique_albums"] == 2
    for ranking in ("top_tracks", "top_artists", "top_albums"):
        assert [(row["id"], row["play_count"]) for row in summary[ranking]] == [("repeat", 2)]


async def test_month_range_matches_monthly_for_a_single_month(client: httpx.AsyncClient) -> None:
    response = await client.get("/wrapped/month-range?year=2024&start_month=11&end_month=11")
    monthly = await client.get("/wrapped/monthly?year=2024&month=11")

    assert response.status_code == monthly.status_code == 200
    summary = response.json()
    monthly_summary = monthly.json()
    assert summary.pop("start_month") == summary.pop("end_month") == monthly_summary.pop("month") == 11
    assert summary == monthly_summary


@pytest.mark.parametrize("start_month,end_month", [(12, 1), (0, 4), (10, 13)])
async def test_month_range_rejects_invalid_months(
    client: httpx.AsyncClient, start_month: int, end_month: int
) -> None:
    response = await client.get(
        "/wrapped/month-range", params={"year": 2024, "start_month": start_month, "end_month": end_month}
    )

    assert response.status_code == 422

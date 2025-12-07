from datetime import datetime, timedelta, timezone
from typing import Dict, List, Literal, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query

from app import analytics
from app.dependencies import get_playback_store, get_spotify_client
from app.playback_store import PlaybackStore
from app.spotify_client import SpotifyClient


router = APIRouter(prefix="/wrapped", tags=["wrapped"])

TimeRange = Literal["short_term", "medium_term", "long_term"]


@router.get("/short")
async def short_term(
    top_limit: int = Query(50, ge=1, le=50, description="Top tracks/artists (Spotify caps at 50)"),
    recent_limit: int = Query(
        50, ge=1, le=50, description="Recently played sample (Spotify exposes ~last 50 plays only)"
    ),
    client: SpotifyClient = Depends(get_spotify_client),
) -> Dict:
    """
    Short-term view (~4 weeks): top tracks, top artists, plus the small recent playback window Spotify exposes.
    """
    profile = await client.get_user_profile()
    top_tracks = await client.get_top_tracks(time_range="short_term", max_items=top_limit)
    top_artists = await client.get_top_artists(time_range="short_term", max_items=top_limit)
    recent_items = await client.get_recently_played(max_items=recent_limit)

    return {
        "time_range": "short_term",
        "user": {"id": profile.get("id"), "display_name": profile.get("display_name")},
        "top_tracks": analytics.summarize_top_tracks(top_tracks, audio_features={}),
        "top_artists": analytics.summarize_top_artists(top_artists),
        "recent": _summarize_recent(recent_items),
    }


@router.get("/medium")
async def medium_term(
    top_limit: int = Query(50, ge=1, le=50, description="Top tracks/artists (Spotify caps at 50)"),
    client: SpotifyClient = Depends(get_spotify_client),
) -> Dict:
    """
    Medium-term view (~6 months): top tracks and artists.
    """
    profile = await client.get_user_profile()
    top_tracks = await client.get_top_tracks(time_range="medium_term", max_items=top_limit)
    top_artists = await client.get_top_artists(time_range="medium_term", max_items=top_limit)

    return {
        "time_range": "medium_term",
        "user": {"id": profile.get("id"), "display_name": profile.get("display_name")},
        "top_tracks": analytics.summarize_top_tracks(top_tracks, audio_features={}),
        "top_artists": analytics.summarize_top_artists(top_artists),
    }


@router.get("/long")
async def long_term(
    top_limit: int = Query(50, ge=1, le=50, description="Top tracks/artists (Spotify caps at 50)"),
    client: SpotifyClient = Depends(get_spotify_client),
) -> Dict:
    """
    Long-term view (multi-year): top tracks and artists.
    """
    profile = await client.get_user_profile()
    top_tracks = await client.get_top_tracks(time_range="long_term", max_items=top_limit)
    top_artists = await client.get_top_artists(time_range="long_term", max_items=top_limit)

    return {
        "time_range": "long_term",
        "user": {"id": profile.get("id"), "display_name": profile.get("display_name")},
        "top_tracks": analytics.summarize_top_tracks(top_tracks, audio_features={}),
        "top_artists": analytics.summarize_top_artists(top_artists),
    }


def _summarize_recent(items: List[Dict]) -> Dict[str, List[Dict]]:
    simplified = []
    for item in items:
        track = item.get("track") or {}
        simplified.append(
            {
                "played_at": item.get("played_at"),
                "id": track.get("id"),
                "name": track.get("name"),
                "artists": [artist["name"] for artist in track.get("artists", [])],
                "duration_ms": track.get("duration_ms"),
            }
        )
    return {"count": len(simplified), "items": simplified}


@router.get("/monthly")
async def monthly_wrapped(
    month: Optional[int] = Query(None, ge=1, le=12, description="Month number (1-12). Defaults to previous month."),
    year: Optional[int] = Query(None, ge=2000, le=2100, description="4-digit year. Defaults alongside month."),
    limit: int = Query(20, ge=1, le=50, description="How many top tracks/artists/albums to include."),
    store: PlaybackStore = Depends(get_playback_store),
) -> Dict:
    """
    Wrapped-style view backed by stored plays in MongoDB for a specific month/year.
    Defaults to the previous calendar month if no params are supplied.
    """
    target_year, target_month = _resolve_month_year(year, month)
    start = datetime(target_year, target_month, 1, tzinfo=timezone.utc)
    end_month = 1 if target_month == 12 else target_month + 1
    end_year = target_year + 1 if target_month == 12 else target_year
    end = datetime(end_year, end_month, 1, tzinfo=timezone.utc)

    try:
        plays = await store.fetch_between(start, end)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    summary = analytics.summarize_month_from_plays(plays, limit=limit)
    return {
        "year": target_year,
        "month": target_month,
        "start": start.isoformat(),
        "end": end.isoformat(),
        **summary,
    }


@router.get("/yearly")
async def yearly_wrapped(
    year: Optional[int] = Query(None, ge=2000, le=2100, description="4-digit year. Defaults to previous year."),
    limit: int = Query(20, ge=1, le=50, description="How many top tracks/artists/albums to include."),
    store: PlaybackStore = Depends(get_playback_store),
) -> Dict:
    """
    Wrapped-style view backed by stored plays in MongoDB for a specific calendar year.
    Defaults to the previous calendar year if omitted.
    """
    target_year = _resolve_year(year)
    start = datetime(target_year, 1, 1, tzinfo=timezone.utc)
    end = datetime(target_year + 1, 1, 1, tzinfo=timezone.utc)

    try:
        plays = await store.fetch_between(start, end)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    summary = analytics.summarize_month_from_plays(plays, limit=limit)
    return {
        "year": target_year,
        "start": start.isoformat(),
        "end": end.isoformat(),
        **summary,
    }


def _resolve_month_year(year: Optional[int], month: Optional[int]) -> Tuple[int, int]:
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_month_anchor = start_of_month - timedelta(days=1)

    if year and month:
        return year, month
    if year and not month:
        return year, previous_month_anchor.month
    if month and not year:
        return now.year, month

    resolved_year = previous_month_anchor.year
    resolved_month = previous_month_anchor.month
    return resolved_year, resolved_month


def _resolve_year(year: Optional[int]) -> int:
    now = datetime.now(timezone.utc)
    if year:
        return year
    return now.year - 1

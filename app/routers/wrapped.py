from typing import Dict, List, Literal

from fastapi import APIRouter, Depends, Query

from app import analytics
from app.dependencies import get_spotify_client
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

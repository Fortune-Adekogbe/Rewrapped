from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional


def summarize_top_tracks(tracks: List[Dict[str, Any]], audio_features: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    summary = []
    for idx, track in enumerate(tracks):
        features = audio_features.get(track["id"], {})
        summary.append(
            {
                "rank": idx + 1,
                "id": track["id"],
                "name": track["name"],
                "artists": [artist["name"] for artist in track.get("artists", [])],
                "album": track.get("album", {}).get("name"),
                "image_url": _pick_image_url(track.get("album", {}).get("images", [])),
                "popularity": track.get("popularity"),
                "duration_ms": track.get("duration_ms"),
                "preview_url": track.get("preview_url"),
                "features": _pick_features(features),
            }
        )
    return summary


def summarize_top_artists(artists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    summary = []
    for idx, artist in enumerate(artists):
        summary.append(
            {
                "rank": idx + 1,
                "id": artist["id"],
                "name": artist["name"],
                "genres": artist.get("genres", []),
                "followers": artist.get("followers", {}).get("total"),
                "popularity": artist.get("popularity"),
            }
        )
    return summary


def top_genres(artists: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    counts = Counter()
    for artist in artists:
        counts.update(artist.get("genres", []))
    return [{"genre": genre, "count": count} for genre, count in counts.most_common(limit)]


def listening_profile_from_recent(recent_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not recent_items:
        return {"total_minutes": 0, "hourly_distribution": {}, "unique_days": 0}

    minutes = 0
    hourly = Counter()
    days = set()
    for item in recent_items:
        track = item.get("track", {})
        minutes += (track.get("duration_ms", 0) or 0) / 60000
        played_at = item.get("played_at")
        if played_at:
            dt = datetime.fromisoformat(played_at.replace("Z", "+00:00"))
            hourly[dt.hour] += 1
            days.add(dt.date())
    return {
        "total_minutes": round(minutes, 2),
        "hourly_distribution": dict(hourly),
        "unique_days": len(days),
    }


def average_features(tracks: List[Dict[str, Any]], audio_features: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    if not tracks:
        return {}
    totals = Counter()
    count = 0
    for track in tracks:
        features = audio_features.get(track["id"])
        if not features:
            continue
        count += 1
        for key in ("energy", "danceability", "valence", "acousticness", "speechiness", "tempo"):
            if key in features:
                totals[key] += features[key]
    if not count:
        return {}
    return {key: round(value / count, 3) for key, value in totals.items()}


def audio_feature_highlights(tracks: List[Dict[str, Any]], audio_features: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    highlight_keys = {
        "most_energetic": ("energy", max),
        "most_danceable": ("danceability", max),
        "most_chill": ("valence", min),
        "fastest": ("tempo", max),
    }
    highlights: Dict[str, Any] = {}
    for label, (feature_key, reducer) in highlight_keys.items():
        candidate = _pick_track_by_feature(tracks, audio_features, feature_key, reducer)
        if candidate:
            highlights[label] = candidate
    return highlights


def monthly_breakdown(recent_items: List[Dict[str, Any]], audio_features: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"tracks": [], "artists": Counter(), "minutes": 0.0})
    for item in recent_items:
        track = item.get("track")
        played_at = item.get("played_at")
        if not track or not played_at:
            continue
        dt = datetime.fromisoformat(played_at.replace("Z", "+00:00"))
        key = dt.strftime("%Y-%m")
        buckets[key]["tracks"].append(track)
        buckets[key]["minutes"] += (track.get("duration_ms", 0) or 0) / 60000
        buckets[key]["artists"].update([artist["name"] for artist in track.get("artists", [])])

    summaries: List[Dict[str, Any]] = []
    for month_key, bucket in sorted(buckets.items(), reverse=True):
        artist_counter: Counter = bucket["artists"]
        features = average_features(bucket["tracks"], audio_features)
        summaries.append(
            {
                "month": month_key,
                "total_minutes": round(bucket["minutes"], 2),
                "track_count": len(bucket["tracks"]),
                "top_artists": [{"name": name, "count": count} for name, count in artist_counter.most_common(5)],
                "top_tracks": _top_tracks_in_bucket(bucket["tracks"], audio_features, limit=5),
                "average_features": features,
            }
        )
    return summaries


def build_wrapped_payload(
    profile: Dict[str, Any],
    top_tracks: List[Dict[str, Any]],
    top_artists: List[Dict[str, Any]],
    recent_items: List[Dict[str, Any]],
    audio_features: Dict[str, Dict[str, Any]],
    time_range: str,
) -> Dict[str, Any]:
    top_tracks_summary = summarize_top_tracks(top_tracks, audio_features)
    top_artists_summary = summarize_top_artists(top_artists)
    genres = top_genres(top_artists)
    profile_summary = listening_profile_from_recent(recent_items)
    feature_avg = average_features(top_tracks, audio_features)
    highlights = audio_feature_highlights(top_tracks, audio_features)
    monthly = monthly_breakdown(recent_items, audio_features)

    return {
        "user": {
            "id": profile.get("id"),
            "display_name": profile.get("display_name"),
            "country": profile.get("country"),
            "followers": profile.get("followers", {}).get("total"),
        },
        "time_range": time_range,
        "overall": {
            "total_minutes": profile_summary.get("total_minutes"),
            "unique_tracks": len({track["id"] for track in top_tracks}),
            "unique_artists": len({artist["id"] for artist in top_artists}),
            "genres": genres,
            "hourly_distribution": profile_summary.get("hourly_distribution"),
            "average_audio_features": feature_avg,
        },
        "top_tracks": top_tracks_summary,
        "top_artists": top_artists_summary,
        "audio_feature_highlights": highlights,
        "monthly": monthly,
    }


def summarize_month_from_plays(plays: List[Dict[str, Any]], limit: int = 20) -> Dict[str, Any]:
    """
    Collapse a month of stored plays into top tracks/artists/albums plus totals.
    """
    if not plays:
        return {
            "play_count": 0,
            "unique_tracks": 0,
            "unique_artists": 0,
            "unique_albums": 0,
            "total_minutes": 0,
            "days_active": 0,
            "top_tracks": [],
            "top_artists": [],
            "top_albums": [],
        }

    track_counter: Counter = Counter()
    track_durations: Counter = Counter()
    track_meta: Dict[str, Dict[str, Any]] = {}

    album_counter: Counter = Counter()
    album_durations: Counter = Counter()
    album_meta: Dict[str, Dict[str, Any]] = {}

    artist_counter: Counter = Counter()
    artist_durations: Counter = Counter()

    days = set()

    for play in plays:
        played_at = play.get("played_at")
        if isinstance(played_at, datetime):
            days.add(played_at.date())

        track = play.get("track") or {}
        track_id = track.get("id") or track.get("name")
        if not track_id:
            continue

        duration_ms = track.get("duration_ms") or 0
        track_counter[track_id] += 1
        track_durations[track_id] += duration_ms

        album = track.get("album") or {}
        album_id = album.get("id") or album.get("name") or track_id
        album_counter[album_id] += 1
        album_durations[album_id] += duration_ms

        track_meta[track_id] = {
            "name": track.get("name"),
            "artists": track.get("artists", []),
            "album": album.get("name"),
            "image_url": _pick_image_url(album.get("images", [])),
        }
        album_meta[album_id] = {
            "name": album.get("name"),
            "artists": track.get("artists", []),
            "image_url": _pick_image_url(album.get("images", [])),
        }

        for artist in track.get("artists", []):
            artist_counter[artist] += 1
            artist_durations[artist] += duration_ms

    total_minutes = round(sum(track_durations.values()) / 60000, 2)

    def _list_from(counter: Counter, durations: Counter, meta: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for key, count in counter.most_common(limit):
            info = meta.get(key, {})
            rows.append(
                {
                    "id": key,
                    "name": info.get("name"),
                    "artists": info.get("artists", []),
                    "album": info.get("album"),
                    "image_url": info.get("image_url"),
                    "play_count": count,
                    "minutes": round((durations.get(key, 0) or 0) / 60000, 2),
                }
            )
        return rows

    artist_meta = {name: {"name": name} for name in artist_counter.keys()}

    return {
        "play_count": sum(track_counter.values()),
        "unique_tracks": len(track_counter),
        "unique_artists": len(artist_counter),
        "unique_albums": len(album_counter),
        "total_minutes": total_minutes,
        "days_active": len(days),
        "top_tracks": _list_from(track_counter, track_durations, track_meta),
        "top_artists": _list_from(artist_counter, artist_durations, artist_meta),
        "top_albums": _list_from(album_counter, album_durations, album_meta),
    }


def _pick_track_by_feature(
    tracks: List[Dict[str, Any]], audio_features: Dict[str, Dict[str, Any]], feature_key: str, reducer
) -> Optional[Dict[str, Any]]:
    candidate = None
    for track in tracks:
        features = audio_features.get(track["id"])
        if not features or feature_key not in features:
            continue
        if not candidate:
            candidate = track
            continue
        if reducer(features[feature_key], audio_features[candidate["id"]][feature_key]) == features[feature_key]:
            candidate = track
    if not candidate:
        return None
    return {
        "id": candidate["id"],
        "name": candidate["name"],
        "artists": [artist["name"] for artist in candidate.get("artists", [])],
        "feature_value": audio_features[candidate["id"]][feature_key],
    }


def _top_tracks_in_bucket(tracks: List[Dict[str, Any]], audio_features: Dict[str, Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    seen = set()
    ordered = []
    for track in tracks:
        if track["id"] in seen:
            continue
        seen.add(track["id"])
        ordered.append(
            {
                "id": track["id"],
                "name": track["name"],
                "artists": [artist["name"] for artist in track.get("artists", [])],
                "image_url": _pick_image_url(track.get("album", {}).get("images", [])),
                "features": _pick_features(audio_features.get(track["id"], {})),
            }
        )
        if len(ordered) >= limit:
            break
    return ordered


def _pick_features(features: Dict[str, Any]) -> Dict[str, Any]:
    if not features:
        return {}
    keep = ("danceability", "energy", "valence", "acousticness", "speechiness", "tempo")
    return {key: features[key] for key in keep if key in features}


def _pick_image_url(images: List[Dict[str, Any]]) -> Optional[str]:
    if not images:
        return None
    if len(images) == 1:
        return images[0].get("url")
    if len(images) >= 2:
        return images[1].get("url") or images[0].get("url")
    return images[0].get("url")

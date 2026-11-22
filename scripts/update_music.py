#!/usr/bin/env python3
"""Update the Last.fm music section of README.md.

Fetches the total scrobble count (user.getinfo) and the most recent
tracks (user.getrecenttracks) from the Last.fm API and fills the
<!--START_SECTION:music--> block with a JSON document.

Requires the LASTFM_API_KEY secret and the LASTFM_USERNAME secret;
without either of them the section is left untouched.
"""

import http.client
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from readme_utils import update_section

API = "https://ws.audioscrobbler.com/2.0/"
RECENT_LIMIT = 5
TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def fetch(api_key, user, method, **extra):
    """Call a Last.fm user method and return the parsed JSON payload."""
    params = urlencode(
        {
            "method": method,
            "user": user,
            "api_key": api_key,
            "format": "json",
            **extra,
        }
    )
    request = Request(f"{API}?{params}", headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)


def fetch_total_plays(api_key, user):
    """Return the user's total scrobble count, or None if unavailable."""
    payload = fetch(api_key, user, "user.getinfo")
    total = (payload.get("user") or {}).get("playcountAtLastScrobble")
    return int(total) if total is not None else None


def fetch_recent_tracks(api_key, user):
    """Return the recently played tracks (currently playing track excluded)."""
    payload = fetch(api_key, user, "user.getrecenttracks", limit=RECENT_LIMIT)
    tracks = (payload.get("recenttracks") or {}).get("track") or []
    return [
        {
            "track": track.get("name"),
            "artist": (track.get("artist") or {}).get("#text"),
            "album": (track.get("album") or {}).get("#text"),
            "played_at": (track.get("date") or {}).get("#text"),
        }
        for track in tracks
        if track.get("@attr", {}).get("nowplaying") != "true"
    ]


def render(total_plays, tracks):
    return {"total_plays": total_plays, "recent_tracks": tracks}


def main():
    api_key = os.environ.get("LASTFM_API_KEY", "").strip()
    user = os.environ.get("LASTFM_USERNAME", "").strip()
    if not api_key or not user:
        print("LASTFM_API_KEY / LASTFM_USERNAME not set, skipping music update")
        return

    errors = []
    total_plays = None
    tracks = []

    try:
        total_plays = fetch_total_plays(api_key, user)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError, http.client.HTTPException) as error:
        print(f"Last.fm user.getinfo failed: {error}")
        errors.append("total_plays")

    try:
        tracks = fetch_recent_tracks(api_key, user)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError, http.client.HTTPException) as error:
        print(f"Last.fm user.getrecenttracks failed: {error}")
        errors.append("recent_tracks")

    if errors:
        # Degrade: write whatever was fetched, keep the rest empty. If nothing
        # was fetched at all, leave the section untouched.
        print(f"Partial Last.fm data, updating without: {', '.join(errors)}")

    update_section("music", json.dumps(render(total_plays, tracks), indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()
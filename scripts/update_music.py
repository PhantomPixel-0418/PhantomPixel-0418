#!/usr/bin/env python3
"""Update the Last.fm music section of README.md.

Fetches the currently playing track and recent tracks from the Last.fm
API and fills the <!--START_SECTION:music--> block with a JSON document.

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


def fetch_recent_tracks(api_key, user):
    """Return the parsed user.getrecenttracks response."""
    params = urlencode(
        {
            "method": "user.getrecenttracks",
            "user": user,
            "api_key": api_key,
            "format": "json",
            "limit": RECENT_LIMIT,
        }
    )
    request = Request(f"{API}?{params}", headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)


def render(recent):
    """Build the music JSON from the Last.fm response."""
    tracks = []
    now_playing = None
    for track in recent.get("recenttracks", {}).get("track", []):
        item = {
            "track": track.get("name"),
            "artist": (track.get("artist") or {}).get("#text"),
            "album": (track.get("album") or {}).get("#text"),
            "url": track.get("url"),
        }
        if track.get("@attr", {}).get("nowplaying") == "true":
            now_playing = item
        else:
            item["played_at"] = (track.get("date") or {}).get("#text")
            tracks.append(item)
    return {"now_playing": now_playing, "recent_tracks": tracks}


def main():
    api_key = os.environ.get("LASTFM_API_KEY", "").strip()
    user = os.environ.get("LASTFM_USERNAME", "").strip()
    if not api_key or not user:
        print("LASTFM_API_KEY / LASTFM_USERNAME not set, skipping music update")
        return

    try:
        recent = fetch_recent_tracks(api_key, user)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError, http.client.HTTPException) as error:
        print(f"Last.fm API request failed: {error}")
        return

    if not isinstance(recent, dict) or "recenttracks" not in recent:
        print("Last.fm API returned an invalid payload, leaving music section untouched")
        return

    update_section("music", json.dumps(render(recent), indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()
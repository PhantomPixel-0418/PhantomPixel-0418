#!/usr/bin/env python3
"""Update the WakaTime coding section of README.md.

Fetches stats from WakaTime's public per-user endpoint (no API key
required) and fills the <!--START_SECTION:waka--> block. Requires the
WAKATIME_USER_ID secret; without it the section is left untouched.

The endpoint without a range serves the user's public profile stats
range (set on wakatime.com); requesting a different range answers 400
("Time range not matching user's public stats range").
"""

import http.client
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from readme_utils import update_section

API = "https://wakatime.com/api/v1/users/{user_id}/stats"
TIMEOUT = 30
LANG_COUNT = 5
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def fetch_stats(user_id):
    """Fetch the user's public-profile stats (no range = profile default)."""
    url = API.format(user_id=user_id)
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=TIMEOUT) as response:
        payload = json.load(response)
    data = payload.get("data")
    if not data:
        raise SystemExit(f"WakaTime API returned no data: {payload}")
    return data


def render_range(stats):
    """Render the stats payload as a JSON-friendly dict."""
    languages = []
    for language in (stats.get("languages") or [])[:LANG_COUNT]:
        try:
            percent = round(float(language.get("percent", 0)), 2)
        except (TypeError, ValueError):
            percent = None
        languages.append(
            {
                "name": language.get("name"),
                "text": language.get("text", ""),
                "percent": percent,
            }
        )
    return {
        "range": stats.get("range") or "unknown",
        "total_time": stats.get("human_readable_total") or "No activity tracked",
        "languages": languages,
    }


def main():
    user_id = os.environ.get("WAKATIME_USER_ID", "").strip()
    if not user_id:
        print("WAKATIME_USER_ID not set, skipping WakaTime update")
        return

    try:
        data = fetch_stats(user_id)
        stats = {data.get("range") or "unknown": render_range(data)}
        print(f"Fetched {data.get('range')}")
    except (HTTPError, OSError, http.client.HTTPException, SystemExit, ValueError) as error:
        print(f"Could not fetch WakaTime stats: {error}")
        stats = {"unknown": {"range": "unknown", "total_time": "Unavailable", "languages": []}}

    update_section("waka", json.dumps(stats, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()
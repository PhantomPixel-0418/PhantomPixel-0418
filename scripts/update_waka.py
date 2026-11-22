#!/usr/bin/env python3
"""Update the WakaTime coding section of README.md.

Fetches the last-7-days and all-time stats from WakaTime's public
per-user stats endpoint (no API key required) and fills the
<!--START_SECTION:waka--> block. Requires the WAKATIME_USER_ID
secret; without it the section is left untouched.
"""

import http.client
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from readme_utils import update_section

API = "https://wakatime.com/api/v1/users/{user_id}/stats/{range}"
TIMEOUT = 30
LANG_COUNT = 5
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def fetch_stats(user_id, time_range):
    """Fetch one stats payload from the public per-user endpoint."""
    url = API.format(user_id=user_id, range=time_range)
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=TIMEOUT) as response:
        payload = json.load(response)
    data = payload.get("data")
    if not data:
        raise SystemExit(f"WakaTime API returned no data for {time_range}: {payload}")
    return data


def render_range(stats):
    """Render one time range as a JSON-friendly dict."""
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
        "total_time": stats.get("human_readable_total") or "No activity tracked",
        "languages": languages,
    }


def main():
    user_id = os.environ.get("WAKATIME_USER_ID", "").strip()
    if not user_id:
        print("WAKATIME_USER_ID not set, skipping WakaTime update")
        return

    stats = {}
    for key in ("last_7_days", "all_time"):
        try:
            stats[key] = render_range(fetch_stats(user_id, key))
            print(f"Fetched {key}")
        except (HTTPError, OSError, http.client.HTTPException, SystemExit, ValueError) as error:
            print(f"Could not fetch {key}: {error}")
            stats[key] = {"total_time": "Unavailable", "languages": []}

    update_section("waka", json.dumps(stats, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()
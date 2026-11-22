#!/usr/bin/env python3
"""Update the WakaTime coding section of README.md.

Fetches the last-7-days and all-time stats from the WakaTime API, renders
them as a JSON document awaited by the <!--START_SECTION:waka--> block,
and leaves committing to the caller. Requires the WAKATIME_API_KEY
secret; without it the section is left untouched.
"""

import http.client
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from readme_utils import update_section

API = "https://wakatime.com/api/v1/users/current/stats/"
TIMEOUT = 30
LANG_COUNT = 5
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def fetch_stats(token, time_range):
    """Fetch one stats payload, trying Bearer auth then the api_key parameter."""
    attempts = (
        (API + time_range, {"Authorization": f"Bearer {token}"}),
        (API + time_range + "?api_key=" + quote(token), {}),
    )
    last_error = None
    for url, extra_headers in attempts:
        request = Request(url, headers={"User-Agent": USER_AGENT, **extra_headers})
        try:
            with urlopen(request, timeout=TIMEOUT) as response:
                payload = json.load(response)
        except (HTTPError, URLError, TimeoutError, ValueError, OSError, http.client.HTTPException) as error:
            last_error = error
            continue
        if payload.get("data"):
            return payload["data"]
        last_error = payload.get("error") or payload.get("errors") or payload
    raise SystemExit(f"WakaTime API request failed for {time_range}: {last_error}")


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
    token = os.environ.get("WAKATIME_API_KEY", "").strip()
    if not token:
        print("WAKATIME_API_KEY not set, skipping WakaTime update")
        return

    stats = {}
    for key, time_range in (("last_7_days", "last_7_days"), ("all_time", "all_time")):
        try:
            stats[key] = render_range(fetch_stats(token, time_range))
            print(f"Fetched {time_range}")
        except (SystemExit, Exception) as error:
            print(f"Could not fetch {time_range}: {error}")
            stats[key] = {"total_time": "Unavailable", "languages": []}

    update_section("waka", json.dumps(stats, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()
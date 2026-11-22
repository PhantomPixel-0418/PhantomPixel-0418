#!/usr/bin/env python3
"""Update the refresh-date line in README.md with the current UTC time.

Runs on every scheduled / dispatched workflow invocation, so the README
always shows when its stats were last refreshed. Rendered as a small,
right-aligned HTML line (no code fence).
"""

from datetime import datetime, timezone

from readme_utils import update_section


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    update_section(
        "refresh",
        '<p align="right"><small>Last refreshed: {stamp}</small></p>'.format(stamp=now),
        fence=None,
    )


if __name__ == "__main__":
    main()

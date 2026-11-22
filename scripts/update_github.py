#!/usr/bin/env python3
"""Update the GitHub stats section of README.md.

Collects profile statistics from the GitHub API — overview counts via
REST, contribution calendar and language byte counts via GraphQL — and
fills the <!--START_SECTION:github--> block with a JSON document.

The workflow provides GITHUB_TOKEN automatically; a personal access
token may be supplied through GH_TOKEN for extra visibility. Every data
point is fetched independently and degrades to null on failure, so a
transient API error never breaks the run.
"""

import json
import http.client
import os
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from readme_utils import update_section

USERNAME = "PhantomPixel-0418"
REST = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"
TIMEOUT = 30
LANG_COUNT = 5
PAGE_SIZE = 100
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def request_json(url, token, method="GET", payload=None, accept=None):
    """Perform an authenticated API request and return the parsed JSON."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": accept or "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)


def paginate(url, token, key=None, max_pages=None):
    """Fetch every page of a REST listing, up to PAGE_SIZE per request.

    max_pages caps how many pages are requested (search results stop at 1000).
    """
    items = []
    page = 1
    while True:
        separator = "&" if "?" in url else "?"
        batch = request_json(f"{url}{separator}per_page={PAGE_SIZE}&page={page}", token)
        chunk = batch if isinstance(batch, list) else batch.get(key, [])
        items.extend(chunk)
        if len(chunk) < PAGE_SIZE:
            return items
        page += 1
        if max_pages is not None and page > max_pages:
            return items


def graphql_user(token):
    """One GraphQL query for the contribution calendar and language bytes."""
    query = f"""
    query {{
      user(login: "{USERNAME}") {{
        contributionsCollection {{
          contributionCalendar {{
            totalContributions
            weeks {{
              contributionDays {{
                date
                contributionCount
              }}
            }}
          }}
        }}
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {{
          nodes {{
            stargazerCount
            languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{
              edges {{
                size
                node {{ name }}
              }}
            }}
          }}
        }}
      }}
    }}
    """
    payload = request_json(GRAPHQL, token, method="POST", payload={"query": query}, accept="application/json")
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]["user"]


def compute_streaks(weeks):
    """Return (current_streak, longest_streak) in days from the calendar."""
    active_dates = sorted(
        {
            date.fromisoformat(day["date"])
            for week in weeks
            for day in week.get("contributionDays", [])
            if day.get("contributionCount", 0) > 0
        }
    )
    if not active_dates:
        return 0, 0

    longest = run = 1
    for previous, current in zip(active_dates, active_dates[1:]):
        if (current - previous).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    current = 0
    today = date.today()
    if (today - active_dates[-1]).days <= 1:
        current = 1
        for previous, last in zip(reversed(active_dates[:-1]), reversed(active_dates[1:])):
            if (last - previous).days == 1:
                current += 1
            else:
                break
    return current, longest


def top_languages(graphql_repos, rest_repos):
    """Share of each language among all repo bytes (GraphQL, with REST fallback)."""
    sizes = {}
    for repo in graphql_repos:
        for edge in repo.get("languages", {}).get("edges", []):
            name = edge["node"]["name"]
            sizes[name] = sizes.get(name, 0) + edge["size"]
    if not sizes:
        # Fallback: count repos per primary language from the REST listing.
        for repo in rest_repos:
            name = repo.get("language")
            if name:
                sizes[name] = sizes.get(name, 0) + 1
    total = sum(sizes.values())
    if not total:
        return {}
    ranked = sorted(sizes.items(), key=lambda item: item[1], reverse=True)
    return {name: round(size / total * 100, 2) for name, size in ranked[:LANG_COUNT]}


def overview_stats(token):
    """Stars, commits, PRs and issues via the REST API; returns (stats, repos)."""
    user = request_json(f"{REST}/users/{USERNAME}", token)

    try:
        repos = paginate(f"{REST}/users/{USERNAME}/repos?type=owner", token)
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, OSError, http.client.HTTPException) as error:
        print(f"  repos listing for {USERNAME} failed: {error}")
        repos = []

    def search_total(path, query):
        try:
            payload = request_json(f"{REST}{path}?q={query}&per_page=1", token)
            return payload.get("total_count")
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError, OSError, http.client.HTTPException) as error:
            print(f"  search for '{query}' failed: {error}")
            return None

    contributed_repos = set()
    try:
        pulls = paginate(
            f"{REST}/search/issues?q=type:pr+author:{USERNAME}+is:merged",
            token,
            key="items",
            max_pages=10,
        )
        contributed_repos.update(repo for pull in pulls if (repo := pull.get("repository_url")))
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, OSError, http.client.HTTPException) as error:
        print(f"  search for merged pull requests failed: {error}")

    stats = {
        "public_repos": user.get("public_repos"),
        "stars_received": sum(repo.get("stargazers_count", 0) for repo in repos),
        "total_commits": search_total("/search/commits", f"author:{USERNAME}"),
        "pull_requests_opened": search_total("/search/issues", f"type:pr+author:{USERNAME}"),
        "issues_opened": search_total("/search/issues", f"type:issue+author:{USERNAME}"),
        "repos_contributed_to": len(contributed_repos),
    }
    return stats, repos


def render(stats):
    return json.dumps(stats, indent=4, ensure_ascii=False)


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("No GitHub token found, skipping GitHub stats update")
        return

    stats = {"overview": {}, "contributions": {}, "top_languages": {}}
    repos = []

    try:
        overview, repos = overview_stats(token)
        stats["overview"] = overview
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, OSError, http.client.HTTPException) as error:
        print(f"Could not fetch overview stats: {error}")

    try:
        profile = graphql_user(token)
        weeks = profile["contributionsCollection"]["contributionCalendar"].get("weeks", [])
        current_streak, longest_streak = compute_streaks(weeks)
        stats["contributions"] = {
            "total": profile["contributionsCollection"]["contributionCalendar"].get("totalContributions"),
            "current_streak": current_streak,
            "longest_streak": longest_streak,
        }
        stats["top_languages"] = top_languages(profile["repositories"]["nodes"], repos)
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, RuntimeError) as error:
        print(f"Could not fetch GraphQL stats: {error}")

    update_section("github", render(stats))


if __name__ == "__main__":
    main()
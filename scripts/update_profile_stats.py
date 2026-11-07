#!/usr/bin/env python3
"""Update the profile SVGs with live GitHub numbers.

Fetches public data from the GitHub API with no auth:
  GET https://api.github.com/users/saurav73            -> public_repos, followers
  GET https://api.github.com/users/saurav73/repos?per_page=100
      -> repos with a detected language, top 6 languages by repo count

Updates assets/hero.svg chips (REPOS, FOLLOWERS; MISSIONS stays 4, it is a
curated list) and assets/id-dashboard.svg KPIs (REPOS, FOLLOWERS,
WITH LANGUAGE), the "checked" date, and the REPOS BY LANGUAGE bar chart
(top 6 languages, bars scaled to a max height of 84px).

Run from anywhere: python3 scripts/update_profile_stats.py [--root PATH]
Exits 0 on success. Only rewrites a file when something actually changed.
"""

import argparse
import collections
import datetime
import json
import re
import sys
import urllib.request
from html import escape

USER = "saurav73"
API = "https://api.github.com"
BAR_X = [470, 586, 702, 818, 934, 1050]
BAR_W = 70
BASELINE = 420
MAX_H = 84
BAR_BEGINS = ["0.4s", "0.55s", "0.7s", "0.85s", "1.0s", "1.15s"]


def fetch_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "saurav73-profile-stats-updater",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise RuntimeError(f"GitHub API {url} returned HTTP {resp.status}")
        return json.load(resp)


def fetch_stats():
    user = fetch_json(f"{API}/users/{USER}")
    repos = fetch_json(f"{API}/users/{USER}/repos?per_page=100")
    langs = [r["language"] for r in repos if r.get("language")]
    top = collections.Counter(langs).most_common(6)
    return {
        "repos": user["public_repos"],
        "followers": user["followers"],
        "with_language": len(langs),
        "languages": top,  # list of (name, count), count desc, ties in repo order
        "checked": datetime.date.today().isoformat(),
    }


def replace_number_before_label(svg, label, value, where):
    """Replace the number in the <text> element directly before the label text."""
    pattern = re.compile(
        r'(<text[^>]*>)(\d+)(</text>\s*<text[^>]*>' + re.escape(label) + r'</text>)'
    )
    new_svg, n = pattern.subn(lambda m: m.group(1) + str(value) + m.group(3), svg, count=1)
    if n != 1:
        raise RuntimeError(f"{where}: could not find number before label {label!r}")
    return new_svg


def rebuild_bars(svg, languages, where):
    """Rebuild the REPOS BY LANGUAGE bar groups with fresh counts."""
    if not languages:
        raise RuntimeError(f"{where}: no languages found")
    max_count = languages[0][1]
    groups = []
    for i, (name, count) in enumerate(languages):
        h = max(1, round(count / max_count * MAX_H))
        y = BASELINE - h
        x = BAR_X[i]
        cx = x + BAR_W // 2
        groups.append(
            f'<g><rect x="{x}" y="{y}" width="{BAR_W}" height="{h}" rx="6" fill="#D4A017">'
            f'<animate attributeName="height" values="0;{h}" keyTimes="0;1" dur="0.6s" begin="{BAR_BEGINS[i]}" fill="both"/>'
            f'<animate attributeName="y" values="{BASELINE};{y}" keyTimes="0;1" dur="0.6s" begin="{BAR_BEGINS[i]}" fill="both"/>'
            f'</rect><text x="{cx}" y="{y - 8}" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="14" font-weight="700" fill="#F5C542" text-anchor="middle">{count}</text>'
            f'<text x="{cx}" y="440" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="13" fill="#8B949E" text-anchor="middle">{escape(name)}</text></g>'
        )
    block = "".join(groups)
    pattern = re.compile(
        r'(REPOS BY LANGUAGE</text>\n)(.*?)(\n<line x1="440" y1="420")', re.DOTALL
    )
    new_svg, n = pattern.subn(lambda m: m.group(1) + block + m.group(3), svg, count=1)
    if n != 1:
        raise RuntimeError(f"{where}: could not find bar chart block")
    return new_svg


def update_hero(path, stats, changes):
    svg = open(path).read()
    orig = svg
    svg = replace_number_before_label(svg, "REPOS", stats["repos"], "hero.svg")
    svg = replace_number_before_label(svg, "FOLLOWERS", stats["followers"], "hero.svg")
    if svg != orig:
        open(path, "w").write(svg)
        changes.append(f"hero.svg: REPOS={stats['repos']}, FOLLOWERS={stats['followers']}")
    return svg


def update_dashboard(path, stats, changes):
    svg = open(path).read()
    orig = svg
    svg = replace_number_before_label(svg, "REPOS", stats["repos"], "id-dashboard.svg")
    svg = replace_number_before_label(svg, "FOLLOWERS", stats["followers"], "id-dashboard.svg")
    svg = replace_number_before_label(svg, "WITH LANGUAGE", stats["with_language"], "id-dashboard.svg")
    svg, n = re.subn(r"checked \d{4}-\d{2}-\d{2}", "checked " + stats["checked"], svg, count=1)
    if n != 1:
        raise RuntimeError("id-dashboard.svg: could not find checked date")
    svg = rebuild_bars(svg, stats["languages"], "id-dashboard.svg")
    if svg != orig:
        open(path, "w").write(svg)
        changes.append(
            f"id-dashboard.svg: REPOS={stats['repos']}, FOLLOWERS={stats['followers']}, "
            f"WITH LANGUAGE={stats['with_language']}, checked={stats['checked']}, "
            f"languages={stats['languages']}"
        )
    return svg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None,
                        help="repo root (default: parent of the scripts dir)")
    args = parser.parse_args()
    root = args.root or __file__.rsplit("/scripts/", 1)[0]
    stats = fetch_stats()
    print(f"live API: repos={stats['repos']} followers={stats['followers']} "
          f"with_language={stats['with_language']} languages={stats['languages']}")
    changes = []
    update_hero(f"{root}/assets/hero.svg", stats, changes)
    update_dashboard(f"{root}/assets/id-dashboard.svg", stats, changes)
    if changes:
        for c in changes:
            print("changed:", c)
    else:
        print("no changes: SVGs already match the live API")
    return 0


if __name__ == "__main__":
    sys.exit(main())

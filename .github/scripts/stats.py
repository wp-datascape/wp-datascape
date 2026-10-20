"""Buat kartu stats SVG (transparan, gelap + terang) dari data GitHub, termasuk repo private."""
import json
import os
import sys
import urllib.request
from html import escape

TOKEN = os.environ["STATS_TOKEN"]
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist"

QUERY = """
query {
  viewer {
    login
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalPullRequestReviewContributions
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

THEMES = {
    "dark": {"title": "#7aa2f7", "icon": "#bb9af7", "text": "#a9b1d6", "muted": "#6b7394"},
    "light": {"title": "#3d59a1", "icon": "#7e57c2", "text": "#3b4252", "muted": "#6b7394"},
}
FONT = "font-family:'Segoe UI',Ubuntu,Sans-Serif"


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]["viewer"]


def collect(v):
    cc = v["contributionsCollection"]
    repos = v["repositories"]["nodes"]
    langs = {}
    for repo in repos:
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            size, color = langs.get(name, (0, e["node"]["color"] or "#8b949e"))
            langs[name] = (size + e["size"], color)
    total = sum(s for s, _ in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: kv[1][0], reverse=True)[:6]
    return {
        "rows": [
            ("Commits (last year)", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
            ("Pull requests (last year)", cc["totalPullRequestContributions"]),
            ("Code reviews (last year)", cc["totalPullRequestReviewContributions"]),
            ("Stars earned", sum(r["stargazerCount"] for r in repos)),
            ("Repositories (incl. private)", v["repositories"]["totalCount"]),
        ],
        "langs": [(n, s / total * 100, c) for n, (s, c) in top],
    }


def stats_svg(rows, t):
    h = 50 + len(rows) * 25
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="360" height="{h}" viewBox="0 0 360 {h}">',
           f'<text x="0" y="22" style="{FONT};font-size:18px;font-weight:600" fill="{t["title"]}">GitHub Stats</text>']
    for i, (label, value) in enumerate(rows):
        y = 55 + i * 25
        out.append(f'<circle cx="6" cy="{y - 5}" r="3.5" fill="{t["icon"]}"/>')
        out.append(f'<text x="20" y="{y}" style="{FONT};font-size:14px" fill="{t["text"]}">{escape(label)}</text>')
        out.append(f'<text x="350" y="{y}" text-anchor="end" style="{FONT};font-size:14px;font-weight:700" fill="{t["title"]}">{value:,}</text>')
    out.append("</svg>")
    return "\n".join(out)


def langs_svg(langs, t):
    w, rows = 360, (len(langs) + 1) // 2
    h = 70 + rows * 24
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
           f'<text x="0" y="22" style="{FONT};font-size:18px;font-weight:600" fill="{t["title"]}">Top Languages</text>',
           '<clipPath id="bar"><rect x="0" y="36" width="350" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">']
    x = 0.0
    for _, pct, color in langs:
        seg = pct / sum(p for _, p, _ in langs) * 350
        out.append(f'<rect x="{x:.2f}" y="36" width="{seg + 0.5:.2f}" height="10" fill="{color}"/>')
        x += seg
    out.append("</g>")
    for i, (name, pct, color) in enumerate(langs):
        cx, cy = (i % 2) * 180, 70 + (i // 2) * 24
        out.append(f'<circle cx="{cx + 6}" cy="{cy + 7}" r="5" fill="{color}"/>')
        out.append(f'<text x="{cx + 18}" y="{cy + 12}" style="{FONT};font-size:13px" fill="{t["text"]}">{escape(name)} <tspan fill="{t["muted"]}">{pct:.1f}%</tspan></text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    data = collect(fetch())
    os.makedirs(OUT, exist_ok=True)
    for mode, t in THEMES.items():
        with open(f"{OUT}/stats-{mode}.svg", "w", encoding="utf-8") as f:
            f.write(stats_svg(data["rows"], t))
        with open(f"{OUT}/langs-{mode}.svg", "w", encoding="utf-8") as f:
            f.write(langs_svg(data["langs"], t))
    print("rows:", data["rows"])
    print("langs:", [(n, round(p, 1)) for n, p, _ in data["langs"]])


main()

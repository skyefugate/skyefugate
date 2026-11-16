#!/usr/bin/env python3
"""Build the profile graphics as local SVGs (no third-party image services).

Run from the repo root:  python3 .assets/build.py
Writes assets/banner.svg, focus.svg and talks.svg (light/dark CSS inside each),
plus the stats board in four variants, assets/board-{wide,narrow}-{dark,light}.svg
(see board.py). Yesterday's numbers live in .assets/state.json so the board can
show change since the last run, and the README <picture> block is rewritten
with a fresh ?v= stamp.
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import board

OUT = Path(__file__).resolve().parent.parent / "assets"

# Grafana-ish palette, same family as the EIT org page.
BLUE_L, BLUE, GREEN, PURPLE, ORANGE, YELLOW, RED = (
    "#8AB8FF",
    "#5794F2",
    "#73BF69",
    "#B877D9",
    "#FF9830",
    "#FADE2A",
    "#F2495C",
)
PALETTE = [BLUE, BLUE_L, GREEN, PURPLE, ORANGE, YELLOW, RED]

FONT = {  # 5x5 pixel letters
    "S": [".####", "#....", ".###.", "....#", "####."],
    "K": ["#...#", "#..#.", "###..", "#..#.", "#...#"],
    "Y": ["#...#", ".#.#.", "..#..", "..#..", "..#.."],
    "E": ["#####", "#....", "####.", "#....", "#####"],
    "F": ["#####", "#....", "####.", "#....", "#...."],
    "U": ["#...#", "#...#", "#...#", "#...#", ".###."],
    "G": [".####", "#....", "#..##", "#...#", ".####"],
    "A": [".###.", "#...#", "#####", "#...#", "#...#"],
    "T": ["#####", "..#..", "..#..", "..#..", "..#.."],
}

STYLE = """<style>
  .t { font: 600 15px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #1f2328; }
  .h { font: 600 14px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #1f2328; }
  .l { font: 12px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #424a53; }
  .m { font: 12px ui-monospace, SFMono-Regular, Menlo, monospace; fill: #59636e; }
  .k { font: 600 11px ui-monospace, SFMono-Regular, Menlo, monospace; fill: #59636e; letter-spacing: 2px; }
  .card { fill: #f6f8fa; stroke: #d0d7de; }
  @media (prefers-color-scheme: dark) {
    .t, .h { fill: #e6edf3; }
    .l { fill: #c9d1d9; }
    .m, .k { fill: #9198a1; }
    .card { fill: #161b22; stroke: #30363d; }
  }
</style>"""


def wordmark(text: str, x0: float, y0: float, cw: int, ch: int) -> str:
    rects, x = [], x0
    for c in text:
        if c == " ":
            x += cw * 3
            continue
        for r, row in enumerate(FONT[c]):
            for col, bit in enumerate(row):
                if bit == "#":
                    rects.append(
                        f'<rect x="{x + col * cw:g}" y="{y0 + r * ch:g}" width="{cw}" height="{ch}"/>'
                    )
        x += cw * 6
    return "".join(rects)


def text_width(text: str, cw: int) -> int:
    return sum(cw * 3 if c == " " else cw * 6 for c in text) - cw


def banner() -> str:
    W, H, cw, ch, name = 760, 200, 10, 17, "SKYE FUGATE"
    x0 = (W - text_width(name, cw)) / 2
    y0 = 30
    # Signal pulses: rings that grow out of two "nodes", like a ping.
    nodes = [(52, 70, BLUE), (708, 120, PURPLE)]
    pulses = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="4" fill="{c}"/>'
        f'<circle class="p" cx="{cx}" cy="{cy}" r="4" stroke="{c}" style="animation-delay:{i * 1.2}s"/>'
        f'<circle class="p" cx="{cx}" cy="{cy}" r="4" stroke="{c}" style="animation-delay:{i * 1.2 + 1.2}s"/>'
        for i, (cx, cy, c) in enumerate(nodes)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Skye Fugate">
<defs>
  <linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BLUE_L}"/><stop offset=".5" stop-color="{BLUE}"/><stop offset="1" stop-color="{PURPLE}"/></linearGradient>
  <linearGradient id="shine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <clipPath id="word">{wordmark(name, x0, y0, cw, ch)}</clipPath>
</defs>
<style>
  .s {{ font: 600 14px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; fill: #59636e; letter-spacing: 6px; }}
  .p {{ fill: none; stroke-width: 1.5; transform-box: fill-box; transform-origin: center; animation: ping 2.4s ease-out 3 both; }}
  .sweep {{ animation: sweep 3s ease-in-out 1s 2 both; }}
  @keyframes ping {{ from {{ transform: scale(1); opacity: .9; }} to {{ transform: scale(7); opacity: 0; }} }}
  @keyframes sweep {{ from {{ transform: translateX(-200px); }} to {{ transform: translateX({W}px); }} }}
  @media (prefers-color-scheme: dark) {{ .s {{ fill: #9198a1; }} }}
  @media (prefers-reduced-motion: reduce) {{ .p, .sweep {{ animation: none; opacity: 0; }} }}
</style>
<path d="M52 70 C 200 150, 560 20, 708 120" fill="none" stroke="url(#g)" stroke-width="1.5" stroke-dasharray="4 6" opacity=".5"/>
{pulses}
<g fill="{BLUE}" opacity=".35" shape-rendering="crispEdges" transform="translate(4 4)">{wordmark(name, x0, y0, cw, ch)}</g>
<g fill="url(#g)" shape-rendering="crispEdges">{wordmark(name, x0, y0, cw, ch)}</g>
<g clip-path="url(#word)"><rect class="sweep" x="0" y="0" width="160" height="{H}" fill="url(#shine)"/></g>
<text class="s" x="{W / 2}" y="{H - 34}" text-anchor="middle">─── NETWORK · CLOUD · AI ───</text>
</svg>
"""


def cards(title: str, items: list[tuple[str, str, str, str]], cols: int = 2) -> str:
    """items: (heading, line1, line2, color). Cards with a color stripe, like the EIT page."""
    W, pad, gap, ch = 760, 20, 20, 92
    cwid = (W - 2 * pad - gap * (cols - 1)) / cols
    rows = (len(items) + cols - 1) // cols
    H = 50 + rows * (ch + gap)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(title)}">',
        STYLE,
        f'<text class="t" x="{pad}" y="28">{escape(title)}</text>',
    ]
    for i, (head, l1, l2, color) in enumerate(items):
        x = pad + (i % cols) * (cwid + gap)
        y = 44 + (i // cols) * (ch + gap)
        out += [
            f'<rect class="card" x="{x:g}" y="{y}" width="{cwid:g}" height="{ch}" rx="8"/>',
            f'<rect x="{x:g}" y="{y}" width="6" height="{ch}" rx="3" fill="{color}"/>',
            f'<text class="h" x="{x + 20:g}" y="{y + 30}">{escape(head)}</text>',
            f'<text class="l" x="{x + 20:g}" y="{y + 54}">{escape(l1)}</text>',
            f'<text class="m" x="{x + 20:g}" y="{y + 74}">{escape(l2)}</text>',
        ]
    out.append("</svg>\n")
    return "\n".join(out)


FOCUS = [
    (
        "AI for networks",
        "Live topology, blast-radius review",
        "agents · prompts · IaC docs",
        BLUE,
    ),
    (
        "Network experience",
        "Telemetry agents and scoring",
        "python · influxdb · grafana",
        GREEN,
    ),
    (
        "Infra as code",
        "AWS, NetBox and Grafana as code",
        "cloudformation · ansible · git sync",
        PURPLE,
    ),
    (
        "Off the clock",
        "Plane tracking, Folding@home",
        "shooting clays · @SecKC",
        ORANGE,
    ),
]

TALKS = [
    (
        "SecKC · Sep 2026",
        "AI for network architecture",
        "topology · blast radius · IaC docs",
        BLUE,
    ),
    (
        "SecDSM · Dec 2025",
        "AI network troubleshooting",
        "C2 detection · VPC flow logs",
        PURPLE,
    ),
]

USER = "skyefugate"
LOCAL = ZoneInfo("America/Chicago")  # commit hours are shown in my time zone
ROOT = OUT.parent
STATE = ROOT / ".assets" / "state.json"
README = ROOT / "README.md"
MARK_START, MARK_END = "<!-- board:start -->", "<!-- board:end -->"


def gh(*args: str):
    return json.loads(
        subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout
    )


def fetch(today: date) -> dict:
    """Live data from GitHub.

    Public repos only, so a run on my Mac and the daily run on GitHub (which
    only has the built-in token) draw the same numbers, and the one repo name
    shown (busiest) can never be a private one. Contribution counts still
    include private work when "Include private contributions" is on.

    Commit hours and line counts come from my own commits on the default
    branch of my public repos; bot commits (the nightly refresh) are skipped.
    """
    q = """query($login: String!, $from: DateTime!, $year: GitTimestamp!) { user(login: $login) {
      createdAt followers { totalCount }
      contributionsCollection { totalCommitContributions totalPullRequestContributions
        totalPullRequestReviewContributions totalIssueContributions
        totalRepositoriesWithContributedCommits
        contributionCalendar { totalContributions
          weeks { contributionDays { date weekday contributionCount } } } }
      recent: contributionsCollection(from: $from) {
        commitContributionsByRepository(maxRepositories: 25) {
          repository { name isPrivate } contributions { totalCount } } }
      repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
        totalCount nodes {
          languages(first: 10) { edges { size node { name } } }
          defaultBranchRef { target { ... on Commit {
            history(first: 100, since: $year) {
              nodes { authoredDate additions deletions author { user { login } } } } } } } } } } }"""
    since = (today - timedelta(days=90)).isoformat() + "T00:00:00Z"
    year = (today - timedelta(days=365)).isoformat() + "T00:00:00Z"
    u = gh(
        "api",
        "graphql",
        "-f",
        f"query={q}",
        "-f",
        f"login={USER}",
        "-f",
        f"from={since}",
        "-f",
        f"year={year}",
    )["data"]["user"]
    cc = u["contributionsCollection"]
    weeks_raw = cc["contributionCalendar"]["weeks"]
    cal = [d for w in weeks_raw for d in w["contributionDays"]]
    days = [d["contributionCount"] for d in cal]

    langs = Counter()
    hours, added, removed = [], 0, 0
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]] += e["size"]
        ref = repo["defaultBranchRef"]
        for c in ref["target"]["history"]["nodes"] if ref else []:
            if (c["author"]["user"] or {}).get("login") != USER:
                continue
            at = datetime.fromisoformat(c["authoredDate"].replace("Z", "+00:00"))
            hours.append(at.astimezone(LOCAL).hour)
            added += c["additions"]
            removed += c["deletions"]
    top = langs.most_common(6)
    total = sum(v for _, v in top) or 1
    public = [
        (r["repository"]["name"], r["contributions"]["totalCount"])
        for r in u["recent"]["commitContributionsByRepository"]
        if not r["repository"]["isPrivate"]
    ]
    joined = datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00")).date()
    return {
        "today": today.isoformat(),
        "total": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "reviews": cc["totalPullRequestReviewContributions"],
        "issues": cc["totalIssueContributions"],
        "repos_touched": cc["totalRepositoriesWithContributedCommits"],
        "followers": u["followers"]["totalCount"],
        "repos": u["repositories"]["totalCount"],
        "lang_count": len(langs),
        "streak": board.streak(days),
        "longest": board.longest_streak(days),
        "active": board.active_days(days),
        "best": board.best_day([(d["date"], d["contributionCount"]) for d in cal]),
        "weekdays": board.weekday_split(
            [(d["weekday"], d["contributionCount"]) for d in cal]
        ),
        "chrono": board.chronotype(hours),
        "lines": (added, removed) if hours else None,
        "since": joined.year,
        "years": (today - joined).days // 365,
        "weeks": [
            sum(d["contributionCount"] for d in w["contributionDays"])
            for w in weeks_raw
        ],
        "busiest": max(public, key=lambda r: r[1]) if public else None,
        "langs": [(k, v / total * 100) for k, v in top],
    }


def update_readme(block: str) -> None:
    text = README.read_text()
    a, b = text.index(MARK_START), text.index(MARK_END)
    README.write_text(text[: a + len(MARK_START)] + "\n" + block + "\n" + text[b:])


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "banner.svg").write_text(banner())
    (OUT / "focus.svg").write_text(cards("What I work on", FOCUS))
    (OUT / "talks.svg").write_text(cards("Talks", TALKS))

    today = datetime.now(timezone.utc).date()
    data = fetch(today)
    state = json.loads(STATE.read_text()) if STATE.exists() else None
    base = board.baseline(state, data["today"])
    values = {k: data[k] for k in board.DELTA_KEYS}
    dl = board.deltas(values, base)
    for size in ("wide", "narrow"):
        for theme in ("dark", "light"):
            (OUT / f"board-{size}-{theme}.svg").write_text(
                board.render(data, dl, base, size == "wide", theme)
            )
    STATE.write_text(
        json.dumps(board.next_state(state, data["today"], values), indent=2) + "\n"
    )
    update_readme(
        board.picture(data["today"].replace("-", ""), board.summary(data, dl, base))
    )
    print("wrote", ", ".join(p.name for p in sorted(OUT.glob("*.svg"))))

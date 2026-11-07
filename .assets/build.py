#!/usr/bin/env python3
"""Build the profile graphics as local SVGs (no third-party image services).

Run from the repo root:  python3 .assets/build.py
Writes assets/banner.svg, assets/focus.svg and assets/talks.svg.
Every SVG carries its own light/dark CSS, so it reads well in both GitHub themes.
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from html import escape
from pathlib import Path

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
    ("Off the clock", "Plane tracking, Folding@home", "trapshooting · @SecKC", ORANGE),
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
LANG_COLORS = {
    "Python": BLUE,
    "Shell": GREEN,
    "HTML": ORANGE,
    "JavaScript": YELLOW,
    "Kotlin": PURPLE,
    "Ruby": RED,
    "CSS": BLUE_L,
    "TypeScript": "#3178C6",
}


def gh(*args: str):
    return json.loads(
        subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout
    )


def fetch() -> dict:
    """Live data from GitHub. Only totals leave this function: no repo names.

    Public repos only, so a run on my Mac and the daily run on GitHub (which
    only has the built-in token) draw the same numbers. Contribution counts
    still include private work when "Include private contributions" is on.
    """
    q = (
        """{ user(login: "%s") {
      contributionsCollection { totalCommitContributions totalPullRequestContributions
        contributionCalendar { totalContributions weeks { contributionDays { contributionCount } } } }
      repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) { totalCount
        nodes { languages(first: 10) { edges { size node { name } } } } } } }"""
        % USER
    )
    u = gh("api", "graphql", "-f", f"query={q}")["data"]["user"]
    cc = u["contributionsCollection"]
    langs = Counter()
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]] += e["size"]
    weeks = [
        sum(d["contributionCount"] for d in w["contributionDays"])
        for w in cc["contributionCalendar"]["weeks"]
    ]
    return {
        "total": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "repos": u["repositories"]["totalCount"],
        "langs": langs,
        "weeks": weeks,
    }


def stats(d: dict) -> str:
    W, pad, gap, n = 760, 20, 16, 4
    bw = (W - 2 * pad - gap * (n - 1)) / n
    tiles = [
        ("CONTRIBUTIONS", d["total"], "last 12 months", BLUE),
        ("COMMITS", d["commits"], "last 12 months", GREEN),
        ("PULL REQUESTS", d["prs"], "last 12 months", PURPLE),
        ("PUBLIC REPOS", d["repos"], "built from scratch", ORANGE),
    ]
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="150" viewBox="0 0 {W} 150" role="img" aria-label="GitHub stats">',
        STYLE,
        f'<text class="t" x="{pad}" y="28">By the numbers</text>',
    ]
    for i, (k, v, sub, c) in enumerate(tiles):
        x = pad + i * (bw + gap)
        out += [
            f'<rect class="card" x="{x:g}" y="44" width="{bw:g}" height="92" rx="8"/>',
            f'<rect x="{x:g}" y="44" width="{bw:g}" height="4" rx="2" fill="{c}"/>',
            f'<text class="k" x="{x + 16:g}" y="72">{k}</text>',
            f'<text x="{x + 16:g}" y="106" style="font:700 30px -apple-system,Segoe UI,Helvetica,Arial,sans-serif" fill="{c}">{v}</text>',
            f'<text class="m" x="{x + 16:g}" y="126">{sub}</text>',
        ]
    out.append("</svg>\n")
    return "\n".join(out)


def languages(d: dict) -> str:
    W, pad = 760, 20
    top = d["langs"].most_common(6)
    total = sum(v for _, v in top) or 1
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="120" viewBox="0 0 {W} 120" role="img" aria-label="Languages">',
        STYLE,
        f'<text class="t" x="{pad}" y="28">Languages</text>',
        f'<clipPath id="bar"><rect x="{pad}" y="44" width="{W - 2 * pad}" height="14" rx="7"/></clipPath><g clip-path="url(#bar)">',
    ]
    x, legend = pad, []
    for i, (name, v) in enumerate(top):
        w = (W - 2 * pad) * v / total
        c = LANG_COLORS.get(name, PALETTE[i % len(PALETTE)])
        out.append(f'<rect x="{x:g}" y="44" width="{w + 1:g}" height="14" fill="{c}"/>')
        x += w
        legend.append((name, v / total * 100, c))
    out.append("</g>")
    col = (W - 2 * pad) / 3
    for i, (name, pct, c) in enumerate(legend):
        lx, ly = pad + (i % 3) * col, 84 + (i // 3) * 22
        out += [
            f'<circle cx="{lx + 6:g}" cy="{ly - 4}" r="5" fill="{c}"/>',
            f'<text class="l" x="{lx + 18:g}" y="{ly}">{escape(name)} <tspan class="m">{pct:.1f}%</tspan></text>',
        ]
    out.append("</svg>\n")
    return "\n".join(out).replace(
        'height="120" viewBox="0 0 760 120"',
        f'height="{84 + 22 * ((len(legend) + 2) // 3)}" viewBox="0 0 760 {84 + 22 * ((len(legend) + 2) // 3)}"',
    )


def activity(d: dict) -> str:
    W, H, pad, top, bot = 760, 220, 20, 50, 190
    weeks = d["weeks"]
    peak = max(weeks) or 1
    step = (W - 2 * pad) / max(len(weeks) - 1, 1)
    pts = [(pad + i * step, bot - (bot - top) * v / peak) for i, v in enumerate(weeks)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = (
        f"M{pad},{bot} L"
        + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        + f" L{W - pad},{bot} Z"
    )
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{PURPLE}"/>'
        for (x, y), v in zip(pts, weeks)
        if v
    )
    grid = "".join(
        f'<line x1="{pad}" x2="{W - pad}" y1="{bot - (bot - top) * f:.1f}" y2="{bot - (bot - top) * f:.1f}" class="grid"/>'
        for f in (0, 0.5, 1)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Weekly activity">
{STYLE}
<defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BLUE}" stop-opacity=".45"/><stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></linearGradient>
<linearGradient id="ln" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{BLUE_L}"/><stop offset=".5" stop-color="{BLUE}"/><stop offset="1" stop-color="{PURPLE}"/></linearGradient></defs>
<style>.grid {{ stroke: #d0d7de; stroke-dasharray: 3 4; }} @media (prefers-color-scheme: dark) {{ .grid {{ stroke: #30363d; }} }}</style>
<text class="t" x="{pad}" y="28">Activity</text>
<text class="m" x="{W - pad}" y="28" text-anchor="end">contributions per week · peak {peak}</text>
{grid}
<path d="{area}" fill="url(#fill)"/>
<polyline points="{line}" fill="none" stroke="url(#ln)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
{dots}
<text class="m" x="{pad}" y="{H - 10}">12 months ago</text>
<text class="m" x="{W - pad}" y="{H - 10}" text-anchor="end">now</text>
</svg>
"""


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "banner.svg").write_text(banner())
    (OUT / "focus.svg").write_text(cards("What I work on", FOCUS))
    (OUT / "talks.svg").write_text(cards("Talks", TALKS))
    data = fetch()
    (OUT / "stats.svg").write_text(stats(data))
    (OUT / "languages.svg").write_text(languages(data))
    (OUT / "activity.svg").write_text(activity(data))
    print("wrote", ", ".join(p.name for p in sorted(OUT.glob("*.svg"))))

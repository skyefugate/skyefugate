"""The stats board: one SVG in four variants (wide/narrow x dark/light).

Pure functions only; build.py fetches the data and writes the files.

Motion, in order, all on one easing curve:
  1. every text line decodes from random glyphs into its real value
  2. the weekly bars grow up from the baseline, one after another
  3. the language bar slides out sideways
Then the board goes still, except the current week's bar, which breathes
because that week is still in progress.

No JavaScript (GitHub strips it from SVGs). Each line is drawn FRAMES times
with more characters resolved per copy, and each copy is shown for STEP
seconds. The real text is the default state: with animation off, or in a
viewer that ignores CSS animation, the board is complete and still.

Green and red stay reserved for up and down; the other accents are decoration.
"""

from __future__ import annotations

import random
from collections import Counter
from html import escape

FRAMES = 14
STEP = 0.05  # seconds each decode copy is visible
GLYPHS = "0123456789ABCDEF#%&*+=/<>$"
EASE = "cubic-bezier(.16,1,.3,1)"  # fast start, soft landing
CHAR = 0.6  # monospace advance width, in em
MONO = (
    "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
)
WEEKDAYS = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")  # GitHub weekday 0 = Sun

THEMES = {
    "dark": {
        "bg": "#0d1117",
        "line": "#30363d",
        "fg": "#e6edf3",
        "mu": "#9198a1",
        "up": "#3fb950",
        "dn": "#f85149",
        "acc": ["#5794F2", "#B877D9", "#FF9830", "#5AC8FA", "#FF7383", "#FADE2A"],
        "grad": ["#8AB8FF", "#5794F2", "#B877D9", "#FF7383"],
        "now": "#FF9830",
    },
    "light": {
        "bg": "#ffffff",
        "line": "#d0d7de",
        "fg": "#1f2328",
        "mu": "#59636e",
        "up": "#1a7f37",
        "dn": "#d1242f",
        "acc": ["#1F60C4", "#8F3BB8", "#C4580E", "#0B7FA8", "#C4306A", "#9A6700"],
        "grad": ["#5794F2", "#1F60C4", "#8F3BB8", "#C4306A"],
        "now": "#E55400",
    },
}

# GitHub linguist colours: here colour means "which language".
LANG_COLORS = {
    "Python": "#3572A5",
    "HTML": "#e34c26",
    "CSS": "#663399",
    "Shell": "#89e051",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Kotlin": "#A97BFF",
    "Ruby": "#701516",
    "Go": "#00ADD8",
    "PowerShell": "#012456",
}

DELTA_KEYS = ("total", "commits", "prs", "reviews", "issues", "followers")


# ---------- numbers ----------


def streak(days: list[int]) -> int:
    """Consecutive active days ending today. Today counts as in progress, so a
    quiet today does not break a streak that ran through yesterday."""
    run = days[:-1] if days and days[-1] == 0 else days
    n = 0
    for c in reversed(run):
        if not c:
            break
        n += 1
    return n


def longest_streak(days: list[int]) -> int:
    best = cur = 0
    for c in days:
        cur = cur + 1 if c else 0
        best = max(best, cur)
    return best


def active_days(days: list[int], window: int = 365) -> int:
    return sum(1 for c in days[-window:] if c)


def best_day(dated: list[tuple[str, int]]) -> tuple[int, str] | None:
    """(count, date) of the biggest day; the earliest wins a tie."""
    top = max(dated, key=lambda d: d[1], default=None)
    return (top[1], top[0]) if top and top[1] else None


def weekday_split(dated: list[tuple[int, int]]) -> tuple[str, float, float] | None:
    """dated: (weekday 0=Sun, count). -> (favourite day, its %, weekend %)."""
    by = Counter()
    for wd, c in dated:
        by[wd] += c
    total = sum(by.values())
    if not total:
        return None
    fav = max(range(7), key=lambda wd: (by[wd], -wd))
    return WEEKDAYS[fav], by[fav] / total * 100, (by[0] + by[6]) / total * 100


def chronotype(hours: list[int]) -> tuple[int, str, float] | None:
    """hours: local commit hours. -> (peak hour, persona, % in that persona)."""
    if not hours:
        return None

    def kind(h):
        if 5 <= h < 9:
            return "early bird"
        if 9 <= h < 17:
            return "day shift"
        if 17 <= h < 22:
            return "evening coder"
        return "night owl"

    peak = Counter(hours).most_common(1)[0][0]
    kinds = Counter(kind(h) for h in hours)
    who, n = kinds.most_common(1)[0]
    return peak, who, n / len(hours) * 100


def fmt_hour(h: int) -> str:
    return f"{h % 12 or 12} {'am' if h < 12 else 'pm'}"


def fmt_k(n: int) -> str:
    return f"{n / 1000:.1f}k" if n >= 1000 else str(n)


def baseline(state: dict | None, today: str) -> dict | None:
    """The snapshot to diff against. A second run on the same day keeps the
    earlier baseline, so re-running never zeroes the change."""
    if not state:
        return None
    if state.get("date") == today:
        return state.get("prev")
    return {"date": state["date"], "values": state["values"]}


def next_state(state: dict | None, today: str, values: dict) -> dict:
    return {"date": today, "values": values, "prev": baseline(state, today)}


def deltas(values: dict, base: dict | None) -> dict:
    if not base:
        return {k: None for k in DELTA_KEYS}
    return {
        k: values[k] - base["values"][k]
        if k in base["values"] and k in values
        else None
        for k in DELTA_KEYS
    }


def fmt_delta(d: int | None) -> tuple[str, str] | None:
    """(text, class). Green up, red down, grey unchanged."""
    if d is None:
        return None
    if d > 0:
        return f"+{d}", "up"
    if d < 0:
        return f"\u2212{-d}", "dn"
    return "\u00b10", "mu"


# ---------- decode ----------


def frames(text: str, n: int = FRAMES) -> list[str]:
    """n scrambled copies of text, resolving left to right. Frame 0 is all
    glyphs; the real text itself is drawn separately as the final state.
    Seeded by the text, so an unchanged board renders byte-identical."""
    rng = random.Random(text)
    out = []
    for k in range(n):
        keep = len(text) * k // n
        out.append(
            "".join(
                c if i < keep or c == " " else rng.choice(GLYPHS)
                for i, c in enumerate(text)
            )
        )
    return out


class Board:
    def __init__(self, w: int, h: int, theme: str):
        self.w, self.h, self.t = w, h, THEMES[theme]
        self.body: list[str] = []
        self.lines = 0

    def text(
        self,
        s: str,
        x: float,
        y: float,
        cls: str,
        size: float,
        end: bool = False,
        fill: str | None = None,
    ) -> float:
        """One decoding line. Returns the line's estimated width in px."""
        start = 0.05 + min(self.lines, 30) * 0.025
        self.lines += 1
        anchor = ' text-anchor="end"' if end else ""
        paint = f' fill="{fill}"' if fill else ""
        pos = f'x="{x:g}" y="{y:g}"{anchor}{paint}'
        for i, f in enumerate(frames(s)):
            self.body.append(
                f'<text class="f {cls}" {pos} opacity="0" style="animation-delay:{start + i * STEP:.2f}s">{escape(f)}</text>'
            )
        done = start + FRAMES * STEP
        self.body.append(
            f'<text class="r {cls}" {pos} style="animation-delay:{done:.2f}s">{escape(s)}</text>'
        )
        return len(s) * size * CHAR

    def css(self) -> str:
        t = self.t
        return f"""<style>
text {{ font-family: {MONO}; }}
.h {{ font-size: 15px; font-weight: 700; letter-spacing: 1px; }}
.s {{ font-size: 11px; fill: {t["mu"]}; }}
.fv {{ font-size: 11px; fill: {t["fg"]}; }}
.lb {{ font-size: 10px; font-weight: 600; letter-spacing: 1px; }}
.v {{ font-size: 22px; font-weight: 600; fill: {t["fg"]}; }}
.d {{ font-size: 12px; font-weight: 600; }}
.n {{ font-size: 10px; fill: {t["mu"]}; }}
.up {{ fill: {t["up"]}; }} .dn {{ fill: {t["dn"]}; }} .mu {{ fill: {t["mu"]}; }}
.f {{ animation: flash {STEP}s linear; }}
.r {{ animation: in .01s linear backwards; }}
.b {{ transform-box: fill-box; transform-origin: 50% 100%; animation: grow .55s {EASE} backwards; }}
.b.now {{ animation: grow .55s {EASE} backwards, breathe 1.6s {EASE} 2.8s infinite alternate; }}
.lg {{ transform-box: fill-box; transform-origin: 0 50%; animation: slide .6s {EASE} backwards; }}
@keyframes flash {{ from, to {{ opacity: 1; }} }}
@keyframes in {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
@keyframes grow {{ from {{ transform: scaleY(0); }} }}
@keyframes slide {{ from {{ transform: scaleX(0); }} }}
@keyframes breathe {{ to {{ opacity: .35; }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>"""


# ---------- layout ----------


def tiles(d: dict, dl: dict) -> list[tuple[str, str, int | None, str]]:
    """(label, value, delta, note)"""
    best = d.get("best")
    return [
        ("CONTRIBUTIONS", str(d["total"]), dl.get("total"), ""),
        ("COMMITS", str(d["commits"]), dl.get("commits"), ""),
        ("PULL REQUESTS", str(d["prs"]), dl.get("prs"), ""),
        ("REVIEWS", str(d["reviews"]), dl.get("reviews"), ""),
        ("ISSUES", str(d["issues"]), dl.get("issues"), ""),
        ("STREAK", f"{d['streak']} d", None, f"best {d['longest']} d"),
        ("ACTIVE DAYS", f"{d['active']}/365", None, ""),
        ("BEST DAY", str(best[0]) if best else "0", None, best[1][5:] if best else ""),
        ("REPOS TOUCHED", str(d["repos_touched"]), None, ""),
        ("FOLLOWERS", str(d["followers"]), dl.get("followers"), ""),
        ("PUBLIC REPOS", str(d["repos"]), None, ""),
        ("LANGUAGES", str(d["lang_count"]), None, "used"),
    ]


def facts(d: dict) -> list[tuple[str, list[tuple[str, str]]]]:
    """(key, [(text, class)]): short lines, some with coloured segments."""
    out = []
    if d.get("busiest"):
        name, n = d["busiest"]
        out.append(
            (
                "BUSIEST 90D",
                [(f"{name} \u00b7 {n} commit{'s' if n != 1 else ''}", "fv")],
            )
        )
    ct = d.get("chrono")
    if ct:
        out.append(
            ("PEAK HOUR", [(f"{fmt_hour(ct[0])} \u00b7 {ct[1]} ({ct[2]:.0f}%)", "fv")])
        )
    wk = d.get("weekdays")
    if wk:
        out.append(
            ("FAVOURITE DAY", [(f"{wk[0]} \u00b7 {wk[1]:.0f}% of the year", "fv")])
        )
        out.append(("WEEKENDS", [(f"{wk[2]:.0f}% of contributions", "fv")]))
    lines = d.get("lines")
    if lines:
        out.append(
            (
                "LINES",
                [(f"+{fmt_k(lines[0])}", "up"), (f"\u2212{fmt_k(lines[1])}", "dn")],
            )
        )
    if d.get("since"):
        out.append(("JOINED", [(f"{d['since']} \u00b7 {d['years']} yrs ago", "fv")]))
    return out


def summary(d: dict, dl: dict, base: dict | None) -> str:
    since = f" since {base['date']}" if base else ""

    def chg(k):
        v = dl.get(k)
        return "" if v is None else f" ({v:+d}{since})"

    parts = [
        f"{d['total']} contributions{chg('total')}",
        f"{d['commits']} commits{chg('commits')}",
        f"{d['prs']} pull requests{chg('prs')}",
        f"{d['reviews']} reviews{chg('reviews')}",
        f"{d['issues']} issues{chg('issues')}",
        f"{d['followers']} followers{chg('followers')}",
    ]
    s = (
        f"Last 12 months: {', '.join(parts)}. "
        f"Current streak {d['streak']} day{'s' if d['streak'] != 1 else ''}, "
        f"longest {d['longest']}, active {d['active']} of 365 days, "
        f"{d['repos_touched']} repos touched, {d['repos']} public repos, "
        f"{d['lang_count']} languages used."
    )
    if d.get("best"):
        s += f" Best day {d['best'][1]} with {d['best'][0]}."
    for key, segs in facts(d):
        s += f" {key.capitalize()}: {' '.join(t for t, _ in segs)}."
    if d.get("langs"):
        s += " Languages: " + ", ".join(f"{k} {p:.0f}%" for k, p in d["langs"]) + "."
    return s


def render(d: dict, dl: dict, base: dict | None, wide: bool, theme: str) -> str:
    W, H = (760, 330) if wide else (480, 588)
    pad = 20
    b = Board(W, H, theme)
    t = b.t
    acc = t["acc"]

    b.text("skyefugate", pad, 32, "h", 15, fill="url(#hg)")
    right = "last 12 months"
    if base:
        right += f" \u00b7 \u0394 since {base['date'][5:]}"
    b.text(right, W - pad, 32, "s", 11, end=True)

    # tiles: 5 across on wide, 3 across on narrow
    cols = 6 if wide else 3
    span = (W - 2 * pad) / cols
    deco = []
    ts = tiles(d, dl)
    for i, (label, value, delta, note) in enumerate(ts):
        x, y = pad + (i % cols) * span, 66 + (i // cols) * 62
        c = acc[i % len(acc)]
        deco.append(
            f'<rect x="{x:g}" y="{y - 16}" width="18" height="3" rx="1.5" fill="{c}"/>'
        )
        b.text(label, x, y, "lb", 10, fill=c)
        vw = b.text(value, x, y + 26, "v", 22)
        fd = fmt_delta(delta)
        if fd:
            b.text(fd[0], x + vw + 8, y + 26, f"d {fd[1]}", 12)
        elif note:
            b.text(note, x + vw + 8, y + 26, "n", 10)
    rows = (len(ts) + cols - 1) // cols
    fy0 = 66 + rows * 62 + 4

    # fun facts
    fx, keyw = pad, 112
    fs = facts(d)
    for i, (key, segs) in enumerate(fs):
        y = fy0 + i * 19
        c = acc[(i + 2) % len(acc)]
        b.text(key, fx, y, "lb", 10, fill=c)
        x = fx + keyw
        for text, cls in segs:
            x += b.text(text, x, y, "fv" if cls == "fv" else f"fv {cls}", 11) + 8

    # weekly bars, beside the facts on wide, below them on narrow
    if wide:
        bx, bw, top = 400, W - pad - 400, fy0 + 4
    else:
        bx, bw, top = pad, W - 2 * pad, fy0 + len(fs) * 19 + 22
    base_y, ly = top + 52, top + 70
    weeks = d["weeks"][-53:]
    peak = max(weeks) or 1
    b.text("weekly", bx, top - 10, "s", 11)
    b.text(f"peak {peak}", bx + bw, top - 10, "s", 11, end=True)
    step = bw / len(weeks)
    barw = step * 0.68
    bars = []
    for i, v in enumerate(weeks):
        hgt = max((base_y - top) * v / peak, 2)
        now = i == len(weeks) - 1
        delay = f"{1.0 + i * 0.01:.2f}s" + (", 2.80s" if now else "")
        fill = t["now"] if now else "url(#bg)"
        bars.append(
            f'<rect class="{"b now" if now else "b"}" x="{bx + i * step:.1f}" y="{base_y - hgt:.1f}" width="{barw:.1f}" height="{hgt:.1f}" rx="1" fill="{fill}" style="animation-delay:{delay}"/>'
        )

    # language bar + legend
    segs, x = [], bx
    for i, (name, pct) in enumerate(d.get("langs", [])):
        w = bw * pct / 100
        c = LANG_COLORS.get(name, t["mu"])
        segs.append(
            f'<rect class="lg" x="{x:.1f}" y="{ly}" width="{w + 0.5:.1f}" height="6" fill="{c}" style="animation-delay:{1.8 + i * 0.08:.2f}s"/>'
        )
        x += w
    col = bw / 3
    dots = []
    for i, (name, pct) in enumerate(d.get("langs", [])):
        lx, lyy = bx + (i % 3) * col, ly + 20 + (i // 3) * 16
        dots.append(
            f'<circle cx="{lx + 4:.1f}" cy="{lyy - 4}" r="3.5" fill="{LANG_COLORS.get(name, t["mu"])}"/>'
        )
        b.text(f"{name} {pct:.0f}%", lx + 12, lyy, "s", 11)

    g = t["grad"]
    stops = "".join(
        f'<stop offset="{i / (len(g) - 1):g}" stop-color="{c}"/>'
        for i, c in enumerate(g)
    )
    desc = summary(d, dl, base)
    title = f"Skye Fugate, last 12 months, {d['today']}"
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d" aria-label="{escape(desc)}">',
            f'<title id="t">{escape(title)}</title>',
            f'<desc id="d">{escape(desc)}</desc>',
            "<defs>",
            f'<linearGradient id="hg" x1="0" y1="0" x2="1" y2="0">{stops}</linearGradient>',
            f'<linearGradient id="bg" gradientUnits="userSpaceOnUse" x1="{bx}" y1="0" x2="{bx + bw}" y2="0">{stops}</linearGradient>',
            f'<linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">{stops}</linearGradient>',
            f'<clipPath id="lc"><rect x="{bx}" y="{ly}" width="{bw}" height="6" rx="3"/></clipPath>',
            "</defs>",
            b.css(),
            f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="8" fill="{t["bg"]}" stroke="{t["line"]}"/>',
            f'<rect x="1" y="1" width="{W - 2}" height="3" rx="1.5" fill="url(#edge)"/>',
            *deco,
            f'<line x1="{bx}" x2="{bx + bw}" y1="{base_y + 0.5}" y2="{base_y + 0.5}" stroke="{t["line"]}"/>',
            *bars,
            f'<g clip-path="url(#lc)">{"".join(segs)}</g>',
            *dots,
            *b.body,
            "</svg>",
            "",
        ]
    )


def picture(version: str, alt: str) -> str:
    """README block. Narrow first so phones never get the wide board shrunk;
    ?v= busts GitHub's image cache when the numbers change."""

    def src(size, theme):
        return f"assets/board-{size}-{theme}.svg?v={version}"

    return "\n".join(
        [
            "<picture>",
            f'  <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="{src("narrow", "dark")}">',
            f'  <source media="(max-width: 600px)" srcset="{src("narrow", "light")}">',
            f'  <source media="(prefers-color-scheme: dark)" srcset="{src("wide", "dark")}">',
            f'  <img src="{src("wide", "light")}" alt="{escape(alt)}" width="760">',
            "</picture>",
        ]
    )

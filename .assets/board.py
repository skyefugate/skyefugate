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

DELTA_KEYS = ("total", "commits", "prs", "reviews", "issues", "followers", "stars")


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


def longest_break(days: list[int]) -> int:
    best = cur = 0
    for c in days:
        cur = 0 if c else cur + 1
        best = max(best, cur)
    return best


def comeback(weeks: list[int], quiet_min: int = 2) -> tuple[int, int] | None:
    """Biggest week that followed at least quiet_min empty weeks.
    -> (count, quiet weeks before it)."""
    best, quiet = None, 0
    for v in weeks:
        if v and quiet >= quiet_min and (best is None or v >= best[0]):
            best = (v, quiet)
        quiet = 0 if v else quiet + 1
    return best


def peak_month(dated: list[tuple[str, int]]) -> tuple[str, int] | None:
    """dated: (YYYY-MM-DD, count) -> ("Sep '26", total) for the busiest month."""
    by = Counter()
    for day, c in dated:
        by[day[:7]] += c
    if not by or not max(by.values()):
        return None
    ym, n = max(by.items(), key=lambda kv: (kv[1], kv[0]))
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    return f"{months[int(ym[5:]) - 1]} '{ym[2:4]}", n


def median(xs: list[float]) -> float | None:
    s = sorted(xs)
    if not s:
        return None
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2


def fmt_dur(minutes: float) -> str:
    if minutes < 60:
        return f"{minutes:.0f}m"
    if minutes < 48 * 60:
        return f"{minutes / 60:.0f}h"
    return f"{minutes / 1440:.0f}d"


def necromancer(
    commits: dict[str, list[str]], today: str, min_gap: int = 30
) -> tuple[str, int] | None:
    """commits: repo -> my commit dates (YYYY-MM-DD). The repo with the longest
    nap that I came back to within the last year. -> (repo, days asleep)."""
    from datetime import date

    t = date.fromisoformat(today)
    best = None
    for repo, ds in commits.items():
        s = sorted(date.fromisoformat(x) for x in set(ds))
        for a, b in zip(s, s[1:]):
            gap = (b - a).days
            if (t - b).days <= 365 and gap >= min_gap and (not best or gap > best[1]):
                best = (repo, gap)
    return best


def new_languages(repos: list[tuple[str, list[str]]], since: str) -> list[str]:
    """repos: (createdAt YYYY-MM-DD, languages). Languages first seen in a repo
    created on or after since, in the order they first appear."""
    old = {lang for created, langs in repos if created < since for lang in langs}
    out = []
    for created, langs in sorted(repos):
        for lang in langs:
            if created >= since and lang not in old and lang not in out:
                out.append(lang)
    return out


def trunc(s: str, n: int) -> str:
    return s if len(s) <= n else s[: max(n - 1, 1)] + "\u2026"


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
        mid: bool = False,
    ) -> float:
        """One decoding line. Returns the line's estimated width in px."""
        start = 0.05 + min(self.lines, 30) * 0.025
        self.lines += 1
        anchor = (
            ' text-anchor="end"' if end else (' text-anchor="middle"' if mid else "")
        )
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
.sk {{ font-size: 9px; font-weight: 600; }}
.ll {{ font-size: 8px; fill: {t["mu"]}; }}
.s {{ font-size: 11px; fill: {t["mu"]}; }}
.fv {{ font-size: 10px; fill: {t["fg"]}; }}
.lb {{ font-size: 9px; font-weight: 600; letter-spacing: 1px; }}
.v {{ font-size: 18px; font-weight: 600; fill: {t["fg"]}; }}
.d {{ font-size: 10px; font-weight: 600; }}
.n {{ font-size: 9px; fill: {t["mu"]}; }}
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

SHORT_LANG = {"JavaScript": "JS", "TypeScript": "TS", "PowerShell": "PS"}


def tiles(d: dict, dl: dict) -> list[tuple[str, str, int | None, str]]:
    """(label, value, delta, note). Labels are short so 6 fit across."""
    return [
        ("CONTRIBS", str(d["total"]), dl.get("total"), ""),
        ("COMMITS", str(d["commits"]), dl.get("commits"), ""),
        ("PRS", str(d["prs"]), dl.get("prs"), ""),
        ("REVIEWS", str(d["reviews"]), dl.get("reviews"), ""),
        ("ISSUES", str(d["issues"]), dl.get("issues"), ""),
        ("FOLLOWERS", str(d["followers"]), dl.get("followers"), ""),
        ("STREAK", f"{d['streak']}d", None, f"max {d['longest']}"),
        ("ACTIVE", f"{d['active']}/365", None, ""),
        ("STARS", str(d["stars"]), dl.get("stars"), ""),
        ("PUBLIC", str(d["repos"]), None, "repos"),
        ("LANGS", str(d["lang_count"]), None, ""),
        ("MERGED", str(d["merged"][0]), None, "PRs"),
    ]


def superlatives(d: dict, room: int) -> list[tuple[str, list[tuple[str, str]], str]]:
    """(name, [(text, kind)], meaning). kind: v plain, up/dn coloured, mu missing.
    room = max characters for the value. meaning goes into the alt text."""
    out = []

    def add(name, value, meaning):
        segs = value if isinstance(value, list) else [(value, "v")]
        if value is None:
            segs = [("not yet", "mu")]
        out.append((name, segs, meaning))

    def pct(pair):
        n, of = pair
        return f"{n / of * 100:.0f}% \u00b7 {n}/{of}" if of else None

    def named(name, suffix):
        return trunc(name, room - len(suffix)) + suffix

    add("Ship It", pct(d["merged"]), "share of my public PRs that merged")
    mm = d.get("merge_mins")
    add(
        "Merge Speed",
        fmt_dur(mm) if mm is not None else None,
        "median time from PR open to merge",
    )
    rk = d.get("review_karma")
    add("Review Karma", f"{rk} merged" if rk else None, "PRs I reviewed that merged")
    add(
        "Actually Done", pct(d["issues_closed"]), "share of my public issues now closed"
    )
    ft = d.get("field_trips")
    add(
        "Field Trips",
        f"{ft[0]} in {ft[1]} repo{'s' if ft[1] != 1 else ''}" if ft and ft[0] else None,
        "contributions to repos I don't own",
    )
    tp = d.get("team_player")
    add(
        "Team Player",
        named(tp[0], f" \u00b7 {tp[1]}") if tp else None,
        "repo I touched with the most contributors",
    )
    add(
        "Tab Hoarder",
        f"{d['repos_touched']} repos",
        "distinct repos committed to this year",
    )
    sq = d.get("side_quest") or []
    add(
        "Side Quest",
        f"+{len(sq)} \u00b7 {sq[0]}" if sq else None,
        "languages new this year",
    )
    best = d.get("best")
    add(
        "Absolute Menace",
        f"{best[0]} on {best[1][5:]}" if best else None,
        "busiest single day",
    )
    pm = d.get("peak_month")
    add("Peak Era", f"{pm[0]} \u00b7 {pm[1]}" if pm else None, "busiest month")
    wk = d.get("weekdays")
    add(
        "Weekend Mode",
        f"{wk[2]:.0f}%" if wk else None,
        "share of contributions on weekends",
    )
    ct = d.get("chrono")
    add(
        ct[1].title() if ct else "Night Owl",
        f"{fmt_hour(ct[0])} \u00b7 {ct[2]:.0f}%" if ct else None,
        "peak commit hour, Central time",
    )
    lb = d.get("longest_break")
    add(
        "Touch Grass",
        f"{lb}d off" if lb else None,
        "longest stretch with no contributions",
    )
    cb = d.get("comeback")
    add(
        "Redemption Arc",
        f"{cb[0]} after {cb[1]}w off" if cb else None,
        "biggest week after a quiet spell",
    )
    nc = d.get("necro")
    add(
        "Necromancer",
        named(nc[0], f" \u00b7 {nc[1]}d") if nc else None,
        "repo revived after the longest nap, in days",
    )
    ln = d.get("lines")
    add(
        "Refactor Energy",
        f"{ln[1] / ln[0] * 100:.0f}% churn" if ln and ln[0] else None,
        "lines removed per 100 added",
    )
    add(
        "Lines",
        [(f"+{fmt_k(ln[0])}", "up"), (f"\u2212{fmt_k(ln[1])}", "dn")] if ln else None,
        "lines added and removed",
    )
    bz = d.get("busiest")
    add(
        "Main Character",
        named(bz[0], "") if bz else None,
        "busiest public repo, last 90 days",
    )
    add("Fav Day", wk[0] if wk else None, "weekday with the most contributions")
    ac = d.get("avg_commit")
    add(
        "Chonky Commits",
        f"avg {ac:.0f} lines" if ac else None,
        "average lines changed per commit",
    )
    add("Day One", str(d["since"]) if d.get("since") else None, "year I joined")
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
        f"{d['stars']} stars{chg('stars')}",
    ]
    s = (
        f"Last 12 months: {', '.join(parts)}. "
        f"Current streak {d['streak']} day{'s' if d['streak'] != 1 else ''}, "
        f"longest {d['longest']}, active {d['active']} of 365 days, "
        f"{d['repos']} public repos, {d['lang_count']} languages."
    )
    for name, segs, meaning in superlatives(d, 40):
        s += f" {name} ({meaning}): {' '.join(t for t, _ in segs)}."
    if d.get("langs"):
        s += " Languages: " + ", ".join(f"{k} {p:.0f}%" for k, p in d["langs"]) + "."
    return s


def render(d: dict, dl: dict, base: dict | None, wide: bool, theme: str) -> str:
    """A compact strip meant to sit under the banner, centred."""
    W, H = (760, 226) if wide else (480, 404)
    pad = 20
    b = Board(W, H, theme)
    t = b.t
    acc = t["acc"]

    # stat grid: 6 x 2 on wide (left of the bars), 4 x 3 on narrow
    cols = 6 if wide else 4
    gw = 504 if wide else W - 2 * pad
    span = gw / cols
    ts = tiles(d, dl)
    for i, (label, value, delta, note) in enumerate(ts):
        x, y = pad + (i % cols) * span, 26 + (i // cols) * 40
        b.text(label, x, y, "lb", 9, fill=acc[i % len(acc)])
        vw = b.text(value, x, y + 20, "v", 18)
        fd = fmt_delta(delta)
        if fd:
            b.text(fd[0], x + vw + 5, y + 20, f"d {fd[1]}", 10)
        elif note:
            b.text(note, x + vw + 5, y + 20, "n", 9)
    rows = (len(ts) + cols - 1) // cols
    grid_bottom = 26 + rows * 40 - 14

    # weekly bars: right of the grid on wide, under it on narrow
    if wide:
        bx, bw, top, base_y = pad + gw + 20, W - pad - (pad + gw + 20), 16, 70
    else:
        bx, bw, top, base_y = pad, W - 2 * pad, grid_bottom + 12, grid_bottom + 52
    weeks = d["weeks"][-53:]
    peak = max(weeks) or 1
    step = bw / len(weeks)
    barw = step * 0.7
    bars = []
    for i, v in enumerate(weeks):
        hgt = max((base_y - top) * v / peak, 1.5)
        now = i == len(weeks) - 1
        delay = f"{0.9 + i * 0.01:.2f}s" + (", 2.60s" if now else "")
        fill = t["now"] if now else "url(#bg)"
        bars.append(
            f'<rect class="{"b now" if now else "b"}" x="{bx + i * step:.1f}" y="{base_y - hgt:.1f}" width="{barw:.1f}" height="{hgt:.1f}" rx="1" fill="{fill}" style="animation-delay:{delay}"/>'
        )
    b.text("weekly \u00b7 12 mo", bx, base_y + 14, "n", 9)
    b.text(f"peak {peak}", bx + bw, base_y + 14, "n", 9, end=True)

    # superlatives: name left, value right-aligned, 3 columns wide / 2 narrow
    scols = 3 if wide else 2
    colw = (W - 2 * pad) / scols
    room = int((colw - 14 - 15 * 9 * CHAR - 10) / (10 * CHAR))
    sy0 = (base_y + 40) if not wide else 112
    rule = sy0 - 14
    for i, (name, segs, _) in enumerate(superlatives(d, room)):
        x, y = pad + (i % scols) * colw, sy0 + (i // scols) * 15
        b.text(name, x, y, "sk", 9, fill=acc[i % len(acc)])
        right = x + colw - 14
        for text, kind in reversed(segs):
            cls = "fv" if kind == "v" else ("n" if kind == "mu" else f"fv {kind}")
            right -= b.text(text, right, y, cls, 10, end=True) + 6

    # language labels in small grey type, then the colour strip on the bottom edge
    segs, labels, x = [], [], 1.0
    for i, (name, pct) in enumerate(d.get("langs", [])):
        w = (W - 2) * pct / 100
        c = LANG_COLORS.get(name, t["mu"])
        segs.append(
            f'<rect class="lg" x="{x:.1f}" y="{H - 4}" width="{w + 0.5:.1f}" height="3" fill="{c}" style="animation-delay:{1.7 + i * 0.08:.2f}s"/>'
        )
        labels.append(
            ([f"{name} {pct:.0f}%", f"{SHORT_LANG.get(name, name)} {pct:.0f}%"], x, w)
        )
        x += w
    edge = 0.0
    for options, sx, w in labels:
        for label in options:  # full name first, then the short one
            half = len(label) * 8 * CHAR / 2 + 3
            if 2 * half > w + 8:
                continue
            cx = min(max(sx + w / 2, 6 + half), W - 6 - half)
            if cx - half >= edge:
                b.text(label, cx, H - 10, "ll", 8, mid=True)
                edge = cx + half
                break  # if none fit, the alt text still lists it

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
            f'<linearGradient id="bg" gradientUnits="userSpaceOnUse" x1="{bx}" y1="0" x2="{bx + bw}" y2="0">{stops}</linearGradient>',
            f'<linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">{stops}</linearGradient>',
            f'<clipPath id="card"><rect width="{W}" height="{H}" rx="8"/></clipPath>',
            "</defs>",
            b.css(),
            '<g clip-path="url(#card)">',
            f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>',
            f'<rect width="{W}" height="3" fill="url(#edge)"/>',
            *segs,
            "</g>",
            f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="8" fill="none" stroke="{t["line"]}"/>',
            f'<line x1="{bx}" x2="{bx + bw}" y1="{base_y + 0.5}" y2="{base_y + 0.5}" stroke="{t["line"]}"/>',
            f'<line x1="{pad}" x2="{W - pad}" y1="{rule}" y2="{rule}" stroke="{t["line"]}" stroke-dasharray="2 3"/>',
            *bars,
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

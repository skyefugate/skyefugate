"""The two hand-written cards, drawn as network-engineer terminal output.

  focus  ->  `show interfaces`: each area of work is a port, with a status LED
  talks  ->  `traceroute`: each talk is a hop, and the next one times out (* * *)

Same rules as the stats board: monospace, text decodes into place, the motion
settles, the finished picture is the default state, and dark/light are
separate files so the README <picture> follows GitHub's theme, not the OS.
"""

from __future__ import annotations

from html import escape

from board import EASE, Board

# (port, status, area, detail, stack)
FOCUS = [
    (
        "ai0",
        "up",
        "AI for networks",
        "live topology, blast-radius review",
        "agents · prompts · IaC docs",
    ),
    (
        "nx0",
        "up",
        "Network experience",
        "telemetry agents and scoring",
        "python · influxdb · grafana",
    ),
    (
        "iac0",
        "up",
        "Infra as code",
        "AWS, NetBox and Grafana as code",
        "cloudformation · ansible · git sync",
    ),
    (
        "off0",
        "idle",
        "Off the clock",
        "plane tracking, Folding@home",
        "shooting clays · @SecKC",
    ),
]

# oldest first: (event, date, title, tags)
TALKS = [
    (
        "SecDSM",
        "Dec 2025",
        "AI network troubleshooting",
        "C2 detection · VPC flow logs",
    ),
    (
        "SecKC",
        "Sep 2026",
        "AI for network architecture",
        "topology · blast radius · IaC docs",
    ),
]

EXTRA_CSS = f"""<style>
.pr {{ font-size: 12px; font-weight: 600; }}
.hd {{ font-size: 9px; font-weight: 600; letter-spacing: 1px; }}
.c11 {{ font-size: 11px; }}
.c11b {{ font-size: 11px; font-weight: 600; }}
.c12b {{ font-size: 12px; font-weight: 700; }}
.c10 {{ font-size: 10px; }}
.led {{ transform-box: fill-box; transform-origin: center; animation: led .5s {EASE} backwards; }}
.hop {{ transform-box: fill-box; transform-origin: center; animation: pop .5s {EASE} backwards; }}
.path {{ stroke-dasharray: 4 5; animation: draw 1.1s {EASE} .3s backwards; }}
@keyframes led {{ 0% {{ opacity: 0; }} 40% {{ opacity: 1; transform: scale(1.8); }} }}
@keyframes pop {{ from {{ transform: scale(0); }} }}
@keyframes draw {{ from {{ stroke-dashoffset: 700; opacity: 0; }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>"""


def _frame(b: Board, w: int, h: int, title: str, desc: str, body: list[str]) -> str:
    t = b.t
    g = t["grad"]
    stops = "".join(
        f'<stop offset="{i / (len(g) - 1):g}" stop-color="{c}"/>'
        for i, c in enumerate(g)
    )
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d" aria-label="{escape(desc)}">',
            f'<title id="t">{escape(title)}</title>',
            f'<desc id="d">{escape(desc)}</desc>',
            f'<defs><linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">{stops}</linearGradient>',
            f'<linearGradient id="pg" gradientUnits="userSpaceOnUse" x1="40" y1="0" x2="{w - 40}" y2="0">{stops}</linearGradient>',
            f'<clipPath id="card"><rect width="{w}" height="{h}" rx="8"/></clipPath></defs>',
            b.css(),
            EXTRA_CSS,
            f'<g clip-path="url(#card)"><rect width="{w}" height="{h}" fill="{t["bg"]}"/>',
            f'<rect width="{w}" height="3" fill="url(#edge)"/></g>',
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="8" fill="none" stroke="{t["line"]}"/>',
            *body,
            *b.body,
            "</svg>",
            "",
        ]
    )


def focus(theme: str) -> str:
    W, pad = 760, 20
    rows = len(FOCUS)
    H = 74 + rows * 22
    b = Board(W, H, theme)
    t, acc = b.t, b.t["acc"]
    body = []
    b.text("skye@fugate:~$ show interfaces", pad, 28, "pr", 12, fill="url(#edge)")
    cols = [pad, pad + 54, pad + 106, pad + 240, pad + 494]
    for x, h in zip(cols, ("PORT", "STATE", "AREA", "DETAIL", "STACK")):
        b.text(h, x, 52, "hd", 9, fill=t["mu"])
    body.append(
        f'<line x1="{pad}" x2="{W - pad}" y1="58.5" y2="58.5" stroke="{t["line"]}"/>'
    )
    for i, (port, status, area, detail, stack) in enumerate(FOCUS):
        y = 76 + i * 22
        c = acc[i % len(acc)]
        b.text(port, cols[0], y, "c11b", 11, fill=c)
        led = t["up"] if status == "up" else t["acc"][5]
        body.append(
            f'<circle class="led" cx="{cols[1] + 4}" cy="{y - 4}" r="3.5" fill="{led}" style="animation-delay:{0.6 + i * 0.12:.2f}s"/>'
        )
        b.text(status, cols[1] + 12, y, "c11", 11, fill=t["mu"])
        b.text(area, cols[2], y, "c11b", 11, fill=t["fg"])
        b.text(detail, cols[3], y, "c11", 11, fill=t["fg"])
        b.text(stack, cols[4], y, "c10", 10, fill=t["mu"])
    desc = "What I work on. " + " ".join(
        f"{area} ({status}): {detail}; {stack}."
        for _, status, area, detail, stack in FOCUS
    )
    return _frame(b, W, H, "What I work on", desc, body)


def talks(theme: str) -> str:
    W, H, pad = 760, 156, 20
    b = Board(W, H, theme)
    t, acc = b.t, b.t["acc"]
    body = []
    b.text("skye@fugate:~$ traceroute talks", pad, 28, "pr", 12, fill="url(#edge)")
    n = len(TALKS) + 1  # plus the hop that has not answered yet
    xs = [110 + i * (W - 220) / (n - 1) for i in range(n)]
    py = 66
    body.append(
        f'<path class="path" d="M{xs[0]} {py} L{xs[-1]} {py}" stroke="url(#pg)" stroke-width="2" fill="none"/>'
    )
    for i, x in enumerate(xs):
        c = acc[i % len(acc)]
        delay = f"animation-delay:{0.5 + i * 0.25:.2f}s"
        b.text(f"hop {i + 1}", x, py - 14, "hd", 9, fill=t["mu"], mid=True)
        if i < len(TALKS):
            event, date, title, tags = TALKS[i]
            body.append(
                f'<circle class="hop" cx="{x}" cy="{py}" r="6" fill="{c}" style="{delay}"/>'
            )
            body.append(f'<circle cx="{x}" cy="{py}" r="2.5" fill="{t["bg"]}"/>')
            b.text(f"{event} \u00b7 {date}", x, py + 28, "c12b", 12, fill=c, mid=True)
            b.text(title, x, py + 46, "c11", 11, fill=t["fg"], mid=True)
            b.text(tags, x, py + 62, "c10", 10, fill=t["mu"], mid=True)
        else:
            body.append(
                f'<circle class="hop" cx="{x}" cy="{py}" r="6" fill="none" stroke="{t["mu"]}" stroke-dasharray="2 2" style="{delay}"/>'
            )
            b.text("*  *  *", x, py + 28, "c12b", 12, fill=t["mu"], mid=True)
            b.text(
                "next hop not answering", x, py + 46, "c11", 11, fill=t["mu"], mid=True
            )
            b.text("want a talk? ask me", x, py + 62, "c10", 10, fill=t["mu"], mid=True)
    desc = "Talks. " + " ".join(f"{e}, {d}: {ti} ({tg})." for e, d, ti, tg in TALKS)
    return _frame(b, W, H, "Talks", desc, body)


def picture(name: str, alt: str, version: str) -> str:
    return "\n".join(
        [
            "<picture>",
            f'  <source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg?v={version}">',
            f'  <img src="assets/{name}-light.svg?v={version}" alt="{escape(alt)}" width="760">',
            "</picture>",
        ]
    )

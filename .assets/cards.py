"""One terminal window: what I work on, then my talks, as a real session.

  $ show interfaces    each area of work is a port with a status LED
  $ traceroute talks   each talk is a hop, and the next hop times out (* * *)
  $ _                  the cursor blinks a few times, then rests

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

# oldest first: (host, title, tags)
TALKS = [
    ("secdsm.dec-2025", "AI network troubleshooting", "C2 detection · VPC flow logs"),
    (
        "seckc.sep-2026",
        "AI for network architecture",
        "topology · blast radius · IaC docs",
    ),
]

DOTS = ("#ff5f57", "#febc2e", "#28c840")  # window controls

EXTRA_CSS = f"""<style>
.c11 {{ font-size: 11px; }}
.c11b {{ font-size: 11px; font-weight: 600; }}
.c10 {{ font-size: 10px; }}
.hd {{ font-size: 9px; font-weight: 600; letter-spacing: 1px; }}
.led {{ transform-box: fill-box; transform-origin: center; animation: led .5s {EASE} backwards; }}
.cur {{ animation: blink 1s steps(1) 2.6s 4; }}
@keyframes led {{ 0% {{ opacity: 0; }} 40% {{ opacity: 1; transform: scale(1.8); }} }}
@keyframes blink {{ 50% {{ opacity: 0; }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>"""


def terminal(theme: str) -> str:
    W, pad, row = 760, 22, 20
    b = Board(W, 0, theme)
    t, acc = b.t, b.t["acc"]
    body = []

    def prompt(y: float, cmd: str) -> float:
        x = pad + b.text("skye@fugate:~$", pad, y, "c11b", 11, fill=acc[0]) + 7
        return x + b.text(cmd, x, y, "c11b", 11, fill=t["fg"]) if cmd else x

    # show interfaces
    y = 58
    prompt(y, "show interfaces")
    cols = [pad, pad + 54, pad + 106, pad + 240, pad + 494]
    y += 24
    for x, h in zip(cols, ("PORT", "STATE", "AREA", "DETAIL", "STACK")):
        b.text(h, x, y, "hd", 9, fill=t["mu"])
    body.append(
        f'<line x1="{pad}" x2="{W - pad}" y1="{y + 6.5}" y2="{y + 6.5}" stroke="{t["line"]}"/>'
    )
    y += 8
    for i, (port, status, area, detail, stack) in enumerate(FOCUS):
        y += row
        b.text(port, cols[0], y, "c11b", 11, fill=acc[(i + 1) % len(acc)])
        led = t["up"] if status == "up" else acc[5]
        body.append(
            f'<circle class="led" cx="{cols[1] + 4}" cy="{y - 4}" r="3.5" fill="{led}" style="animation-delay:{0.7 + i * 0.12:.2f}s"/>'
        )
        b.text(status, cols[1] + 12, y, "c11", 11, fill=t["mu"])
        b.text(area, cols[2], y, "c11b", 11, fill=t["fg"])
        b.text(detail, cols[3], y, "c11", 11, fill=t["fg"])
        b.text(stack, cols[4], y, "c10", 10, fill=t["mu"])

    # traceroute talks: plain traceroute output, the next hop times out
    y += 32
    prompt(y, "traceroute talks")
    y += row
    b.text(
        f"traceroute to next-talk, {len(TALKS) + 1} hops max",
        pad,
        y,
        "c11",
        11,
        fill=t["mu"],
    )
    hcols = [pad + 8, pad + 34, pad + 200, pad + 494]
    for i, (host, title, tags) in enumerate(TALKS):
        y += row
        b.text(f"{i + 1}", hcols[0], y, "c11", 11, fill=t["mu"])
        b.text(host, hcols[1], y, "c11b", 11, fill=acc[(i + 2) % len(acc)])
        b.text(title, hcols[2], y, "c11", 11, fill=t["fg"])
        b.text(tags, hcols[3], y, "c10", 10, fill=t["mu"])
    y += row
    b.text(f"{len(TALKS) + 1}", hcols[0], y, "c11", 11, fill=t["mu"])
    b.text("*  *  *", hcols[1], y, "c11b", 11, fill=t["mu"])
    b.text("request timed out", hcols[2], y, "c11", 11, fill=t["mu"])
    b.text("want a talk? ask me", hcols[3], y, "c10", 10, fill=acc[4])

    # resting prompt with a cursor that blinks a few times, then stays
    y += 30
    cx = prompt(y, "")
    body.append(
        f'<rect class="cur" x="{cx:.1f}" y="{y - 10}" width="7" height="13" fill="{t["fg"]}"/>'
    )
    H = int(y + 18)

    # window chrome
    g = t["grad"]
    stops = "".join(
        f'<stop offset="{i / (len(g) - 1):g}" stop-color="{c}"/>'
        for i, c in enumerate(g)
    )
    chrome = [
        f'<defs><linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">{stops}</linearGradient>',
        f'<clipPath id="card"><rect width="{W}" height="{H}" rx="8"/></clipPath></defs>',
        f'<g clip-path="url(#card)"><rect width="{W}" height="{H}" fill="{t["bg"]}"/>',
        f'<rect width="{W}" height="30" fill="{t["line"]}" opacity=".45"/>',
        f'<rect y="30" width="{W}" height="1.5" fill="url(#edge)"/></g>',
        *(
            f'<circle cx="{20 + i * 18}" cy="15" r="5.5" fill="{c}"/>'
            for i, c in enumerate(DOTS)
        ),
        f'<text x="{W / 2}" y="19" text-anchor="middle" class="c10" fill="{t["mu"]}">skye@fugate: ~ \u2014 zsh</text>',
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="8" fill="none" stroke="{t["line"]}"/>',
    ]
    desc = (
        "What I work on: "
        + " ".join(f"{a} ({s}): {d}; {k}." for _, s, a, d, k in FOCUS)
        + " Talks: "
        + " ".join(f"{h}: {ti} ({tg})." for h, ti, tg in TALKS)
        + " Next talk: not scheduled yet, ask me."
    )
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d" aria-label="{escape(desc)}">',
            '<title id="t">What I work on, and my talks</title>',
            f'<desc id="d">{escape(desc)}</desc>',
            b.css(),
            EXTRA_CSS,
            *chrome,
            *body,
            *b.body,
            "</svg>",
            "",
        ]
    )


def picture(name: str, alt: str, version: str) -> str:
    return "\n".join(
        [
            "<picture>",
            f'  <source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg?v={version}">',
            f'  <img src="assets/{name}-light.svg?v={version}" alt="{escape(alt)}" width="760">',
            "</picture>",
        ]
    )

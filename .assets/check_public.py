#!/usr/bin/env python3
"""Opsec gate: fail if anything private would be published in this public repo.

Checks every tracked text file (or the paths given) for:
  - private / internal IP addresses (RFC 1918, CGNAT, link-local)
  - names of my private GitHub repos (fetched live with gh, never stored here)
  - words from a local, untracked deny list (~/.config/git/public-denylist)

The deny list lives outside the repo so the list of things to hide is never
itself published. One entry per line, case-insensitive:
  word        block this word
  !word       allow this word even if it is a private repo name
  # comment

Matches are reported by file and line only, never by the matched text,
because CI logs on a public repo are public too.

Run:  python3 .assets/check_public.py [paths...]
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

USER = "skyefugate"
ROOT = Path(__file__).resolve().parent.parent
SELF = Path(__file__).resolve()
DENYLIST = Path.home() / ".config" / "git" / "public-denylist"

PRIVATE_IP = re.compile(
    r"\b(?:10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])|192\.168|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])|169\.254)"
    r"\.\d{1,3}\.\d{1,3}\b"
)


def private_repo_names() -> list[str]:
    try:
        out = subprocess.run(
            [
                "gh",
                "repo",
                "list",
                USER,
                "--visibility",
                "private",
                "--limit",
                "500",
                "--json",
                "name",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        print(
            "check_public: gh unavailable, skipping private repo names", file=sys.stderr
        )
        return []
    return [r["name"] for r in json.loads(out)]


def local_list() -> tuple[set[str], set[str]]:
    deny, allow = set(), set()
    if DENYLIST.exists():
        for line in DENYLIST.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            (allow if line.startswith("!") else deny).add(line.lstrip("!").lower())
    return deny, allow


def files(args: list[str]) -> list[Path]:
    if args:
        paths = [Path(a).resolve() for a in args]
    else:
        out = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout
        paths = [ROOT / p for p in out.splitlines()]
    return [p for p in paths if p.is_file() and p != SELF and p.suffix != ".png"]


def main() -> int:
    deny, allow = local_list()
    words = ({w.lower() for w in private_repo_names() if len(w) >= 4} | deny) - allow
    word_re = (
        re.compile(
            r"(?<![\w-])("
            + "|".join(map(re.escape, sorted(words, key=len, reverse=True)))
            + r")(?![\w-])",
            re.I,
        )
        if words
        else None
    )

    hits = []
    for path in files(sys.argv[1:]):
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if PRIVATE_IP.search(line):
                hits.append(f"{path.relative_to(ROOT)}:{n}: private IP")
            if word_re and word_re.search(line):
                hits.append(f"{path.relative_to(ROOT)}:{n}: private word")
    if hits:
        print(
            "check_public: private data found, not publishing:\n  " + "\n  ".join(hits),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

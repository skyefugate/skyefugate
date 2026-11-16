"""Run:  python3 -m unittest discover -s .assets"""

import unittest
import xml.etree.ElementTree as ET

import board

NS = "{http://www.w3.org/2000/svg}"

DATA = {
    "today": "2026-11-16",
    "total": 55,
    "commits": 40,
    "prs": 6,
    "followers": 6,
    "reviews": 0,
    "issues": 2,
    "repos_touched": 7,
    "repos": 5,
    "lang_count": 9,
    "streak": 3,
    "longest": 4,
    "active": 14,
    "best": (26, "2026-09-12"),
    "weekdays": ("Sat", 31.0, 38.0),
    "chrono": (21, "evening coder", 46.0),
    "lines": (8846, 802),
    "since": 2020,
    "years": 6,
    "weeks": [0] * 50 + [4, 9, 2],
    "busiest": ("2026-09-SecKC-AI-Talk", 17),
    "langs": [("Python", 48.0), ("HTML", 16.0), ("Shell", 11.0)],
}
BASE_VALUES = dict(total=54, commits=41, prs=6, reviews=0, issues=2, followers=6)


class Numbers(unittest.TestCase):
    def test_streak_ignores_quiet_today(self):
        self.assertEqual(board.streak([0, 1, 1, 1, 0]), 3)
        self.assertEqual(board.streak([1, 0, 2, 5]), 2)
        self.assertEqual(board.streak([1, 0, 0]), 0)
        self.assertEqual(board.streak([]), 0)

    def test_longest_streak(self):
        self.assertEqual(board.longest_streak([1, 1, 0, 1, 1, 1, 0, 1]), 3)
        self.assertEqual(board.longest_streak([0, 0]), 0)

    def test_best_day(self):
        self.assertEqual(board.best_day([("a", 1), ("b", 5), ("c", 5)]), (5, "b"))
        self.assertIsNone(board.best_day([("a", 0)]))

    def test_weekday_split(self):
        # Sun 2, Mon 1, Sat 1 -> Sun favourite at 50%, weekend 75%
        self.assertEqual(
            board.weekday_split([(0, 2), (1, 1), (6, 1)]), ("Sun", 50.0, 75.0)
        )
        self.assertIsNone(board.weekday_split([(3, 0)]))

    def test_chronotype(self):
        self.assertEqual(board.chronotype([23, 23, 1, 10]), (23, "night owl", 75.0))
        self.assertEqual(board.chronotype([6])[1], "early bird")
        self.assertIsNone(board.chronotype([]))
        self.assertEqual(board.fmt_hour(0), "12 am")
        self.assertEqual(board.fmt_hour(21), "9 pm")
        self.assertEqual(board.fmt_k(8846), "8.8k")

    def test_active_days_window(self):
        self.assertEqual(board.active_days([1] * 10 + [0, 2], window=3), 2)

    def test_same_day_rerun_keeps_baseline(self):
        s1 = board.next_state(None, "2026-11-15", {"total": 50})
        s2 = board.next_state(s1, "2026-11-16", {"total": 54})
        s3 = board.next_state(s2, "2026-11-16", {"total": 55})
        self.assertEqual(board.baseline(s3, "2026-11-16")["values"], {"total": 50})
        self.assertEqual(board.baseline(s3, "2026-11-17")["values"], {"total": 55})

    def test_deltas_and_colours(self):
        base = {"date": "x", "values": {"total": 50, "commits": 41, "prs": 6}}
        d = board.deltas(dict(total=55, commits=40, prs=6, followers=6), base)
        self.assertEqual(
            d,
            {
                "total": 5,
                "commits": -1,
                "prs": 0,
                "reviews": None,
                "issues": None,
                "followers": None,
            },
        )
        self.assertEqual(board.fmt_delta(5), ("+5", "up"))
        self.assertEqual(board.fmt_delta(-1)[1], "dn")
        self.assertEqual(board.fmt_delta(0)[1], "mu")
        self.assertIsNone(board.fmt_delta(None))
        self.assertTrue(all(v is None for v in board.deltas({}, None).values()))


class Decode(unittest.TestCase):
    def test_frames_resolve_left_to_right(self):
        s = "358/365 active"
        fs = board.frames(s)
        self.assertEqual(len(fs), board.FRAMES)
        for k, f in enumerate(fs):
            self.assertEqual(len(f), len(s))
            keep = len(s) * k // board.FRAMES
            self.assertEqual(f[:keep], s[:keep])
            self.assertEqual(f[7], " ")
            self.assertTrue(all(c in board.GLYPHS for c in f[keep:] if c != " "))

    def test_frames_are_deterministic(self):
        self.assertEqual(board.frames("abc def"), board.frames("abc def"))


class Render(unittest.TestCase):
    def setUp(self):
        base = {
            "date": "2026-11-15",
            "values": BASE_VALUES,
        }
        dl = board.deltas({k: DATA[k] for k in board.DELTA_KEYS}, base)
        self.svgs = {
            (w, t): board.render(DATA, dl, base, w, t)
            for w in (True, False)
            for t in ("dark", "light")
        }

    def test_valid_and_sized(self):
        for (wide, _), svg in self.svgs.items():
            root = ET.fromstring(svg)
            self.assertEqual(root.get("width"), "760" if wide else "480")

    def test_finished_board_is_the_default_state(self):
        """With animation off, every real line shows and every scramble hides."""
        root = ET.fromstring(self.svgs[(True, "dark")])
        texts = list(root.iter(NS + "text"))
        real = [t for t in texts if t.get("class", "").startswith("r ")]
        junk = [t for t in texts if t.get("class", "").startswith("f ")]
        self.assertTrue(real)
        self.assertEqual(len(junk), len(real) * board.FRAMES)
        self.assertTrue(all(t.get("opacity") is None for t in real))
        self.assertTrue(all(t.get("opacity") == "0" for t in junk))
        shown = {t.text for t in real}
        for want in (
            "skyefugate",
            "55",
            "+1",
            "\u22121",
            "3 d",
            "best 4 d",
            "14/365",
            "09-12",
            "9 pm \u00b7 evening coder (46%)",
            "Sat \u00b7 31% of the year",
            "+8.8k",
            "\u2212802",
            "2020 \u00b7 6 yrs ago",
            "Python 48%",
        ):
            self.assertIn(want, shown)
        self.assertFalse(any("github" in s.lower() for s in shown))
        self.assertIn("prefers-reduced-motion", self.svgs[(True, "dark")])

    def test_only_this_week_breathes(self):
        svg = self.svgs[(False, "light")]
        self.assertEqual(svg.count('class="b now"'), 1)
        self.assertEqual(svg.count("infinite"), 1)

    def test_numbers_are_readable_as_text(self):
        root = ET.fromstring(self.svgs[(True, "light")])
        desc = root.find(NS + "desc").text
        for want in (
            "55 contributions (+1 since 2026-11-15)",
            "streak 3 days",
            "longest 4",
            "14 of 365",
            "evening coder",
            "2026-09-SecKC-AI-Talk",
        ):
            self.assertIn(want, desc)
        self.assertEqual(root.get("aria-label"), desc)

    def test_picture_serves_narrow_to_phones(self):
        p = board.picture("20261116", "alt")
        self.assertLess(p.index("narrow-dark"), p.index("wide-dark"))
        self.assertEqual(p.count("?v=20261116"), 4)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Difference-in-differences readout for a before/after test with control pages.

For measures that are "k out of n": AI answers that named the site out of
answers collected, pages indexed out of pages submitted, prompts where a page
was cited out of prompts run. Not for raw counts with no denominator (clicks,
crawl hits); those need a different method.

Each proportion gets a Wilson score interval. The change in each group and the
difference-in-differences get intervals by combining the Wilson limits with the
MOVER method (Newcombe's approach for a difference of proportions, extended to
four terms). Groups are treated as independent samples. That is an
approximation: repeated runs of the same prompts are not fully independent.

Usage:
  python3 readout.py --test-before 3/40 --test-after 11/40 \
                     --control-before 4/40 --control-after 5/40 \
                     [--min-effect 0.10] [--confidence 0.95] [--lower-is-better]

Standard library only. Python 3.8+.
"""

import argparse
import math
import sys
from statistics import NormalDist


def parse_kn(text):
    try:
        k, n = text.split("/")
        k, n = int(k), int(n)
    except (ValueError, AttributeError):
        raise argparse.ArgumentTypeError(f"expected k/n, for example 7/40, got {text!r}")
    if n <= 0:
        raise argparse.ArgumentTypeError(f"n must be positive in {text!r}")
    if k < 0 or k > n:
        raise argparse.ArgumentTypeError(f"k must be between 0 and n in {text!r}")
    return k, n


def wilson(k, n, z):
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    lo = 0.0 if k == 0 else max(0.0, center - half)
    hi = 1.0 if k == n else min(1.0, center + half)
    return p, lo, hi


def mover(terms):
    """terms: list of (sign, p, lo, hi). Returns (estimate, lo, hi) for sum(sign*p)."""
    est = sum(s * p for s, p, _, _ in terms)
    lo_sq = sum(((p - lo) if s > 0 else (hi - p)) ** 2 for s, p, lo, hi in terms)
    hi_sq = sum(((hi - p) if s > 0 else (p - lo)) ** 2 for s, p, lo, hi in terms)
    return est, est - math.sqrt(lo_sq), est + math.sqrt(hi_sq)


def suggest_label(did, lo, hi, min_effect, lower_is_better=False):
    """Suggested outcome label against a pre-registered minimum effect.
    The pre-registration, not this function, is the final rule."""
    if lower_is_better:
        did, lo, hi = -did, -hi, -lo
    if lo > -min_effect and hi < min_effect:
        return "no detectable effect", "the whole interval is smaller than the minimum effect worth acting on"
    if lo > 0 and did >= min_effect:
        return "worked", "interval excludes zero and the estimate reaches the minimum effect"
    if hi < 0 and did <= -min_effect:
        return "made it worse", "interval excludes zero in the wrong direction and reaches the minimum effect"
    if lo > 0:
        return "inconclusive", "a change was detected but the estimate is below the minimum effect worth acting on"
    if hi < 0:
        return "inconclusive", "a drop was detected but the estimate is below the minimum effect"
    return "inconclusive", "the interval includes both zero and effects at least as large as the minimum"


def pct(x):
    return f"{x * 100:+.1f} pts" if x is not None else ""


def readout(tb, ta, cb, ca, confidence=0.95, min_effect=None, lower_is_better=False):
    z = NormalDist().inv_cdf(1 - (1 - confidence) / 2)
    cells = {name: (k, n) + wilson(k, n, z) for name, (k, n) in
             [("test_before", tb), ("test_after", ta), ("control_before", cb), ("control_after", ca)]}
    t = lambda name, s: (s, cells[name][2], cells[name][3], cells[name][4])  # noqa: E731
    test_change = mover([t("test_after", 1), t("test_before", -1)])
    control_change = mover([t("control_after", 1), t("control_before", -1)])
    did = mover([t("test_after", 1), t("test_before", -1), t("control_after", -1), t("control_before", 1)])
    result = {"confidence": confidence, "cells": cells, "test_change": test_change,
              "control_change": control_change, "did": did, "label": None}
    if min_effect is not None:
        result["label"] = suggest_label(*did, min_effect, lower_is_better)
    return result


def render(r):
    c = int(round(r["confidence"] * 100))
    lines = [f"Wilson {c}% intervals per cell", ""]
    lines.append(f"{'cell':<16}{'k/n':>9}{'rate':>9}{'interval':>20}")
    for name, (k, n, p, lo, hi) in r["cells"].items():
        lines.append(f"{name:<16}{f'{k}/{n}':>9}{p * 100:>8.1f}%{f'{lo * 100:.1f}% to {hi * 100:.1f}%':>20}")
    lines.append("")
    lines.append(f"Changes in percentage points, approximate {c}% intervals (MOVER)")
    lines.append("")
    for label, key in [("test change", "test_change"), ("control change", "control_change"),
                       ("diff-in-diff", "did")]:
        est, lo, hi = r[key]
        lines.append(f"{label:<16}{pct(est):>12}   ({pct(lo)} to {pct(hi)})")
    if r["label"]:
        lines.append("")
        lines.append(f"Suggested label: {r['label'][0]} ({r['label'][1]})")
        lines.append("Check this against the rule written in the pre-registration before using it.")
    small = [name for name, (k, n, *_rest) in r["cells"].items() if n < 30]
    if small:
        lines.append("")
        lines.append(f"Note: fewer than 30 observations in {', '.join(small)}. Treat the result as directional.")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test-before", type=parse_kn, required=True, metavar="K/N")
    ap.add_argument("--test-after", type=parse_kn, required=True, metavar="K/N")
    ap.add_argument("--control-before", type=parse_kn, required=True, metavar="K/N")
    ap.add_argument("--control-after", type=parse_kn, required=True, metavar="K/N")
    ap.add_argument("--min-effect", type=float, help="smallest change worth acting on, as a proportion (0.10 = 10 pts)")
    ap.add_argument("--confidence", type=float, default=0.95)
    ap.add_argument("--lower-is-better", action="store_true", help="for measures where a drop is the goal")
    args = ap.parse_args(argv)
    if not 0.5 < args.confidence < 1:
        ap.error("--confidence must be between 0.5 and 1")
    if args.min_effect is not None and not 0 < args.min_effect < 1:
        ap.error("--min-effect must be a proportion between 0 and 1")
    r = readout(args.test_before, args.test_after, args.control_before, args.control_after,
                args.confidence, args.min_effect, args.lower_is_better)
    sys.stdout.write(render(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())

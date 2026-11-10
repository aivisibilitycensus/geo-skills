#!/usr/bin/env python3
"""SV-001 scoring run: run each third-party audit script on each brand URL and record its score.

  python3 run_scores.py urls.csv --citability path/to/citability_scorer.py \
      --geo-audit path/to/geo-audit.mjs --out scores.csv --raw raw/

The third-party scripts are run as they are, at the commits pinned in the workflow, with
no arguments beyond the URL (and --json --lang en for geo-audit, so its output is
machine-readable). Both run with their default checks, as a user would run them.
A script that fails or returns no score for a URL is recorded with an empty score and
the reason. Nothing is retried more than once and no score is ever filled in by hand.
"""
import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

TIMEOUT = 180


def run_json(cmd):
    """Run a command, parse stdout as JSON. Returns (data or None, note)."""
    for attempt in (1, 2):
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            note = "timeout"
            continue
        text = p.stdout.strip()
        start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
        if start < 0:
            note = f"no JSON on stdout (exit {p.returncode}): {(p.stderr or text)[:200]}"
            continue
        try:
            return json.loads(text[start:]), f"exit {p.returncode}" + ("" if attempt == 1 else ", second attempt")
        except ValueError as e:
            note = f"bad JSON: {e}"
    return None, note


def citability(script, url):
    data, note = run_json([sys.executable, script, url])
    if data is None:
        return None, note, data
    if data.get("error"):
        return None, str(data["error"])[:200], data
    score = data.get("average_citability_score")
    blocks = data.get("total_blocks_analyzed", data.get("total_blocks"))
    if score is None:
        return None, "no average_citability_score in output", data
    return float(score), f"{note}; blocks={blocks}", data


def geo_audit(script, url):
    data, note = run_json(["node", script, url, "--json", "--lang", "en"])
    if data is None:
        return None, note, data
    if isinstance(data, list):
        data = data[0] if data else {}
    score = data.get("score")
    if score is None:
        return None, "no score in output", data
    return float(score), f"{note}; final={data.get('finalUrl', '')}", data


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls")
    ap.add_argument("--citability", help="path to geo-seo-claude scripts/citability_scorer.py")
    ap.add_argument("--geo-audit", help="path to geo-doctor cli/geo-audit.mjs")
    ap.add_argument("--out", default="scores.csv")
    ap.add_argument("--raw", default="raw")
    a = ap.parse_args(argv)
    os.makedirs(a.raw, exist_ok=True)
    scorers = [(n, s, f) for n, s, f in (("geo-seo-claude citability", a.citability, citability),
                                         ("geo-doctor audit", a.geo_audit, geo_audit)) if s]
    with open(a.urls, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["domain", "brand", "url", "scorer", "score", "note", "scored_at_utc"])
        for r in rows:
            for name, script, fn in scorers:
                score, note, raw = fn(script, r["url"])
                slug = name.split()[0] + "_" + r["domain"].replace(".", "-")
                with open(os.path.join(a.raw, slug + ".json"), "w", encoding="utf-8") as rf:
                    json.dump(raw, rf)
                w.writerow([r["domain"], r["brand"], r["url"], name, "" if score is None else score, note, stamp])
                print(f"{r['domain']:18} {name:28} {'' if score is None else score}  {note}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

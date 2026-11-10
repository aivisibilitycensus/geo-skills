#!/usr/bin/env python3
"""SV-001 analysis: do GEO audit scores go with being named by AI engines?

  python3 analyze.py scores.csv outcomes.csv --out-md readout.md

scores.csv    domain, scorer, score            (written by run_scores.py)
outcomes.csv  domain, engine, answers, named, cited   (exported from the Census100 collection)
covars.csv    domain, dr                       (optional, --covars; Ahrefs Domain Rating)

For each scorer and outcome it reports Spearman's rank correlation with a p-value from
seeded permutations. Standard library only. The decision rule is fixed in
../SV-001-protocol.md and is not a parameter here.
"""
import argparse
import csv
import math
import random
import sys
from collections import defaultdict

SEED = 20261110
PERMUTATIONS = 100000
ALPHA = 0.025            # two primary tests, Bonferroni from 0.05
MIN_N = 15               # fewer scored brands than this: arm reported as not testable


def ranks(values):
    """Average ranks, ties shared."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            out[order[k]] = r
        i = j + 1
    return out


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx == 0 or syy == 0:
        return float("nan")
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sxx * syy)


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def perm_p(x, y, n_perm=PERMUTATIONS, seed=SEED):
    """Two-sided permutation p-value for Spearman's rho."""
    rx, ry = ranks(x), ranks(y)
    obs = pearson(rx, ry)
    if math.isnan(obs):
        return obs, float("nan")
    rng = random.Random(seed)
    hits = 0
    ry = list(ry)
    for _ in range(n_perm):
        rng.shuffle(ry)
        if abs(pearson(rx, ry)) >= abs(obs) - 1e-12:
            hits += 1
    return obs, (hits + 1) / (n_perm + 1)


def partial_spearman(x, y, z):
    """Spearman correlation of x and y with z held fixed (first-order partial on ranks)."""
    rxy, rxz, ryz = spearman(x, y), spearman(x, z), spearman(y, z)
    den = math.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))
    return float("nan") if den == 0 else (rxy - rxz * ryz) / den


def power(n, rho, alpha=ALPHA, sims=2000, n_perm=2000, seed=SEED):
    """Share of simulated samples (bivariate normal, correlation rho) where the permutation
    test rejects at alpha. Used once, to state in the protocol what n can detect."""
    rng = random.Random(seed)
    wins = 0
    for s in range(sims):
        x = [rng.gauss(0, 1) for _ in range(n)]
        y = [rho * a + math.sqrt(1 - rho ** 2) * rng.gauss(0, 1) for a in x]
        _, p = perm_p(x, y, n_perm=n_perm, seed=seed + s)
        if p < alpha:
            wins += 1
    return wins / sims


def read_scores(path):
    out = defaultdict(dict)
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("score") or "").strip() == "":
                continue
            out[r["scorer"]][r["domain"].strip().lower()] = float(r["score"])
    return out


def read_outcomes(path):
    """Return {domain: {engine: (answers, named, cited)}} plus an 'all' engine pooled over engines."""
    out = defaultdict(dict)
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = r["domain"].strip().lower()
            out[d][r["engine"].strip().lower()] = (int(r["answers"]), int(r["named"]), int(r["cited"]))
    for d, eng in out.items():
        eng["all"] = tuple(sum(v[i] for v in eng.values()) for i in range(3))
    return out


def read_covars(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {r["domain"].strip().lower(): float(r["dr"]) for r in csv.DictReader(f) if (r.get("dr") or "").strip()}


def verdict(n, rho, p):
    if n < MIN_N:
        return "not testable (fewer than %d scored brands)" % MIN_N
    if math.isnan(rho):
        return "not testable (no variation)"
    if p < ALPHA and rho > 0:
        return "score goes with the outcome"
    if p < ALPHA and rho < 0:
        return "score goes against the outcome"
    return "no relationship detected"


def analyze(scores, outcomes, covars=None, n_perm=PERMUTATIONS):
    rows = []
    engines = sorted({e for v in outcomes.values() for e in v})
    engines = ["all"] + [e for e in engines if e != "all"]
    for scorer in sorted(scores):
        for engine in engines:
            for measure, idx in (("named", 1), ("cited", 2)):
                doms = [d for d in sorted(scores[scorer]) if engine in outcomes.get(d, {}) and outcomes[d][engine][0] > 0]
                x = [scores[scorer][d] for d in doms]
                y = [outcomes[d][engine][idx] / outcomes[d][engine][0] for d in doms]
                if len(doms) < 3:
                    rho, p = float("nan"), float("nan")
                else:
                    rho, p = perm_p(x, y, n_perm=n_perm)
                part = float("nan")
                if covars and len(doms) >= 4 and all(d in covars for d in doms):
                    part = partial_spearman(x, y, [covars[d] for d in doms])
                primary = engine == "all" and measure == "named"
                rows.append({"scorer": scorer, "engine": engine, "measure": measure, "n": len(doms),
                             "rho": rho, "p": p, "partial_rho_dr": part, "primary": primary,
                             "verdict": verdict(len(doms), rho, p) if primary else ""})
    return rows


def fmt(v, nd=2):
    return "n/a" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{nd}f}"


def render(rows):
    out = ["# SV-001 readout", "",
           "Spearman rank correlation between each audit score and the share of Census100 answers "
           f"that name (or cite) the brand. p from {PERMUTATIONS:,} seeded permutations, two-sided. "
           f"Primary tests: pooled engines, named share, one per scorer, alpha {ALPHA} each.", "",
           "## Primary tests", "", "| Scorer | Brands | rho | p | Verdict |", "|---|---|---|---|---|"]
    for r in rows:
        if r["primary"]:
            out.append(f"| {r['scorer']} | {r['n']} | {fmt(r['rho'])} | {fmt(r['p'], 3)} | {r['verdict']} |")
    out += ["", "\"No relationship detected\" is not \"the score does not work\". With about 20 brands "
            "this test only finds strong relationships; see the protocol for what it can detect.", "",
            "## All comparisons (secondary, no verdicts)", "",
            "| Scorer | Engine | Outcome | Brands | rho | p | rho with DR held fixed |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['scorer']} | {r['engine']} | {r['measure']} | {r['n']} | {fmt(r['rho'])} | "
                   f"{fmt(r['p'], 3)} | {fmt(r['partial_rho_dr'])} |")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scores")
    ap.add_argument("outcomes")
    ap.add_argument("--covars")
    ap.add_argument("--out-md")
    a = ap.parse_args(argv)
    rows = analyze(read_scores(a.scores), read_outcomes(a.outcomes), read_covars(a.covars) if a.covars else None)
    md = render(rows)
    if a.out_md:
        with open(a.out_md, "w", encoding="utf-8") as f:
            f.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())

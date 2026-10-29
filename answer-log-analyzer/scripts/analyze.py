#!/usr/bin/env python3
"""answer-log-analyzer: report how often a brand is named and cited in logged AI answers.

Standard library only. Reads a canonical CSV of logged answers (see SKILL.md) and a
brand config JSON, and writes a markdown report plus a CSV of per-cell results.

Usage:
  python3 analyze.py answers.csv --brands brands.json --out-md report.md --out-csv cells.csv
"""
import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, OrderedDict, defaultdict

Z95 = 1.959964
THIN_CELL = 3      # question x engine x period cells with fewer runs are flagged
THIN_AGG = 30      # aggregates with fewer answers are flagged as too thin to compare

REQUIRED = ["run_date", "engine", "question_id"]
MENTION_COLS = ["answer_text", "brands_named"]
OPTIONAL = ["period", "intent", "run_number", "question", "cited_urls"]
CONTENT_FIELDS = ["run_date", "period", "engine", "question_id", "intent", "run_number",
                  "question", "answer_text", "brands_named", "cited_urls"]


class InputError(Exception):
    """Raised for problems the user must fix in their input files."""


# ---------------------------------------------------------------- statistics

def wilson(k, n, z=Z95):
    """95% Wilson score interval for k successes out of n. Returns (low, high) or (None, None)."""
    if n == 0:
        return (None, None)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def two_proportion(k1, n1, k2, n2):
    """Pooled two-proportion z-test. Returns (z, two-sided p) or (None, None) if undefined."""
    if n1 == 0 or n2 == 0:
        return (None, None)
    pooled = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return (0.0, 1.0)
    z = (k2 / n2 - k1 / n1) / se
    return (z, math.erfc(abs(z) / math.sqrt(2)))


# ---------------------------------------------------------------- normalizing

def norm_host(url):
    """Reduce a URL or bare domain to a lowercase host without scheme, www., port or path."""
    s = (url or "").strip().strip("<>\"'()[]").lower()
    if not s:
        return ""
    s = re.sub(r"^[a-z][a-z0-9+.\-]*://", "", s)
    s = re.split(r"[/?#]", s, maxsplit=1)[0]
    s = s.split("@")[-1].split(":")[0].rstrip(".")
    if s.startswith("www."):
        s = s[4:]
    return s


def host_matches(host, domain):
    """True if host is the domain or any subdomain of it (blog.x.com matches x.com)."""
    return bool(host) and (host == domain or host.endswith("." + domain))


def split_list(value):
    """Split a semicolon (or newline) separated cell into trimmed, non-empty items."""
    return [p.strip() for p in re.split(r"[;\n]", value or "") if p.strip()]


def squash(value):
    return re.sub(r"\s+", " ", (value or "").strip())


# ---------------------------------------------------------------- brands

def load_brands(path):
    try:
        with open(path, encoding="utf-8-sig") as fh:
            cfg = json.load(fh)
    except FileNotFoundError:
        raise InputError("Brand config not found: %s" % path)
    except json.JSONDecodeError as exc:
        raise InputError("Brand config is not valid JSON (%s): %s" % (path, exc))
    return load_brands_from(cfg)


def load_brands_from(cfg):
    """Validate a parsed brand config. The first brand is the one the report is about."""
    if not isinstance(cfg, dict) or not isinstance(cfg.get("brand"), dict):
        raise InputError('Brand config needs a "brand" object: {"brand": {"name": ..., '
                         '"aliases": [...], "domains": [...]}, "competitors": [...]}')
    brands = []
    for i, raw in enumerate([cfg["brand"]] + list(cfg.get("competitors") or [])):
        if not isinstance(raw, dict) or not str(raw.get("name", "")).strip():
            raise InputError("Every brand and competitor needs a non-empty \"name\" (entry %d)." % i)
        name = str(raw["name"]).strip()
        aliases = [name] + [str(a).strip() for a in raw.get("aliases") or [] if str(a).strip()]
        domains = [norm_host(d) for d in raw.get("domains") or [] if norm_host(d)]
        brands.append({"name": name, "aliases": list(OrderedDict.fromkeys(aliases)),
                       "domains": list(OrderedDict.fromkeys(domains)), "primary": i == 0})
    names = [b["name"].lower() for b in brands]
    if len(set(names)) != len(names):
        raise InputError("Brand names in the config must be unique.")
    return brands


class Matcher:
    """Case-insensitive, word-bounded alias matching. Longer aliases claim text first, so a
    competitor called "Liffey Tax Partners" is not also counted as a brand aliased "Liffey"."""

    def __init__(self, brands):
        self.patterns = []
        self.warnings = []
        for b in brands:
            for alias in b["aliases"]:
                tokens = alias.split()
                rx = r"(?<!\w)" + r"\s+".join(re.escape(t) for t in tokens) + r"(?!\w)"
                self.patterns.append((len(alias), b["name"], re.compile(rx, re.IGNORECASE)))
                if len(tokens) == 1 and len(alias) < 4:
                    self.warnings.append('Alias "%s" (%s) is very short and may match unrelated '
                                         'words. Check a sample of answers by hand.' % (alias, b["name"]))
        self.patterns.sort(key=lambda p: -p[0])

    def find(self, text):
        """Return {brand name: offset of first mention} for configured brands found in text."""
        taken, first = [], {}
        for _, name, rx in self.patterns:
            for m in rx.finditer(text or ""):
                s, e = m.span()
                if any(s < te and ts < e for ts, te in taken):
                    continue
                taken.append((s, e))
                if name not in first or s < first[name]:
                    first[name] = s
        return first


# ---------------------------------------------------------------- loading answers

def read_rows(path):
    try:
        fh = open(path, encoding="utf-8-sig", newline="")
    except FileNotFoundError:
        raise InputError("Answers file not found: %s" % path)
    with fh:
        sample = fh.read()
    if not sample.strip():
        raise InputError("Answers file is empty: %s" % path)
    reader = csv.DictReader(sample.splitlines(True))
    if not reader.fieldnames:
        raise InputError("Answers file has no header row: %s" % path)
    header = {(h or "").strip().lower(): h for h in reader.fieldnames}
    missing = [c for c in REQUIRED if c not in header]
    if missing or not any(c in header for c in MENTION_COLS):
        need = missing + ([] if any(c in header for c in MENTION_COLS)
                          else ["answer_text or brands_named"])
        raise InputError("Missing required column(s): %s. Found: %s. Map your export's columns "
                         "to the canonical schema in SKILL.md first."
                         % (", ".join(need), ", ".join(h for h in reader.fieldnames if h)))
    rows = []
    for line_no, raw in enumerate(reader, start=2):
        row = {c: squash(raw.get(header[c])) if c in header and c != "answer_text"
               else (raw.get(header[c]) or "").strip() if c in header else ""
               for c in CONTENT_FIELDS}
        row["_line"] = line_no
        row["_extra_cells"] = None in raw
        rows.append(row)
    if not rows:
        raise InputError("Answers file has a header but no data rows: %s" % path)
    return rows, set(header)


def prepare(rows, columns, period_by):
    """Validate rows, drop exact duplicates, assign periods and run numbers."""
    notes, skipped, seen = [], [], set()
    dupes, kept = 0, []
    for r in rows:
        problems = [c for c in REQUIRED if not r[c]]
        if not r["answer_text"] and not r["brands_named"] and "brands_named" not in columns:
            problems.append("answer_text")
        if r["_extra_cells"]:
            problems.append("more cells than header columns")
        if period_by == "month" and not re.match(r"^\d{4}-\d{2}-\d{2}", r["run_date"]):
            problems.append("run_date not YYYY-MM-DD")
        if period_by == "column" and not r["period"]:
            problems.append("period")
        if problems:
            skipped.append((r["_line"], ", ".join(problems)))
            continue
        key = tuple(squash(r[c]) for c in CONTENT_FIELDS)
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        r["period"] = (r["run_date"][:7] if period_by == "month" else
                       r["run_date"] if period_by == "date" else r["period"])
        kept.append(r)
    counters = defaultdict(int)
    for r in kept:
        if not r["run_number"]:
            k = (r["run_date"], r["engine"], r["question_id"])
            counters[k] += 1
            r["run_number"] = "auto%d" % counters[k]
    collisions = Counter((r["run_date"], r["engine"], r["question_id"], r["run_number"]) for r in kept)
    clash = [k for k, v in collisions.items() if v > 1]
    if clash:
        notes.append("%d run key(s) (run_date, engine, question_id, run_number) appear more than once "
                     "with different content. All were kept as separate answers; check the export. "
                     "First: %s" % (len(clash), " / ".join(clash[0])))
    intents = defaultdict(Counter)
    for r in kept:
        intents[r["question_id"]][r["intent"] or "unlabeled"] += 1
    intent_of = {}
    for q, c in intents.items():
        intent_of[q] = c.most_common(1)[0][0]
        if len(c) > 1:
            notes.append("Question %s has more than one intent label (%s); using %s."
                         % (q, ", ".join(sorted(c)), intent_of[q]))
    for r in kept:
        r["intent"] = intent_of[r["question_id"]]
    return kept, skipped, dupes, notes


# ---------------------------------------------------------------- scoring answers

def score(rows, brands, matcher, mention_mode, cited_available):
    """Attach per-brand outcomes to each answer row."""
    fallbacks = 0
    domain_map = [(d, b["name"]) for b in brands for d in b["domains"]]
    for r in rows:
        use_list = mention_mode == "list" or (mention_mode == "text" and not r["answer_text"])
        if mention_mode == "text" and use_list:
            fallbacks += 1
        named_pos, others = {}, []
        if use_list:
            for idx, entry in enumerate(split_list(r["brands_named"]), start=1):
                found = matcher.find(entry)
                if found:
                    name = min(found, key=found.get)
                    named_pos.setdefault(name, idx)
                else:
                    others.append(entry)
        else:
            offsets = matcher.find(r["answer_text"])
            for rank, name in enumerate(sorted(offsets, key=offsets.get), start=1):
                named_pos[name] = rank
        hosts = [norm_host(u) for u in split_list(r["cited_urls"])]
        cited = {}
        for h in hosts:
            for d, name in domain_map:
                if host_matches(h, d):
                    cited.setdefault(name, []).append(h)
        r["_named"] = named_pos
        r["_others"] = others
        r["_cited"] = cited if cited_available else {}
    return fallbacks


def outcome(r, brand):
    named = brand in r["_named"]
    cited = brand in r["_cited"]
    other_named = any(n != brand for n in r["_named"]) or bool(r["_others"])
    return named, cited, other_named


def stats(rows, brand):
    s = {"n": len(rows), "named": 0, "cited": 0, "nc": 0, "nnc": 0, "cnn": 0,
         "cnn_other": 0, "absent": 0, "pos": []}
    for r in rows:
        named, cited, other = outcome(r, brand)
        s["named"] += named
        s["cited"] += cited
        if named and cited:
            s["nc"] += 1
        elif named:
            s["nnc"] += 1
        elif cited:
            s["cnn"] += 1
            s["cnn_other"] += other
        else:
            s["absent"] += 1
        if named:
            s["pos"].append(r["_named"][brand])
    return s


# ---------------------------------------------------------------- formatting

def pct(k, n):
    return "n/a" if n == 0 else "%.0f%%" % (100.0 * k / n)


def ci(k, n):
    lo, hi = wilson(k, n)
    return "n/a" if lo is None else "%.0f-%.0f%%" % (100 * lo, 100 * hi)


def rate_ci(k, n):
    return "n/a" if n == 0 else "%s (%s)" % (pct(k, n), ci(k, n))


def thin(n):
    return " (thin)" if n < THIN_AGG else ""


def mean_pos(pos):
    return "n/a" if not pos else "%.1f" % (sum(pos) / len(pos))


def table(header, body):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in body]
    return "\n".join(out)


def verdict(a, b):
    """Plain-language comparison of rate a (earlier) and b (later), each (k, n)."""
    (k1, n1), (k2, n2) = a, b
    if n1 < THIN_AGG or n2 < THIN_AGG:
        return "too thin to compare", None
    z, p = two_proportion(k1, n1, k2, n2)
    lo1, hi1 = wilson(k1, n1)
    lo2, hi2 = wilson(k2, n2)
    overlap = not (hi1 < lo2 or hi2 < lo1)
    if p is None:
        return "n/a", None
    if p < 0.05 and not overlap:
        return "change outside noise (intervals do not overlap)", p
    if p < 0.05:
        return "possible change (test p<0.05, intervals overlap): provisional", p
    return "within noise", p


# ---------------------------------------------------------------- report

def build(rows, brands, meta, compare):
    primary = brands[0]["name"]
    periods = sorted({r["period"] for r in rows})
    engines = sorted({r["engine"] for r in rows})
    questions = sorted({r["question_id"] for r in rows})
    intent_of = {r["question_id"]: r["intent"] for r in rows}
    qtext = {}
    for r in rows:
        if r["question"] and r["question_id"] not in qtext:
            qtext[r["question_id"]] = r["question"]
    intents = sorted(set(intent_of.values()))
    by = defaultdict(list)
    for r in rows:
        by[(r["period"], r["question_id"], r["engine"])].append(r)

    md = []
    md.append("# AI answer log report: %s" % primary)
    md.append("")
    md.append("## Data")
    md.append("")
    md.append("- Answers file: `%s`" % meta["path"])
    md.append("- Rows read: %d. Exact duplicates dropped: %d. Rows skipped as malformed: %d."
              % (meta["rows_read"], meta["dupes"], len(meta["skipped"])))
    if meta["skipped"]:
        md.append("  - First skipped rows (line: problem): " + "; ".join(
            "%d: %s" % s for s in meta["skipped"][:5]))
    md.append("- Answers analyzed: %d, over %d question(s), %d engine(s) (%s), %d period(s) (%s)."
              % (len(rows), len(questions), len(engines), ", ".join(engines), len(periods),
                 ", ".join(periods)))
    md.append("- Mentions detected from: %s." % meta["mention_desc"])
    md.append("- Citations: %s." % ("from `cited_urls`, matched by domain and subdomain"
                                   if meta["cited_available"] else
                                   "no `cited_urls` column, so cited measures are not available"))
    runs = Counter(len(v) for v in by.values())
    md.append("- Runs per question x engine x period cell: " + ", ".join(
        "%d run(s) in %d cell(s)" % (k, runs[k]) for k in sorted(runs)) + ".")
    for n in meta["notes"]:
        md.append("- Note: %s" % n)
    md.append("")
    md.append("Rates show the share of answers, with a 95%% Wilson interval in parentheses. "
              "\"(thin)\" marks any aggregate under %d answers: too few to compare. "
              "Cells with fewer than %d runs are marked with `*`." % (THIN_AGG, THIN_CELL))
    md.append("")

    # Headline per period for the primary brand
    md.append("## %s by period" % primary)
    md.append("")
    body = []
    for p in periods:
        pr = [r for r in rows if r["period"] == p]
        s = stats(pr, primary)
        first = sum(1 for x in s["pos"] if x == 1)
        body.append([p, "%d%s" % (s["n"], thin(s["n"])), rate_ci(s["named"], s["n"]),
                     rate_ci(s["cited"], s["n"]) if meta["cited_available"] else "n/a",
                     s["nc"], s["nnc"], s["cnn"], s["cnn_other"], s["absent"],
                     mean_pos(s["pos"]), "%d of %d" % (first, len(s["pos"]))])
    md.append(table(["Period", "Answers", "Named", "Cited", "Named and cited", "Named not cited",
                     "Cited not named", "of which named another brand", "Absent",
                     "Mean position when named", "Named first"], body))
    md.append("")
    md.append("Named and cited + named not cited + cited not named + absent = answers. "
              "\"Named another brand\" is the read-but-credited-someone-else case: the site was a "
              "source, and the answer named a different brand but not this one.")
    md.append("")

    # All brands
    md.append("## All configured brands by period")
    md.append("")
    body = []
    for b in brands:
        row = [b["name"] + (" (yours)" if b["primary"] else "")]
        for p in periods:
            pr = [r for r in rows if r["period"] == p]
            s = stats(pr, b["name"])
            row += [rate_ci(s["named"], s["n"]),
                    rate_ci(s["cited"], s["n"]) if meta["cited_available"] else "n/a"]
        body.append(row)
    hdr = ["Brand"] + [x for p in periods for x in ("Named %s" % p, "Cited %s" % p)]
    md.append(table(hdr, body))
    md.append("")

    # By engine and by intent
    for label, keyname, keys in (("engine", "engine", engines), ("intent", "intent", intents)):
        md.append("## %s by %s" % (primary, label))
        md.append("")
        body = []
        for k in keys:
            row = [k]
            for p in periods:
                pr = [r for r in rows if r["period"] == p and r[keyname] == k]
                s = stats(pr, primary)
                row += ["%s, n=%d%s" % (rate_ci(s["named"], s["n"]), s["n"], thin(s["n"])),
                        rate_ci(s["cited"], s["n"]) if meta["cited_available"] else "n/a"]
            body.append(row)
        md.append(table([label.capitalize()] + [x for p in periods for x in
                                                ("Named %s" % p, "Cited %s" % p)], body))
        md.append("")

    # Period comparison
    md.append("## Period comparison")
    md.append("")
    if not compare:
        md.append("Only one period in the data, so there is nothing to compare.")
        md.append("")
    else:
        p1, p2 = compare
        md.append("Comparing %s with %s for %s. A change is called \"outside noise\" only when a "
                  "two-proportion test gives p<0.05 and the two 95%% intervals do not overlap. "
                  "Anything else is reported as within noise or provisional." % (p1, p2, primary))
        md.append("")
        body = []
        groups = [("All answers", lambda r: True)]
        groups += [("Engine: " + e, (lambda e: lambda r: r["engine"] == e)(e)) for e in engines]
        groups += [("Intent: " + i, (lambda i: lambda r: r["intent"] == i)(i)) for i in intents]
        measures = [("named", "Named")] + ([("cited", "Cited")] if meta["cited_available"] else [])
        for gname, fn in groups:
            for key, mlabel in measures:
                a = stats([r for r in rows if r["period"] == p1 and fn(r)], primary)
                b = stats([r for r in rows if r["period"] == p2 and fn(r)], primary)
                v, p = verdict((a[key], a["n"]), (b[key], b["n"]))
                change = ("n/a" if not a["n"] or not b["n"] else
                          "%+.0f pts" % (100.0 * (b[key] / b["n"] - a[key] / a["n"])))
                body.append([gname, mlabel, "%s, n=%d" % (rate_ci(a[key], a["n"]), a["n"]),
                             "%s, n=%d" % (rate_ci(b[key], b["n"]), b["n"]), change,
                             "n/a" if p is None else "%.3f" % p, v])
        md.append(table(["Group", "Measure", p1, p2, "Change", "p", "Reading"], body))
        md.append("")
        md.append("Read this cautiously. Repeated runs of the same question are not independent "
                  "samples, so the real uncertainty is wider than these intervals suggest, and with "
                  "many rows a few will cross p<0.05 by chance. Question x engine cells (a few runs "
                  "each) are never compared on their own. The test says whether a difference is "
                  "larger than run-to-run noise. It cannot say why it happened.")
        md.append("")

    # Question x engine cells
    md.append("## Question x engine runs naming %s" % primary)
    md.append("")
    md.append("Each cell is runs naming the brand / runs. `*` = fewer than %d runs." % THIN_CELL)
    md.append("")
    body, mixed, total_cells = [], 0, 0
    for q in questions:
        row = [q, intent_of[q]]
        for e in engines:
            for p in periods:
                rr = by.get((p, q, e), [])
                if not rr:
                    row.append("-")
                    continue
                s = stats(rr, primary)
                total_cells += 1
                if 0 < s["named"] < s["n"]:
                    mixed += 1
                row.append("%d/%d%s" % (s["named"], s["n"], "*" if s["n"] < THIN_CELL else ""))
        body.append(row)
    md.append(table(["Question", "Intent"] + ["%s %s" % (e, p) for e in engines for p in periods],
                    body))
    md.append("")
    md.append("%d of %d cells are mixed (named in some runs, not others). A mixed cell means one "
              "run would have given a different answer from the next." % (mixed, total_cells))
    md.append("")

    # Cited not named
    if meta["cited_available"]:
        md.append("## Read but credited someone else")
        md.append("")
        cases = [r for r in rows if outcome(r, primary) == (False, True, True)]
        if not cases:
            md.append("No answer cited a %s page while naming another brand." % primary)
        else:
            md.append("%d answer(s) used a %s page as a source and named another brand, "
                      "but not %s." % (len(cases), primary, primary))
            md.append("")
            grouped = defaultdict(list)
            for r in cases:
                grouped[(r["question_id"], r["engine"])].append(r)
            body = []
            for (q, e), rr in sorted(grouped.items()):
                named = Counter(n for r in rr for n in list(r["_named"]) + r["_others"])
                hosts = sorted({h for r in rr for h in r["_cited"].get(primary, [])})
                body.append([q, e, len(rr), ", ".join("%s (%d)" % kv for kv in named.most_common()),
                             ", ".join(hosts)])
            md.append(table(["Question", "Engine", "Answers", "Named instead", "Your host cited"],
                            body))
        md.append("")

    # Zero-mention questions
    md.append("## Questions where %s was never named" % primary)
    md.append("")
    zero = [q for q in questions if stats([r for r in rows if r["question_id"] == q], primary)["named"] == 0]
    if not zero:
        md.append("None. Every question named %s at least once." % primary)
    else:
        md.append("Candidate content gaps. For each, list the 3 to 5 sub-questions an AI tool would "
                  "need answered first (question-set-builder, Step 4) and check whether the site "
                  "answers them.")
        md.append("")
        body = []
        for q in zero:
            rr = [r for r in rows if r["question_id"] == q]
            named = Counter(n for r in rr for n in list(r["_named"]) + r["_others"])
            s = stats(rr, primary)
            body.append([q, intent_of[q], qtext.get(q, ""), s["n"],
                         ", ".join("%s (%d)" % kv for kv in named.most_common()) or "no brand named",
                         s["cited"] if meta["cited_available"] else "n/a"])
        md.append(table(["Question", "Intent", "Text", "Answers", "Named instead (answers)",
                         "Answers citing your site"], body))
    md.append("")

    # Thin data
    md.append("## Thin data")
    md.append("")
    small_cells = sum(1 for v in by.values() if len(v) < THIN_CELL)
    md.append("- Cells with fewer than %d runs: %d of %d." % (THIN_CELL, small_cells, len(by)))
    thin_aggs = []
    for p in periods:
        for k in engines:
            n = sum(1 for r in rows if r["period"] == p and r["engine"] == k)
            if n < THIN_AGG:
                thin_aggs.append("%s / %s (n=%d)" % (p, k, n))
        for k in intents:
            n = sum(1 for r in rows if r["period"] == p and r["intent"] == k)
            if n < THIN_AGG:
                thin_aggs.append("%s / %s (n=%d)" % (p, k, n))
    md.append("- Engine or intent aggregates under %d answers: %s." % (
        THIN_AGG, "; ".join(thin_aggs) if thin_aggs else "none"))
    for w in meta["warnings"]:
        md.append("- Warning: %s" % w)
    md.append("")
    return "\n".join(md) + "\n"


def cell_rows(rows, brands, cited_available):
    by = defaultdict(list)
    for r in rows:
        by[(r["period"], r["question_id"], r["engine"])].append(r)
    out = []
    for (p, q, e), rr in sorted(by.items()):
        for b in brands:
            s = stats(rr, b["name"])
            lo, hi = wilson(s["named"], s["n"])
            clo, chi = wilson(s["cited"], s["n"])
            out.append(OrderedDict([
                ("period", p), ("question_id", q), ("intent", rr[0]["intent"]), ("engine", e),
                ("brand", b["name"]), ("is_primary", int(b["primary"])), ("runs", s["n"]),
                ("named", s["named"]), ("named_rate", round(s["named"] / s["n"], 4)),
                ("named_ci_low", round(lo, 4)), ("named_ci_high", round(hi, 4)),
                ("cited", s["cited"] if cited_available else ""),
                ("cited_rate", round(s["cited"] / s["n"], 4) if cited_available else ""),
                ("cited_ci_low", round(clo, 4) if cited_available else ""),
                ("cited_ci_high", round(chi, 4) if cited_available else ""),
                ("named_and_cited", s["nc"]), ("named_not_cited", s["nnc"]),
                ("cited_not_named", s["cnn"]), ("cited_not_named_other_brand_named", s["cnn_other"]),
                ("absent", s["absent"]),
                ("mean_position", round(sum(s["pos"]) / len(s["pos"]), 2) if s["pos"] else ""),
                ("thin_cell", int(s["n"] < THIN_CELL)),
            ]))
    return out


# ---------------------------------------------------------------- main

def run(args):
    brands = load_brands(args.brands)
    matcher = Matcher(brands)
    raw, columns = read_rows(args.answers)
    period_by = args.period_by or ("column" if "period" in columns else "month")
    if period_by == "column" and "period" not in columns:
        raise InputError("--period-by column needs a 'period' column.")
    rows, skipped, dupes, notes = prepare(raw, columns, period_by)
    if not rows:
        raise InputError("No usable rows after validation. First problems: %s"
                         % "; ".join("line %d: %s" % s for s in skipped[:5]))
    has_text = "answer_text" in columns and any(r["answer_text"] for r in rows)
    has_list = "brands_named" in columns
    mode = args.mentions
    if mode == "auto":
        mode = "text" if has_text else "list"
    if mode == "text" and not has_text:
        raise InputError("--mentions text needs a non-empty answer_text column.")
    if mode == "list" and not has_list:
        raise InputError("--mentions list needs a brands_named column.")
    cited_available = "cited_urls" in columns
    fallbacks = score(rows, brands, matcher, mode, cited_available)
    if mode == "text":
        desc = ("answer_text, by case-insensitive whole-word alias match. Position counts only "
                "configured brands, and brands not in the config are not detected")
        if fallbacks:
            desc += " (%d answer(s) had no text and used brands_named instead)" % fallbacks
    else:
        desc = "brands_named list (order = position)"
    periods = sorted({r["period"] for r in rows})
    compare = None
    if args.compare:
        missing = [p for p in args.compare if p not in periods]
        if missing:
            raise InputError("--compare period(s) not in data: %s. Periods found: %s"
                             % (", ".join(missing), ", ".join(periods)))
        compare = tuple(args.compare)
    elif len(periods) >= 2:
        compare = (periods[-2], periods[-1])
        if len(periods) > 2:
            notes.append("More than two periods found; comparing the last two. Use --compare to choose.")
    meta = {"path": args.answers, "rows_read": len(raw), "dupes": dupes, "skipped": skipped,
            "notes": notes, "mention_desc": desc, "cited_available": cited_available,
            "warnings": matcher.warnings}
    report = build(rows, brands, meta, compare)
    cells = cell_rows(rows, brands, cited_available)
    with open(args.out_md, "w", encoding="utf-8") as fh:
        fh.write(report)
    with open(args.out_csv, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cells[0].keys()))
        w.writeheader()
        w.writerows(cells)
    return len(rows), len(cells)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Analyze logged AI answers for brand mentions and citations.")
    ap.add_argument("answers", help="canonical answers CSV")
    ap.add_argument("--brands", required=True, help="brand config JSON")
    ap.add_argument("--out-md", default="report.md")
    ap.add_argument("--out-csv", default="cells.csv")
    ap.add_argument("--mentions", choices=["auto", "text", "list"], default="auto",
                    help="detect mentions from answer_text or the brands_named list (auto: text if present)")
    ap.add_argument("--period-by", choices=["column", "month", "date"],
                    help="how to group runs into periods (default: period column if present, else month of run_date)")
    ap.add_argument("--compare", nargs=2, metavar=("EARLIER", "LATER"), help="two periods to compare")
    args = ap.parse_args(argv)
    try:
        n, c = run(args)
    except InputError as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 2
    print("Analyzed %d answers. Wrote %s and %s (%d cell rows)." % (n, args.out_md, args.out_csv, c))
    return 0


if __name__ == "__main__":
    sys.exit(main())

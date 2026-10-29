#!/usr/bin/env python3
"""migration_check.py: protect AI search and organic visibility through a site migration.

Subcommands (run with -h for options):
  columns   FILE                      show a CSV's columns and guess which hold URLs and numbers
  baseline  --sources sources.json    record each important URL before launch (raw HTML, no JavaScript)
  redirects --map map.csv             follow every old URL and check where it lands
  parity    --baseline b.csv --map m  compare each baseline page with its new target
  robots    --old R1 --new R2         check that crawlers are not newly blocked
  launch    (all of the above)        one prioritized list: launch blockers, fix soon, check

Standard library only. Every fetch is a plain HTTP request: no JavaScript runs, so the
results show what a crawler that does not render JavaScript receives.
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pagekit as pk  # noqa: E402

BLOCKER, FIX, CHECK = "LAUNCH BLOCKER", "FIX SOON", "CHECK"
TIER_ORDER = {BLOCKER: 0, FIX: 1, CHECK: 2}
WORD_DROP = 0.30          # flag a drop in main-content words larger than this
TITLE_SIM_MIN = 0.30      # below this, the target title looks unrelated to the old page
MAX_HOPS_OK = 1

# Crawler tokens. Each was checked against the operator's own documentation (see SKILL.md).
AGENTS = [
    # token, operator, role, tier if newly blocked
    ("Googlebot", "Google", "Google Search crawler; also the control for AI Overviews and AI Mode", BLOCKER),
    ("Bingbot", "Microsoft", "Bing search crawler", BLOCKER),
    ("OAI-SearchBot", "OpenAI", "ChatGPT search results", BLOCKER),
    ("Claude-SearchBot", "Anthropic", "Claude search result quality", BLOCKER),
    ("PerplexityBot", "Perplexity", "Perplexity search results", BLOCKER),
    ("ChatGPT-User", "OpenAI", "user-triggered fetches (OpenAI: robots.txt rules may not apply)", FIX),
    ("Claude-User", "Anthropic", "user-triggered fetches for Claude users", FIX),
    ("Perplexity-User", "Perplexity", "user-triggered fetches (Perplexity: generally ignores robots.txt)", FIX),
    ("GPTBot", "OpenAI", "model training", CHECK),
    ("ClaudeBot", "Anthropic", "model training", CHECK),
    ("Google-Extended", "Google", "Gemini training and grounding control (not a separate crawler)", CHECK),
]


# =========================================================================== CSV input

def read_csv(path):
    """Return (header, rows as dicts, problems). Tolerates BOM, ; or tab delimiters, short rows."""
    problems = []
    with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        sample = f.read(65536)
        f.seek(0)
        if not sample.strip():
            return [], [], ["file is empty"]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(f, dialect)
        rows = list(reader)
    if not rows:
        return [], [], ["file is empty"]
    header = [h.strip() for h in rows[0]]
    out = []
    for i, r in enumerate(rows[1:], start=2):
        if not any(c.strip() for c in r):
            continue
        if len(r) != len(header):
            problems.append(f"line {i}: {len(r)} fields, header has {len(header)}")
        out.append({header[j]: (r[j].strip() if j < len(r) else "") for j in range(len(header))})
    return header, out, problems


def to_number(s):
    s = (s or "").strip().replace(",", "").replace("%", "")
    try:
        return float(s)
    except ValueError:
        return None


def guess_columns(header, rows):
    url_cols, num_cols = [], []
    for h in header:
        vals = [r.get(h, "") for r in rows[:200] if r.get(h, "")]
        if not vals:
            continue
        if sum(pk.looks_like_url(v) for v in vals) / len(vals) >= 0.8:
            url_cols.append(h)
        elif sum(to_number(v) is not None for v in vals) / len(vals) >= 0.8:
            num_cols.append(h)
    return url_cols, num_cols


def cmd_columns(args):
    header, rows, problems = read_csv(args.file)
    if not header:
        print(f"{args.file}: {', '.join(problems)}")
        return 1
    url_cols, num_cols = guess_columns(header, rows)
    print(f"File: {args.file}")
    print(f"Rows: {len(rows)}")
    print("Columns:")
    for h in header:
        tag = " <- looks like URLs" if h in url_cols else " <- numeric" if h in num_cols else ""
        ex = next((r[h] for r in rows if r.get(h)), "")
        print(f"  {h!r}: e.g. {ex[:60]!r}{tag}")
    for p in problems[:10]:
        print(f"Problem: {p}")
    print("\nAdd this file to sources.json with the column names you confirm, for example:")
    print(json.dumps({"file": args.file, "url_column": url_cols[0] if url_cols else "?",
                      "metric_column": num_cols[0] if num_cols else "",
                      "kind": "ai_citations | organic | other", "label": "describe the source"}, indent=2))
    return 0


def load_sources(args):
    """Return list of source dicts with resolved file paths."""
    if args.sources:
        with open(args.sources, encoding="utf-8") as f:
            cfg = json.load(f)
        base = os.path.dirname(os.path.abspath(args.sources))
        srcs = cfg.get("sources", cfg if isinstance(cfg, list) else [])
        for s in srcs:
            if not os.path.isabs(s["file"]):
                s["file"] = os.path.join(base, s["file"])
        return srcs
    if args.input:
        return [{"file": args.input, "url_column": args.url_col, "metric_column": args.metric_col,
                 "kind": args.kind, "label": args.label or os.path.basename(args.input)}]
    raise SystemExit("Give --sources sources.json or --input FILE")


def collect_urls(sources):
    urls, notes = {}, []
    for s in sources:
        header, rows, problems = read_csv(s["file"])
        label = s.get("label") or os.path.basename(s["file"])
        kind = s.get("kind") or "other"
        if kind not in ("ai_citations", "organic", "other"):
            notes.append(f"{label}: unknown kind {kind!r}, treated as 'other'")
            kind = "other"
        if not header:
            notes.append(f"{label}: {', '.join(problems)}")
            continue
        ucol = s.get("url_column")
        if not ucol:
            guess, _ = guess_columns(header, rows)
            ucol = guess[0] if guess else None
            notes.append(f"{label}: no url_column given, guessed {ucol!r}")
        if ucol not in header:
            notes.append(f"{label}: URL column {ucol!r} not in file (columns: {', '.join(header)}). Skipped.")
            continue
        mcol = s.get("metric_column") or ""
        if mcol and mcol not in header:
            notes.append(f"{label}: metric column {mcol!r} not found; metric left blank")
            mcol = ""
        skipped = 0
        for r in rows:
            u = r.get(ucol, "").strip()
            if not pk.looks_like_url(u):
                skipped += 1
                continue
            key = pk.norm_url(u)
            rec = urls.setdefault(key, {"url": u, "sources": [], "ai_citations": 0.0, "organic": 0.0, "other": 0.0})
            if label not in rec["sources"]:
                rec["sources"].append(label)
            val = to_number(r.get(mcol, "")) if mcol else None
            rec[kind] += val if val is not None else (1.0 if kind == "ai_citations" and not mcol else 0.0)
        if skipped:
            notes.append(f"{label}: {skipped} row(s) without a valid http(s) URL skipped")
        for p in problems[:5]:
            notes.append(f"{label}: {p}")
    return urls, notes


def priority_of(rec):
    if float(rec.get("ai_citations") or 0) > 0:
        return "P1"
    if float(rec.get("organic") or 0) > 0:
        return "P2"
    return "P3"


# =========================================================================== page snapshot

def snapshot(url, args):
    r = pk.fetch(url, timeout=args.timeout, user_agent=args.user_agent)
    snap = {"status": r["status"], "final_url": r["final_url"], "hops": len(r["hops"]),
            "hop_codes": ",".join(str(h["status"]) for h in r["hops"]), "error": r["error"] or "",
            "title": "", "h1": "", "canonical": "", "robots_meta": "", "x_robots_tag": "",
            "jsonld_types": "", "word_count": "", "main_word_count": "", "meta_refresh": ""}
    headers = {k.lower(): v for k, v in (r["headers"] or {}).items()}
    snap["x_robots_tag"] = headers.get("x-robots-tag", "")
    if r["body"] and "html" in headers.get("content-type", "text/html"):
        p = pk.parse_page(r["body"])
        snap.update(title=p["title"], h1=" | ".join(p["h1"]), canonical=" | ".join(p["canonical"]),
                    robots_meta="; ".join(f"{k}: {v}" for k, v in p["robots_meta"].items()),
                    jsonld_types="|".join(p["jsonld_types"]), word_count=p["word_count"],
                    main_word_count=p["main_word_count"], meta_refresh=p["meta_refresh"] or "")
    return snap, r


BASELINE_FIELDS = ["priority", "url", "sources", "ai_citations", "organic", "other", "status", "final_url",
                   "hops", "hop_codes", "title", "h1", "canonical", "robots_meta", "x_robots_tag",
                   "jsonld_types", "word_count", "main_word_count", "meta_refresh", "fetched_at", "error"]


def cmd_baseline(args):
    sources = load_sources(args)
    urls, notes = collect_urls(sources)
    for n in notes:
        print(f"Note: {n}", file=sys.stderr)
    if not urls:
        print("No URLs found in the inputs.", file=sys.stderr)
        return 1
    recs = sorted(urls.values(), key=lambda r: (priority_of(r), -r["ai_citations"], -r["organic"], r["url"]))
    if args.limit:
        recs = recs[:args.limit]
    out = []
    for i, rec in enumerate(recs):
        snap, _ = snapshot(rec["url"], args)
        row = {"priority": priority_of(rec), "url": rec["url"], "sources": "|".join(rec["sources"]),
               "ai_citations": _fmt(rec["ai_citations"]), "organic": _fmt(rec["organic"]),
               "other": _fmt(rec["other"]), "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               **snap}
        out.append(row)
        if args.delay and i < len(recs) - 1:
            time.sleep(args.delay)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=BASELINE_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    by = {p: sum(1 for r in out if r["priority"] == p) for p in ("P1", "P2", "P3")}
    print(f"Baseline written: {args.out}")
    print(f"URLs: {len(out)} (P1 cited by AI: {by['P1']}, P2 organic: {by['P2']}, P3 other: {by['P3']})")
    print(f"{'pri':<4}{'status':<7}{'words':>6}{'main':>6}  {'schema':<28}url")
    for r in out:
        status = r["status"] if not r["error"] else "ERR"
        if r["hops"]:
            status = f"{status}*"
        print(f"{r['priority']:<4}{str(status):<7}{str(r['word_count']):>6}{str(r['main_word_count']):>6}  "
              f"{(r['jsonld_types'] or '-')[:27]:<28}{r['url']}")
    if any(r["hops"] for r in out):
        print("* = the URL already redirects before the migration; final_url is recorded.")
    issues = [r for r in out if r["error"] or (r["status"] and int(r["status"]) >= 400)
              or "noindex" in (r["robots_meta"] + r["x_robots_tag"]).lower()]
    for r in issues:
        print(f"Baseline issue (fix before comparing): {r['url']} status={r['status']} {r['error']} "
              f"{r['robots_meta']} {r['x_robots_tag']}".rstrip())
    return 0


def _fmt(x):
    x = float(x or 0)
    return str(int(x)) if x.is_integer() else f"{x:.2f}"


def read_baseline(path):
    header, rows, problems = read_csv(path)
    if not header or "url" not in header:
        raise SystemExit(f"{path}: not a baseline file from this script ({', '.join(problems) or 'no url column'})")
    return {pk.norm_url(r["url"]): r for r in rows if r.get("url")}


def read_map(path, old_col, new_col):
    header, rows, problems = read_csv(path)
    if not header:
        raise SystemExit(f"{path}: {', '.join(problems)}")
    if old_col not in header or new_col not in header:
        raise SystemExit(f"{path}: needs columns {old_col!r} and {new_col!r}; found {', '.join(header)}. "
                         "Use --old-col / --new-col.")
    m, bad = {}, []
    for i, r in enumerate(rows, start=2):
        o, n = r.get(old_col, "").strip(), r.get(new_col, "").strip()
        if not pk.looks_like_url(o):
            bad.append(f"line {i}: old URL missing or not http(s): {o!r}")
            continue
        if n and not pk.looks_like_url(n):
            n = urllib.parse.urljoin(o, n)
        m[pk.norm_url(o)] = (o, n)
    return m, bad + problems


# =========================================================================== findings

class Findings:
    def __init__(self):
        self.items = []
        self._seen = set()

    def add(self, tier, priority, url, check, issue, evidence="", p1_escalate=False):
        if p1_escalate and priority == "P1" and tier == FIX:
            tier = BLOCKER
            issue += " (escalated: URL is cited by AI)"
        key = (url, check, issue)
        if key in self._seen:
            return
        self._seen.add(key)
        self.items.append({"tier": tier, "priority": priority, "url": url, "check": check,
                           "issue": issue, "evidence": evidence})

    def sorted(self):
        return sorted(self.items, key=lambda f: (TIER_ORDER[f["tier"]], f["priority"], f["check"], f["url"]))


def title_cores(a, b):
    """Drop title segments (split on | : or a spaced dash) that both titles share, such as a brand suffix."""
    split = lambda t: [x.strip() for x in re.split(r"\s[|\u2013\u2014-]\s|\s*\|\s*|:\s", t or "") if x.strip()]  # noqa: E731
    sa, sb = split(a), split(b)
    shared = {pk.norm(x) for x in sa} & {pk.norm(x) for x in sb}
    ca = " ".join(x for x in sa if pk.norm(x) not in shared) or (a or "")
    cb = " ".join(x for x in sb if pk.norm(x) not in shared) or (b or "")
    return ca, cb


def topic_similarity(a, b):
    return pk.title_similarity(*title_cores(a, b))


def is_noindex(robots_meta, x_robots):
    return "noindex" in (robots_meta or "").lower() or "noindex" in (x_robots or "").lower() \
        or "none" in re.split(r"[\s,;:]+", (robots_meta or "").lower())


def path_of(u):
    return urllib.parse.urlsplit(u).path or "/"


def check_redirects(mapping, baseline, args, F, stage="post"):
    targets = {}
    order = sorted(mapping.items(), key=lambda kv: (priority_of(baseline.get(kv[0], {})), kv[0]))
    for key, (old, new) in order:
        b = baseline.get(key, {})
        pri = b.get("priority") or "P3"
        r = pk.fetch(old, timeout=args.timeout, user_agent=args.user_agent)
        targets[key] = r
        chain = " -> ".join(f"{h['status']} {h['location']}" for h in r["hops"])
        ev_chain = f"{old} -> {chain}" if chain else old
        if r["error"]:
            F.add(BLOCKER, pri, old, "redirect", f"Request failed: {r['error']}", ev_chain)
            continue
        final = r["final_url"]
        if r["status"] and r["status"] >= 400:
            F.add(BLOCKER, pri, old, "redirect", f"Ends in HTTP {r['status']}", ev_chain)
            continue
        if not r["hops"]:
            if new and pk.norm_url(new) != key:
                if stage == "pre":
                    F.add(CHECK, pri, old, "redirect", "Not redirecting yet (pre-launch run)", f"HTTP {r['status']}")
                else:
                    F.add(BLOCKER, pri, old, "redirect", "Old URL does not redirect", f"HTTP {r['status']} at {old}; mapped to {new}")
            # URL unchanged in the map: the page itself is checked in parity
        else:
            if new and pk.norm_url(final) != pk.norm_url(new):
                F.add(FIX, pri, old, "redirect", "Lands on a different URL than the redirect map says",
                      f"map: {new} | actual: {final}", p1_escalate=True)
            n = len(r["hops"])
            if n >= 5:
                F.add(BLOCKER, pri, old, "redirect", f"Redirect chain of {n} hops", ev_chain)
            elif n > MAX_HOPS_OK:
                F.add(FIX, pri, old, "redirect", f"Redirect chain of {n} hops (redirect straight to the final URL)", ev_chain)
            temp = [h for h in r["hops"] if h["status"] in (302, 303, 307)]
            if temp:
                F.add(FIX, pri, old, "redirect", "Temporary redirect (" + ", ".join(str(h["status"]) for h in temp)
                      + "), use 301 or 308 for a permanent move", ev_chain, p1_escalate=True)
            if path_of(final) == "/" and path_of(old) != "/":
                F.add(BLOCKER, pri, old, "redirect", "Redirects to the homepage", ev_chain)
            old_title = b.get("title", "")
            if old_title and r["body"]:
                new_title = pk.parse_page(r["body"])["title"]
                sim = topic_similarity(old_title, new_title)
                if sim < TITLE_SIM_MIN:
                    F.add(FIX, pri, old, "redirect", f"Target title looks unrelated to the old page (similarity {sim:.2f})",
                          f"old: {old_title!r} | new: {new_title!r}", p1_escalate=True)
        # checks on whatever page the old URL ends on
        if r["body"]:
            p = pk.parse_page(r["body"])
            xr = {k.lower(): v for k, v in (r["headers"] or {}).items()}.get("x-robots-tag", "")
            rm = "; ".join(f"{k}: {v}" for k, v in p["robots_meta"].items())
            if is_noindex(rm, xr):
                F.add(BLOCKER, pri, old, "target", "Target page is noindex", f"{final} | meta: {rm or '-'} | X-Robots-Tag: {xr or '-'}")
            for c in p["canonical"]:
                cabs = urllib.parse.urljoin(final, c)
                if pk.norm_url(cabs) != pk.norm_url(final):
                    F.add(FIX, pri, old, "target", "Target canonical points to a different URL",
                          f"{final} canonical -> {cabs}", p1_escalate=True)
            if len(p["canonical"]) > 1:
                F.add(FIX, pri, old, "target", "Target has more than one canonical tag", " | ".join(p["canonical"]))
            if p["meta_refresh"]:
                F.add(CHECK, pri, old, "target", "Target uses a meta refresh", p["meta_refresh"])
    return targets


def check_parity(mapping, baseline, args, F, targets=None):
    rows = []
    for key, b in sorted(baseline.items(), key=lambda kv: (kv[1].get("priority", "P3"), kv[0])):
        pri = b.get("priority") or "P3"
        old = b["url"]
        new = mapping.get(key, (old, ""))[1] or old
        r = (targets or {}).get(key)
        if r is None:
            r = pk.fetch(new if key not in mapping else old, timeout=args.timeout, user_agent=args.user_agent)
        if r["error"] or not r["body"] or (r["status"] or 0) >= 400:
            if targets is None:  # redirects stage already reported failures when run together
                F.add(BLOCKER, pri, old, "parity", "New page could not be fetched",
                      f"{r['final_url']} status={r['status']} {r['error'] or ''}".strip())
            continue
        p = pk.parse_page(r["body"])
        final = r["final_url"]
        row = {"priority": pri, "old_url": old, "new_url": final}
        # title and h1
        if b.get("title") and topic_similarity(b["title"], p["title"]) < 0.6:
            F.add(CHECK, pri, old, "parity", "Title changed", f"old: {b['title']!r} | new: {p['title']!r}")
        old_h1 = b.get("h1", "")
        new_h1 = " | ".join(p["h1"])
        if old_h1 and not new_h1:
            F.add(FIX, pri, old, "parity", "h1 missing in the no-JavaScript view", f"old h1: {old_h1!r}")
        elif old_h1 and pk.title_similarity(old_h1, new_h1) < 0.6:
            F.add(CHECK, pri, old, "parity", "h1 changed", f"old: {old_h1!r} | new: {new_h1!r}")
        # structured data
        old_types = set(t for t in (b.get("jsonld_types") or "").split("|") if t)
        new_types = set(p["jsonld_types"])
        lost = sorted(old_types - new_types)
        if lost:
            F.add(FIX, pri, old, "parity", "JSON-LD types missing on the new page: " + ", ".join(lost),
                  f"old: {', '.join(sorted(old_types))} | new: {', '.join(sorted(new_types)) or 'none'}")
        if p["jsonld_errors"]:
            F.add(FIX, pri, old, "parity", "New page has JSON-LD that does not parse", "; ".join(p["jsonld_errors"]))
        # words in the no-JS view
        ow = to_number(str(b.get("main_word_count", "")))
        nw = p["main_word_count"]
        row.update(old_words=ow, new_words=nw)
        if ow and ow > 0:
            drop = (ow - nw) / ow
            if drop > WORD_DROP:
                tier = BLOCKER if nw < 50 else FIX
                note = " (almost no text without JavaScript: content may be rendered client-side)" if nw < 50 else ""
                F.add(tier, pri, old, "parity", f"Main-content words in the no-JavaScript view fell {drop:.0%}{note}",
                      f"{int(ow)} -> {nw} words", p1_escalate=True)
        # robots meta
        xr = {k.lower(): v for k, v in (r["headers"] or {}).items()}.get("x-robots-tag", "")
        rm = "; ".join(f"{k}: {v}" for k, v in p["robots_meta"].items())
        if is_noindex(rm, xr) and not is_noindex(b.get("robots_meta"), b.get("x_robots_tag")):
            F.add(BLOCKER, pri, old, "target", "Target page is noindex", f"{final} | meta: {rm or '-'} | X-Robots-Tag: {xr or '-'}")
        if "nofollow" in (rm + xr).lower() and "nofollow" not in (b.get("robots_meta", "") + b.get("x_robots_tag", "")).lower():
            F.add(FIX, pri, old, "parity", "New page adds nofollow", f"meta: {rm or '-'} | X-Robots-Tag: {xr or '-'}")
        if "nosnippet" in (rm + xr).lower() and "nosnippet" not in (b.get("robots_meta", "") + b.get("x_robots_tag", "")).lower():
            F.add(BLOCKER, pri, old, "parity", "New page adds nosnippet (Google: pages must be eligible for a snippet to appear in AI features)",
                  f"meta: {rm or '-'} | X-Robots-Tag: {xr or '-'}")
        rows.append(row)
    return rows


# =========================================================================== robots.txt (RFC 9309)

def parse_robots(text):
    groups, cur, last_ua = [], None, False
    for line in (text or "").splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            if not last_ua:
                cur = {"agents": [], "rules": []}
                groups.append(cur)
            cur["agents"].append(v.lower())
            last_ua = True
        elif k in ("allow", "disallow"):
            last_ua = False
            if cur is not None and v:
                cur["rules"].append((k, v))
            elif cur is not None and k == "disallow" and not v:
                pass  # empty disallow allows everything
        else:
            last_ua = False if k not in ("sitemap",) else last_ua
    return groups


def _rule_match(pattern, path):
    regex = re.escape(pattern).replace(r"\*", ".*")
    if regex.endswith(r"\$"):
        regex = regex[:-2] + "$"
    return re.match(regex, path) is not None


def robots_allowed(groups, agent, path):
    """Return (allowed, matched rule). Combines all groups naming the agent; falls back to '*'."""
    if path.split("?")[0] == "/robots.txt":
        return True, "robots.txt is always allowed"
    a = agent.lower()
    rules = [r for g in groups if a in g["agents"] for r in g["rules"]]
    named = any(a in g["agents"] for g in groups)
    if not named:
        rules = [r for g in groups if "*" in g["agents"] for r in g["rules"]]
    best = None
    for kind, pat in rules:
        if _rule_match(pat, path):
            length = len(pat.encode())
            if best is None or length > best[0] or (length == best[0] and kind == "allow"):
                best = (length, kind, pat)
    if not best:
        return True, ""
    return best[1] == "allow", f"{best[1]}: {best[2]} (group: {agent if named else '*'})"


def load_robots(src, args):
    """Return (groups, note, state). state: ok | allow_all | disallow_all."""
    if pk.looks_like_url(src):
        if not src.rstrip("/").endswith("robots.txt"):
            src = urllib.parse.urljoin(src, "/robots.txt")
        r = pk.fetch(src, timeout=args.timeout, user_agent=args.user_agent)
        if r["error"]:
            return [], f"{src}: {r['error']} (RFC 9309: treat an unreachable robots.txt as complete disallow)", "disallow_all"
        if r["status"] >= 500:
            return [], f"{src}: HTTP {r['status']} (RFC 9309: complete disallow)", "disallow_all"
        if r["status"] >= 400:
            return [], f"{src}: HTTP {r['status']} (RFC 9309: crawlers may access everything)", "allow_all"
        return parse_robots(r["body"]), f"{src}: HTTP {r['status']}" + (f" after {len(r['hops'])} redirect(s)" if r["hops"] else ""), "ok"
    with open(src, encoding="utf-8", errors="replace") as f:
        return parse_robots(f.read()), f"{src}: file", "ok"


def check_robots(old_src, new_src, paths_old, paths_new, args, F, prio_by_path=None):
    og, onote, ostate = load_robots(old_src, args) if old_src else ([], "no old robots.txt given (assumed allow all)", "allow_all")
    ng, nnote, nstate = load_robots(new_src, args)
    lines = [f"old: {onote}", f"new: {nnote}"]
    if nstate == "disallow_all":
        F.add(BLOCKER, "P1", new_src, "robots", "New robots.txt is unreachable or returns 5xx, which crawlers treat as complete disallow", nnote)
    table = []
    pairs = list(zip(paths_old, paths_new)) or [("/", "/")]
    if ("/", "/") not in pairs:
        pairs.insert(0, ("/", "/"))
    for token, operator, role, tier in AGENTS:
        newly, freed = [], []
        for po, pn in pairs:
            o_ok = True if ostate == "allow_all" else (False if ostate == "disallow_all" else robots_allowed(og, token, po)[0])
            n_ok, n_rule = (True, "") if nstate == "allow_all" else ((False, "unreachable") if nstate == "disallow_all" else robots_allowed(ng, token, pn))
            if o_ok and not n_ok:
                newly.append((po, pn, n_rule))
            elif not o_ok and n_ok:
                freed.append(pn)
        status = "newly blocked" if newly else ("newly allowed" if freed else "unchanged")
        table.append((token, operator, role, status, len(newly)))
        if newly:
            pri = "P1"
            if prio_by_path:
                pri = min((prio_by_path.get(po, "P3") for po, _, _ in newly), default="P3")
            sample = "; ".join(f"{pn} ({rule})" for _, pn, rule in newly[:4])
            more = f" and {len(newly) - 4} more" if len(newly) > 4 else ""
            what = "Training crawler newly blocked: confirm this is a deliberate decision" if tier == CHECK else \
                f"{token} newly blocked ({role})"
            F.add(tier, pri, f"robots.txt [{token}]", "robots", what, f"{len(newly)} path(s): {sample}{more}")
        if freed and tier != CHECK:
            F.add(CHECK, "P3", f"robots.txt [{token}]", "robots", f"{token} newly allowed on {len(freed)} path(s)", "; ".join(freed[:4]))
    lines.append(f"paths checked per crawler: {len(pairs)} (including /)")
    return lines, table


# =========================================================================== commands

def _paths_from(baseline, mapping):
    po, pn, prio = [], [], {}
    for key, b in baseline.items():
        old = b["url"]
        new = mapping.get(key, (old, ""))[1] or old
        po.append(_pathq(old))
        pn.append(_pathq(new))
        prio[_pathq(old)] = b.get("priority", "P3")
    for key, (old, new) in mapping.items():
        if key not in baseline:
            po.append(_pathq(old))
            pn.append(_pathq(new or old))
    return po, pn, prio


def _pathq(u):
    s = urllib.parse.urlsplit(u)
    return (s.path or "/") + (f"?{s.query}" if s.query else "")


def print_findings(F, title, baseline=None):
    items = F.sorted()
    counts = {t: sum(1 for f in items if f["tier"] == t) for t in (BLOCKER, FIX, CHECK)}
    print(f"\n{title}")
    print(f"{counts[BLOCKER]} launch blocker(s), {counts[FIX]} fix soon, {counts[CHECK]} to check")
    current = None
    for f in items:
        if f["tier"] != current:
            current = f["tier"]
            print(f"\n== {current} ==")
        print(f"[{f['priority']}] {f['url']}")
        print(f"     {f['check']}: {f['issue']}")
        if f["evidence"]:
            print(f"     evidence: {f['evidence']}")
    if not items:
        print("No issues found by the checks this script runs.")


def write_outputs(F, args, extra=None):
    if getattr(args, "json_out", None):
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump({"findings": F.sorted(), **(extra or {})}, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nJSON written: {args.json_out}")
    if getattr(args, "csv_out", None):
        with open(args.csv_out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["tier", "priority", "url", "check", "issue", "evidence"])
            w.writeheader()
            w.writerows(F.sorted())
        print(f"CSV written: {args.csv_out}")


def cmd_redirects(args):
    baseline = read_baseline(args.baseline) if args.baseline else {}
    mapping, bad = read_map(args.map, args.old_col, args.new_col)
    for b in bad:
        print(f"Map problem: {b}", file=sys.stderr)
    F = Findings()
    check_redirects(mapping, baseline, args, F, stage=args.stage)
    print(f"Redirect map: {args.map} ({len(mapping)} rows)")
    print_findings(F, "Redirect check")
    write_outputs(F, args)
    return 0


def cmd_parity(args):
    baseline = read_baseline(args.baseline)
    mapping = read_map(args.map, args.old_col, args.new_col)[0] if args.map else {}
    F = Findings()
    rows = check_parity(mapping, baseline, args, F)
    _print_words(rows)
    print_findings(F, "Post-launch parity")
    write_outputs(F, args)
    return 0


def _print_words(rows):
    if not rows:
        return
    print(f"{'pri':<4}{'old words':>10}{'new words':>10}  old URL -> new URL")
    for r in rows:
        ow = "" if r.get("old_words") is None else int(r["old_words"])
        print(f"{r['priority']:<4}{str(ow):>10}{str(r.get('new_words', '')):>10}  {r['old_url']} -> {r['new_url']}")


def cmd_robots(args):
    baseline = read_baseline(args.baseline) if args.baseline else {}
    mapping = read_map(args.map, args.old_col, args.new_col)[0] if args.map else {}
    po, pn, prio = _paths_from(baseline, mapping)
    F = Findings()
    lines, table = check_robots(args.old, args.new, po, pn, args, F, prio)
    _print_robots(lines, table, len(po) or 1)
    print_findings(F, "robots.txt check")
    write_outputs(F, args)
    return 0


def _print_robots(lines, table, npaths):
    print("robots.txt sources:")
    for ln in lines:
        print(f"  {ln}")
    print(f"{'token':<18}{'operator':<11}{'status':<19}role")
    for token, op, role, status, n in table:
        st = f"{status} ({n})" if n else status
        print(f"{token:<18}{op:<11}{st:<19}{role}")


def cmd_launch(args):
    baseline = read_baseline(args.baseline)
    mapping, bad = read_map(args.map, args.old_col, args.new_col)
    for b in bad:
        print(f"Map problem: {b}", file=sys.stderr)
    F = Findings()
    print(f"Baseline: {args.baseline} ({len(baseline)} URLs) | Map: {args.map} ({len(mapping)} rows)")
    unmapped = [b["url"] for k, b in baseline.items() if k not in mapping]
    for u in unmapped:
        pri = baseline[pk.norm_url(u)].get("priority", "P3")
        F.add(FIX, pri, u, "redirect", "Baseline URL is not in the redirect map (checked as unchanged)", "", p1_escalate=True)
    targets = check_redirects(mapping, baseline, args, F, stage="post")
    rows = check_parity(mapping, baseline, args, F, targets=targets)
    print("\nNo-JavaScript word counts (main content):")
    _print_words(rows)
    robots_info = None
    if args.new_robots:
        po, pn, prio = _paths_from(baseline, mapping)
        lines, table = check_robots(args.old_robots, args.new_robots, po, pn, args, F, prio)
        print()
        _print_robots(lines, table, len(po) or 1)
        robots_info = {"sources": lines, "agents": [dict(zip(["token", "operator", "role", "status", "paths"], t)) for t in table]}
    else:
        print("\nrobots.txt not checked (give --new-robots).")
    print_findings(F, "Migration launch check")
    write_outputs(F, args, {"word_counts": rows, "robots": robots_info})
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--user-agent", default=pk.DEFAULT_UA)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("columns", help="show a CSV's columns")
    s.add_argument("file")
    s.set_defaults(fn=cmd_columns)

    def common_out(p):
        p.add_argument("--json-out", help="write findings as JSON")
        p.add_argument("--csv-out", help="write findings as CSV")

    def map_args(p, required):
        p.add_argument("--map", required=required, help="redirect map CSV")
        p.add_argument("--old-col", default="old_url")
        p.add_argument("--new-col", default="new_url")

    s = sub.add_parser("baseline", help="record important URLs before launch")
    s.add_argument("--sources", help="JSON file listing input CSVs and their column mapping")
    s.add_argument("--input", help="a single CSV instead of --sources")
    s.add_argument("--url-col")
    s.add_argument("--metric-col")
    s.add_argument("--kind", default="other", choices=["ai_citations", "organic", "other"])
    s.add_argument("--label")
    s.add_argument("--out", default="baseline.csv")
    s.add_argument("--limit", type=int, default=0, help="only the first N URLs after prioritizing")
    s.add_argument("--delay", type=float, default=0.0, help="seconds between requests")
    s.set_defaults(fn=cmd_baseline)

    s = sub.add_parser("redirects", help="check the redirect map")
    map_args(s, True)
    s.add_argument("--baseline", help="baseline CSV, for priorities and old titles")
    s.add_argument("--stage", choices=["pre", "post"], default="post")
    common_out(s)
    s.set_defaults(fn=cmd_redirects)

    s = sub.add_parser("parity", help="compare baseline pages with their new targets")
    s.add_argument("--baseline", required=True)
    map_args(s, False)
    common_out(s)
    s.set_defaults(fn=cmd_parity)

    s = sub.add_parser("robots", help="compare old and new robots.txt for search and AI crawlers")
    s.add_argument("--old", help="old robots.txt (URL or saved file)")
    s.add_argument("--new", required=True, help="new robots.txt (URL or saved file)")
    s.add_argument("--baseline")
    map_args(s, False)
    common_out(s)
    s.set_defaults(fn=cmd_robots)

    s = sub.add_parser("launch", help="redirects + parity + robots in one prioritized list")
    s.add_argument("--baseline", required=True)
    map_args(s, True)
    s.add_argument("--old-robots", help="saved copy of the old robots.txt (URL or file)")
    s.add_argument("--new-robots", help="new robots.txt (URL or file)")
    common_out(s)
    s.set_defaults(fn=cmd_launch)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except FileNotFoundError as e:
        print(f"File not found: {e.filename}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

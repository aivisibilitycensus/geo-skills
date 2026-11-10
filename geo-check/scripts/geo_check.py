#!/usr/bin/env python3
"""geo_check.py: one command that checks whether AI search can reach and read a page.

  python3 geo_check.py https://example.com/pricing
  python3 geo_check.py https://example.com/ --out-md report.md --json-out report.json

It makes plain HTTP requests (no JavaScript) for the page, robots.txt and llms.txt, then
lists findings in four tiers. There is no score: a page that fails one BLOCKS check is
not "80% fine", and nobody has shown that a higher audit score means being named more.

Every finding carries the evidence grade for the claim behind it, from tactics/EVIDENCE.md:
[P] platform documentation, [S] published study, [U] untested.

Standard library only. If the schema-parity-checker skill sits next to this one, its
field-by-field comparison is run too.
"""
import argparse
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pagekit as pk  # noqa: E402

BLOCKS, FIX, CHECK, INFO = "BLOCKS", "FIX", "CHECK", "INFO"
TIER_ORDER = {BLOCKS: 0, FIX: 1, CHECK: 2, INFO: 3}
TIER_MEANS = {
    BLOCKS: "stops an engine from using the page",
    FIX: "likely to cost you, worth fixing",
    CHECK: "cannot be decided from outside, look at it",
    INFO: "recorded, no action implied",
}
THIN_WORDS = 100          # raw-HTML words below this get a JavaScript-rendering check

# token, operator, what a block costs, tier when blocked.
# Roles are from each operator's own documentation; see ai-crawler-log-check/references/crawlers.md.
AGENTS = [
    ("Googlebot", "Google", "Google Search, and with it AI Overviews and AI Mode", BLOCKS),
    ("Bingbot", "Microsoft", "Bing, and with it Copilot", BLOCKS),
    ("OAI-SearchBot", "OpenAI", "ChatGPT search answers", BLOCKS),
    ("Claude-SearchBot", "Anthropic", "Claude search results", BLOCKS),
    ("PerplexityBot", "Perplexity", "Perplexity search results", BLOCKS),
    ("ChatGPT-User", "OpenAI", "pages ChatGPT fetches when a user asks", FIX),
    ("Claude-User", "Anthropic", "pages Claude fetches when a user asks", FIX),
    ("Perplexity-User", "Perplexity", "pages Perplexity fetches when a user asks", FIX),
    ("GPTBot", "OpenAI", "model training (a choice, not a fault)", INFO),
    ("ClaudeBot", "Anthropic", "model training (a choice, not a fault)", INFO),
    ("Google-Extended", "Google", "Gemini training and grounding (a choice, not a fault)", INFO),
]
# Tokens to send as a user agent, to see whether a firewall or CDN answers them differently.
UA_PROBES = ["OAI-SearchBot", "GPTBot", "ClaudeBot", "PerplexityBot"]

EV = {
    "indexable": ("[P]", "Google: a page must be indexed and eligible to be shown with a snippet to appear in AI Overviews and AI Mode"),
    "oai": ("[P]", "OpenAI: sites opted out of OAI-SearchBot will not be shown in ChatGPT search answers"),
    "robots": ("[P]", "Each operator documents that its crawler follows robots.txt for this token"),
    "user_fetch": ("[P]", "Operators document these as user-triggered fetches; some say robots.txt may not apply to them"),
    "training": ("[P]", "Operators document these tokens as training controls, separate from search"),
    "js": ("[S]", "Vercel and MERJ (December 2024): most AI crawlers did not render JavaScript; Googlebot and Applebot did"),
    "parity": ("[P]", "Google lists structured data matching the visible text among practices for AI features"),
    "markup": ("[P] against", "Google: no special markup or AI text files are needed for its AI features"),
    "llms": ("[U]", "llms.txt is a proposal; no evidence found that it changes what AI engines show"),
    "firewall": ("[U]", "A user-agent test from one address; real crawlers come from other addresses and may be treated differently"),
    "none": ("", ""),
}


class Findings:
    def __init__(self):
        self.items = []

    def add(self, tier, check, found, why="none", fix=""):
        grade, basis = EV[why]
        self.items.append({"tier": tier, "check": check, "found": found, "fix": fix,
                           "evidence_grade": grade, "evidence": basis})

    def sorted(self):
        return sorted(self.items, key=lambda f: TIER_ORDER[f["tier"]])

    def count(self, tier):
        return sum(1 for f in self.items if f["tier"] == tier)


# --------------------------------------------------------------------------- robots.txt
# Same parser as geo-migration-guard (RFC 9309 longest match, allow wins ties).

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
        elif k != "sitemap":
            last_ua = False
    return groups


def _rule_match(pattern, path):
    regex = re.escape(pattern).replace(r"\*", ".*")
    if regex.endswith(r"\$"):
        regex = regex[:-2] + "$"
    return re.match(regex, path) is not None


def robots_allowed(groups, agent, path):
    """Return (allowed, matched rule). Uses the groups naming the agent, else the '*' groups."""
    a = agent.lower()
    named = any(a in g["agents"] for g in groups)
    rules = [r for g in groups if (a if named else "*") in g["agents"] for r in g["rules"]]
    best = None
    for kind, pat in rules:
        if _rule_match(pat, path):
            length = len(pat.encode())
            if best is None or length > best[0] or (length == best[0] and kind == "allow"):
                best = (length, kind, pat)
    if not best:
        return True, ""
    return best[1] == "allow", f"{best[1]}: {best[2]} (group: {agent if named else '*'})"


def check_robots(F, origin, path, opts):
    url = urllib.parse.urljoin(origin, "/robots.txt")
    r = pk.fetch(url, timeout=opts["timeout"], user_agent=opts["user_agent"])
    table = []
    if r["error"] or (r["status"] or 0) >= 500:
        what = r["error"] or f"HTTP {r['status']}"
        F.add(BLOCKS, "robots.txt", f"{url} could not be read ({what}). Under RFC 9309 crawlers treat this as "
              "\"do not crawl anything\".", "robots", "Make robots.txt return 200, or 404 if you have none.")
        return table
    if r["status"] >= 400:
        F.add(INFO, "robots.txt", f"{url} returns HTTP {r['status']}: no rules, crawlers may fetch everything.", "robots")
        return table
    groups = parse_robots(r["body"])
    for token, operator, costs, tier in AGENTS:
        ok, rule = robots_allowed(groups, token, path)
        table.append({"agent": token, "operator": operator, "allowed": ok, "rule": rule})
        if ok:
            continue
        why = "oai" if token == "OAI-SearchBot" else "training" if tier == INFO else \
              "user_fetch" if tier == FIX else "robots"
        fix = "" if tier == INFO else f"Remove or narrow the rule if you want {operator} to use this page."
        F.add(tier, "robots.txt", f"{token} is blocked from {path} by \"{rule}\". Affects: {costs}.", why, fix)
    if all(t["allowed"] for t in table):
        F.add(INFO, "robots.txt", f"All {len(table)} search and AI crawler tokens checked may fetch {path}.", "robots")
    return table


# --------------------------------------------------------------------------- page checks

def is_noindex(value):
    parts = [p.strip() for p in re.split(r"[,;]", (value or "").lower())]
    return "noindex" in parts or "none" in parts


def has_nosnippet(value):
    v = (value or "").lower().replace(" ", "")
    return "nosnippet" in v or "max-snippet:0" in v


def check_page(F, url, opts):
    r = pk.fetch(url, timeout=opts["timeout"], user_agent=opts["user_agent"])
    info = {"url": url, "final_url": r["final_url"], "status": r["status"], "hops": len(r["hops"])}
    if r["error"]:
        F.add(BLOCKS, "Page request", f"{url} could not be fetched: {r['error']}.")
        return None, info
    if r["status"] != 200:
        F.add(BLOCKS, "Page request", f"{r['final_url']} returns HTTP {r['status']}. A crawler gets no content.",
              "indexable", "Return 200 for the page you want named.")
        return None, info
    if len(r["hops"]) > 1:
        chain = " -> ".join(h["url"] for h in r["hops"]) + " -> " + r["final_url"]
        F.add(CHECK, "Redirects", f"{len(r['hops'])} redirects before the page: {chain}.", "none",
              "Link and redirect straight to the final URL.")
    page = pk.parse_page(r["body"])
    headers = {k.lower(): v for k, v in r["headers"].items()}
    xrobots = headers.get("x-robots-tag", "")
    meta = "; ".join(f"{k}: {v}" for k, v in page["robots_meta"].items())
    info.update(title=page["title"], words=page["word_count"], main_words=page["main_word_count"],
                robots_meta=meta, x_robots_tag=xrobots, jsonld_types=page["jsonld_types_all"],
                canonical=page["canonical"])
    directives = ",".join(list(page["robots_meta"].values()) + [xrobots])
    if is_noindex(directives):
        where = "X-Robots-Tag header" if is_noindex(xrobots) else "robots meta tag"
        F.add(BLOCKS, "Indexing", f"The page says noindex ({where}: {xrobots or meta}).", "indexable",
              "Remove noindex if this page should appear in search or AI answers.")
    elif has_nosnippet(directives):
        F.add(FIX, "Snippets", f"The page limits snippets ({meta or xrobots}).", "indexable",
              "Remove nosnippet or max-snippet:0 if you want Google's AI features to quote the page.")
    canon = page["canonical"]
    if canon and pk.norm_url(urllib.parse.urljoin(r["final_url"], canon)) != pk.norm_url(r["final_url"]):
        F.add(CHECK, "Canonical", f"The canonical points to another URL: {canon}.", "none",
              "Fine if deliberate. If not, engines are told to use that page instead of this one.")
    scripts = len(re.findall(r"<script\b", r["body"], re.I))
    if page["word_count"] < THIN_WORDS:
        F.add(FIX, "Text in raw HTML", f"The HTML the server sends has {page['word_count']} words of visible "
              f"text and {scripts} script tags. If the page shows more in a browser, that text is added by "
              "JavaScript.", "js", "Server-render the content you want quoted, then run this again.")
    else:
        F.add(INFO, "Text in raw HTML", f"{page['word_count']} words of visible text arrive without JavaScript "
              f"({page['main_word_count']} in the main content).", "js")
    check_schema(F, r, page, opts)
    return page, info


def check_schema(F, r, page, opts):
    for err in page["jsonld_errors"]:
        F.add(FIX, "Structured data", f"A JSON-LD block does not parse: {str(err)[:160]}.", "parity",
              "Fix the JSON so the block can be read at all.")
    if not page["jsonld_blocks"] and not page["microdata_items"] and not page["rdfa_attrs"]:
        F.add(INFO, "Structured data", "No structured data on the page. It is not required for AI answers.", "markup")
        return
    sp = load_schema_parity()
    if sp is None:
        F.add(INFO, "Structured data", f"JSON-LD types found: {', '.join(page['jsonld_types_all']) or 'none'}. "
              "Field-by-field comparison with the visible text was not run (schema-parity-checker not installed "
              "next to this skill).", "parity")
        return
    _, rep, checked = sp.analyze(r["body"], r["final_url"], False, opts["timeout"])
    bad = [f for f in rep.findings if f["severity"] in ("high", "medium")]
    for f in bad[:8]:
        F.add(FIX if f["severity"] == "high" else CHECK, "Structured data",
              f"{f['type']}.{f['field']}: {f['issue']}. Schema says \"{f['schema_value']}\"."
              + (f" Page shows \"{f['page_evidence']}\"." if f["page_evidence"] else ""), "parity",
              "Make the markup say what the page says.")
    if len(bad) > 8:
        F.add(CHECK, "Structured data", f"{len(bad) - 8} more mismatches. Run schema-parity-checker for the full list.", "parity")
    if not bad:
        F.add(INFO, "Structured data", f"Checked {', '.join(sorted(set(checked))) or 'no supported types'}: "
              f"{len(rep.ok)} field(s) match the visible page, none differ.", "parity")


def load_schema_parity():
    path = os.path.join(HERE, "..", "..", "schema-parity-checker", "scripts")
    if not os.path.isfile(os.path.join(path, "schema_parity.py")):
        return None
    sys.path.insert(0, path)
    try:
        import schema_parity
        return schema_parity
    except Exception:
        return None


def check_firewall(F, url, opts, base_status):
    """Send the same request with crawler tokens in the user agent and compare the status."""
    out = []
    for token in UA_PROBES:
        ua = f"Mozilla/5.0 (compatible; {token}/1.0)"
        r = pk.fetch(url, timeout=opts["timeout"], user_agent=ua)
        status = r["status"] if not r["error"] else None
        out.append({"agent": token, "status": status, "error": r["error"]})
        if status != base_status:
            got = r["error"] or f"HTTP {status}"
            F.add(CHECK, "Firewall or CDN", f"A request with \"{token}\" in the user agent gets {got}; the same "
                  f"request with a browser-like user agent gets HTTP {base_status}.", "firewall",
                  "Look at your CDN or firewall bot rules. Confirm with server logs (ai-crawler-log-check) "
                  "before changing anything.")
    if all(o["status"] == base_status for o in out):
        F.add(INFO, "Firewall or CDN", f"Requests with {', '.join(UA_PROBES)} in the user agent get the same "
              f"HTTP {base_status} as a browser-like one.", "firewall")
    return out


def check_llms(F, origin, opts):
    url = urllib.parse.urljoin(origin, "/llms.txt")
    r = pk.fetch(url, timeout=opts["timeout"], user_agent=opts["user_agent"])
    present = not r["error"] and r["status"] == 200 and "<html" not in r["body"][:2000].lower()
    F.add(INFO, "llms.txt", ("Present." if present else "Not present.") + " Neither is a finding: there is no "
          "evidence it changes what AI engines show.", "llms")
    return present


# --------------------------------------------------------------------------- run and report

NOT_CHECKED = [
    "Whether AI engines name or cite you. That needs logged answers: question-set-builder, answer-collector, answer-log-analyzer.",
    "Whether crawlers actually visit. That needs server logs: ai-crawler-log-check.",
    "What a browser shows after JavaScript runs. This check reads the HTML the server sends.",
    "Rankings, backlinks, content quality. No score is given for any of them.",
]


def run(url, opts):
    if not pk.looks_like_url(url):
        url = "https://" + url
    F = Findings()
    page, info = check_page(F, url, opts)
    final = info["final_url"] or url
    parts = urllib.parse.urlsplit(final)
    origin = f"{parts.scheme}://{parts.netloc}"
    path = parts.path or "/"
    robots = check_robots(F, origin, path, opts)
    probes = check_firewall(F, final, opts, info["status"]) if info["status"] == 200 and not opts["no_probe"] else []
    llms = check_llms(F, origin, opts)
    return {"page": info, "findings": F.sorted(), "robots": robots, "user_agent_probes": probes,
            "llms_txt": llms, "not_checked": NOT_CHECKED,
            "counts": {t: F.count(t) for t in (BLOCKS, FIX, CHECK, INFO)}}


def render_markdown(res):
    p, c = res["page"], res["counts"]
    out = [f"# GEO check: {p['final_url'] or p['url']}", ""]
    out.append(f"HTTP {p['status']}" + (f" after {p['hops']} redirect(s)" if p.get("hops") else "")
               + (f". Title: {p['title']}" if p.get("title") else "") + ".")
    out += ["", f"**{c[BLOCKS]} blocking, {c[FIX]} to fix, {c[CHECK]} to check, {c[INFO]} recorded.** "
            "No score: these are separate findings, not parts of a total.", ""]
    for tier in (BLOCKS, FIX, CHECK, INFO):
        items = [f for f in res["findings"] if f["tier"] == tier]
        if not items:
            continue
        out += [f"## {tier}: {TIER_MEANS[tier]}", ""]
        for f in items:
            out.append(f"- **{f['check']}.** {f['found']}")
            if f["fix"]:
                out.append(f"  - Do: {f['fix']}")
            if f["evidence_grade"]:
                out.append(f"  - Evidence {f['evidence_grade']}: {f['evidence']}.")
        out.append("")
    if res["robots"]:
        out += ["## robots.txt by crawler", "", "| Crawler | Operator | This page | Rule |", "|---|---|---|---|"]
        for t in res["robots"]:
            out.append(f"| {t['agent']} | {t['operator']} | {'allowed' if t['allowed'] else 'blocked'} | {t['rule'] or 'no matching rule'} |")
        out.append("")
    out += ["## Not checked", ""] + [f"- {n}" for n in res["not_checked"]]
    out += ["", "Evidence grades are explained in tactics/EVIDENCE.md: [P] platform documentation, "
            "[S] published study, [U] untested. A grade says how well the claim is supported, not that "
            "fixing the item will get a page named."]
    return "\n".join(out) + "\n"


REPO = "https://github.com/aivisibilitycensus/geo-skills"


def badge_markdown(res, date):
    """A README badge that states a count, not a score. Only offered when nothing blocks."""
    n = res["counts"][BLOCKS]
    if n:
        return ""
    label = "AI%20search%20check"
    msg = f"0%20blocking%20%C2%B7%20{date}"
    return (f"[![AI search check: 0 blocking findings, {date}]"
            f"(https://img.shields.io/badge/{label}-{msg}-2ea44f)]({REPO}/tree/main/geo-check)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--badge", action="store_true",
                    help="when nothing blocks, print a README badge line stating the count and date")
    ap.add_argument("--out-md", help="write the report here (default: print it)")
    ap.add_argument("--json-out", help="write the findings as JSON")
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--user-agent", default=pk.DEFAULT_UA)
    ap.add_argument("--no-probe", action="store_true", help="skip the crawler user-agent requests")
    a = ap.parse_args(argv)
    res = run(a.url, {"timeout": a.timeout, "user_agent": a.user_agent, "no_probe": a.no_probe})
    md = render_markdown(res)
    if a.out_md:
        with open(a.out_md, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Wrote {a.out_md}")
    else:
        print(md)
    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1)
    if a.badge:
        import datetime
        line = badge_markdown(res, datetime.date.today().isoformat())
        print("\nBadge (states a count for this page on this date, nothing more):\n" + line if line
              else "\nNo badge: there are blocking findings.")
    return 2 if res["counts"][BLOCKS] else 0


if __name__ == "__main__":
    sys.exit(main())

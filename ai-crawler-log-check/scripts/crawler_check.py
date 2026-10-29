#!/usr/bin/env python3
"""Check server or CDN access logs for AI and search crawler activity, and
verify each hit against the vendor's published IP ranges or reverse DNS
instead of trusting the user-agent string.

Standard library only. Python 3.8+.

Usage:
  python3 crawler_check.py access.log [more.log.gz ...]
      [--format auto|combined|csv] [--ranges-dir DIR] [--fetch-ranges]
      [--no-dns] [--out-md report.md] [--out-csv summary.csv]
      [--out-hits hits.csv] [--top N]

Verification statuses for each hit whose user agent claims a known crawler:
  verified      IP is inside the vendor's published ranges, or reverse DNS
                ends in a vendor domain and forward DNS resolves back to the IP.
  failed        A verification method exists and was run, and the IP did not
                pass it. Likely spoofed (or ranges are out of date).
  unverifiable  No published method, the range file is not available, or the
                method needs DNS and --no-dns was set. Not a pass, not a fail.
"""

import argparse
import csv
import gzip
import io
import ipaddress
import json
import os
import re
import socket
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Crawler families. Every entry was checked against the vendor's own
# documentation (URLs in references/crawlers.md). Range files are stored in
# --ranges-dir under the local name given here.
# ---------------------------------------------------------------------------

RANGE_SOURCES = {
    "openai-gptbot.json": "https://openai.com/gptbot.json",
    "openai-searchbot.json": "https://openai.com/searchbot.json",
    "openai-chatgpt-user.json": "https://openai.com/chatgpt-user.json",
    "openai-adsbot.json": "https://openai.com/adsbot.json",
    "anthropic-bots.json": "https://claude.com/crawling/bots.json",
    "perplexity-perplexitybot.json": "https://www.perplexity.ai/perplexitybot.json",
    "perplexity-user.json": "https://www.perplexity.ai/perplexity-user.json",
    "google-common-crawlers.json": "https://developers.google.com/static/crawling/ipranges/common-crawlers.json",
    "bing-bingbot.json": "https://www.bing.com/toolbox/bingbot.json",
    "apple-applebot.json": "https://search.developer.apple.com/applebot.json",
    "commoncrawl-ccbot.json": "https://index.commoncrawl.org/ccbot.json",
    # Meta publishes no JSON file. Its docs say to list routes announced by
    # AS32934 (whois). Build this file yourself; see references/crawlers.md.
    "meta-as32934.json": None,
}

# (family, vendor, purpose, ua regex, range files, rDNS suffixes)
# Order matters: first match wins, so specific tokens come before general ones.
FAMILIES = [
    ("GPTBot", "OpenAI", "training", r"GPTBot", ["openai-gptbot.json"], []),
    ("OAI-SearchBot", "OpenAI", "search", r"OAI-SearchBot", ["openai-searchbot.json"], []),
    ("ChatGPT-User", "OpenAI", "user-triggered fetch", r"ChatGPT-User", ["openai-chatgpt-user.json"], []),
    ("OAI-AdsBot", "OpenAI", "ad landing page review", r"OAI-AdsBot", ["openai-adsbot.json"], []),
    ("ClaudeBot", "Anthropic", "training", r"ClaudeBot", ["anthropic-bots.json"], []),
    ("Claude-SearchBot", "Anthropic", "search", r"Claude-SearchBot", ["anthropic-bots.json"], []),
    ("Claude-User", "Anthropic", "user-triggered fetch", r"Claude-User", ["anthropic-bots.json"], []),
    ("Perplexity-User", "Perplexity", "user-triggered fetch", r"Perplexity-User", ["perplexity-user.json"], []),
    ("PerplexityBot", "Perplexity", "search", r"PerplexityBot", ["perplexity-perplexitybot.json"], []),
    ("Google-CloudVertexBot", "Google", "site-owner-requested crawl (Vertex AI Agents)", r"Google-CloudVertexBot",
     ["google-common-crawlers.json"], [".googlebot.com", ".google.com", ".googleusercontent.com"]),
    ("GoogleOther", "Google", "generic crawler (research, product teams)", r"GoogleOther",
     ["google-common-crawlers.json"], [".googlebot.com", ".google.com", ".googleusercontent.com"]),
    ("Googlebot", "Google", "search", r"Googlebot",
     ["google-common-crawlers.json"], [".googlebot.com", ".google.com", ".googleusercontent.com"]),
    ("Bingbot", "Microsoft", "search", r"bingbot", ["bing-bingbot.json"], [".search.msn.com"]),
    ("Applebot", "Apple", "search", r"Applebot", ["apple-applebot.json"], [".applebot.apple.com"]),
    ("CCBot", "Common Crawl", "open web crawl archive", r"CCBot",
     ["commoncrawl-ccbot.json"], [".crawl.commoncrawl.org"]),
    ("Meta-ExternalAgent", "Meta", "training and indexing", r"meta-externalagent", ["meta-as32934.json"], []),
    ("Meta-ExternalFetcher", "Meta", "user-triggered fetch", r"meta-externalfetcher", ["meta-as32934.json"], []),
    ("Meta-WebIndexer", "Meta", "Meta AI search", r"meta-webindexer", ["meta-as32934.json"], []),
    ("Meta-ExternalAds", "Meta", "ads and business products", r"meta-externalads", ["meta-as32934.json"], []),
    ("FacebookExternalHit", "Meta", "link previews for shared URLs", r"facebookexternalhit", ["meta-as32934.json"], []),
    # No official ByteDance documentation was found. Matched by UA only and
    # always reported as unverifiable.
    ("Bytespider", "ByteDance", "not documented by vendor", r"Bytespider", [], []),
]

COMPILED = [(f, v, p, re.compile(rx, re.I), rf, dn) for f, v, p, rx, rf, dn in FAMILIES]
SPECIAL_PATHS = {"/robots.txt": "robots.txt", "/llms.txt": "llms.txt", "/llms-full.txt": "llms-full.txt"}

COMBINED_RE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<req>[^"]*)" (?P<status>\d{3}) \S+'
    r'(?: "(?P<ref>[^"]*)" "(?P<ua>[^"]*)")?'
)


def classify(ua):
    for fam, vendor, purpose, rx, rfiles, dns in COMPILED:
        if rx.search(ua or ""):
            return fam
    return None


FAMILY_INFO = {f[0]: f for f in FAMILIES}


# ---------------------------------------------------------------------------
# IP handling
# ---------------------------------------------------------------------------

def parse_ip(raw):
    """Return an ipaddress object or None. Handles [v6], zone ids, v4-mapped v6,
    and a trailing :port on IPv4."""
    if not raw:
        return None
    s = raw.strip().strip('"')
    if s.startswith("[") and "]" in s:
        s = s[1:s.index("]")]
    s = s.split("%", 1)[0]
    if s.count(":") == 1 and "." in s:  # 203.0.113.5:443
        s = s.split(":", 1)[0]
    try:
        ip = ipaddress.ip_address(s)
    except ValueError:
        return None
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip


def load_range_file(path):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    nets = []
    for entry in data.get("prefixes", []):
        for key in ("ipv4Prefix", "ipv6Prefix"):
            if key in entry:
                try:
                    nets.append(ipaddress.ip_network(entry[key], strict=False))
                except ValueError:
                    pass
    return {"nets": nets, "creationTime": data.get("creationTime"), "comment": data.get("_comment")}


def load_ranges(ranges_dir):
    loaded = {}
    if not ranges_dir or not os.path.isdir(ranges_dir):
        return loaded
    for name in RANGE_SOURCES:
        p = os.path.join(ranges_dir, name)
        if os.path.isfile(p):
            try:
                loaded[name] = load_range_file(p)
            except (OSError, ValueError) as exc:
                print(f"warning: could not read {p}: {exc}", file=sys.stderr)
    return loaded


def fetch_ranges(ranges_dir, timeout=20):
    os.makedirs(ranges_dir, exist_ok=True)
    results = {}
    for name, url in RANGE_SOURCES.items():
        if not url:
            continue
        req = urllib.request.Request(url, headers={"User-Agent": "ai-crawler-log-check/1.0 (range fetch)"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
            json.loads(body.decode("utf-8"))  # must be valid JSON
            with open(os.path.join(ranges_dir, name), "wb") as fh:
                fh.write(body)
            results[name] = "ok"
        except Exception as exc:  # network, HTTP, decode
            results[name] = f"failed ({exc.__class__.__name__}: {exc})"
            print(f"warning: could not fetch {url}: {exc}", file=sys.stderr)
    return results


# ---------------------------------------------------------------------------
# DNS verification (reverse lookup, then forward confirm)
# ---------------------------------------------------------------------------

_dns_cache = {}


def rdns_verify(ip, suffixes):
    """Return ('verified'|'failed'|'unverifiable', detail)."""
    key = (str(ip), tuple(suffixes))
    if key in _dns_cache:
        return _dns_cache[key]
    try:
        host = socket.gethostbyaddr(str(ip))[0].rstrip(".").lower()
    except socket.herror:
        res = ("failed", "no PTR record")
    except (socket.gaierror, socket.timeout, OSError) as exc:
        res = ("unverifiable", f"reverse DNS error: {exc}")
    else:
        if not any(host.endswith(s) for s in suffixes):
            res = ("failed", f"PTR {host} not in {', '.join(suffixes)}")
        else:
            try:
                infos = socket.getaddrinfo(host, None)
                addrs = {parse_ip(i[4][0]) for i in infos}
            except socket.gaierror:
                res = ("failed", f"PTR {host} does not resolve forward")
            except (socket.timeout, OSError) as exc:
                res = ("unverifiable", f"forward DNS error: {exc}")
            else:
                if ip in addrs:
                    res = ("verified", f"rDNS {host} forward-confirmed")
                else:
                    res = ("failed", f"PTR {host} resolves to other addresses")
    _dns_cache[key] = res
    return res


def verify(ip, family, ranges, use_dns):
    _, _, _, _, rfiles, suffixes = FAMILY_INFO[family]
    have_ranges = [r for r in rfiles if r in ranges]
    if ip is not None:
        for r in have_ranges:
            if any(ip in n for n in ranges[r]["nets"]):
                return "verified", f"in {r}"
    if ip is None:
        return "unverifiable", "unparseable IP"
    if suffixes and use_dns:
        status, detail = rdns_verify(ip, suffixes)
        if status == "failed" and have_ranges:
            detail += f"; not in {', '.join(have_ranges)}"
        return status, detail
    if have_ranges:
        return "failed", f"not in {', '.join(have_ranges)}"
    if not rfiles and not suffixes:
        return "unverifiable", "vendor publishes no verification method"
    if suffixes and not use_dns:
        return "unverifiable", "range file missing and --no-dns set"
    if any(RANGE_SOURCES.get(r) is None for r in rfiles):
        return "unverifiable", "no published range file; build " + rfiles[0] + " from the vendor's ASN routes"
    return "unverifiable", "range file not available (use --fetch-ranges)"


# ---------------------------------------------------------------------------
# Log parsing
# ---------------------------------------------------------------------------

def open_text(path):
    with open(path, "rb") as fh:
        magic = fh.read(2)
    if magic == b"\x1f\x8b":
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def parse_ts(value):
    v = (value or "").strip()
    if not v:
        return None
    for fmt in ("%d/%b/%Y:%H:%M:%S %z",):
        try:
            return datetime.strptime(v, fmt).astimezone(timezone.utc)
        except ValueError:
            pass
    if re.fullmatch(r"\d{10}(\.\d+)?", v):
        return datetime.fromtimestamp(float(v), tz=timezone.utc)
    if re.fullmatch(r"\d{13}", v):  # epoch milliseconds
        return datetime.fromtimestamp(int(v) / 1000, tz=timezone.utc)
    if re.fullmatch(r"\d{19}", v):  # epoch nanoseconds
        return datetime.fromtimestamp(int(v) / 1e9, tz=timezone.utc)
    try:
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def clean_path(p):
    p = (p or "").split("?", 1)[0].split("#", 1)[0]
    if p.startswith("http://") or p.startswith("https://"):
        m = re.match(r"https?://[^/]+(/.*)?", p)
        p = (m.group(1) if m else "") or "/"
    return p or "/"


def iter_combined(fh, stats):
    for n, line in enumerate(fh, 1):
        line = line.rstrip("\r\n")
        if not line.strip() or line.startswith("#"):
            continue
        stats["lines"] += 1
        m = COMBINED_RE.match(line)
        if not m:
            stats["malformed"] += 1
            if len(stats["malformed_examples"]) < 5:
                stats["malformed_examples"].append(n)
            continue
        parts = m.group("req").split()
        method, path = (parts[0], parts[1]) if len(parts) >= 2 else ("-", "-")
        yield {"ip": m.group("ip"), "ts": m.group("ts"), "method": method, "path": path,
               "status": m.group("status"), "ua": m.group("ua") or ""}


CSV_COLS = ["timestamp", "ip", "method", "path", "status", "user_agent"]


def iter_csv(fh, stats):
    reader = csv.reader(fh)
    header = None
    for n, row in enumerate(reader, 1):
        if not row or (len(row) == 1 and not row[0].strip()) or row[0].startswith("#"):
            continue
        if header is None:
            header = [h.strip().lower() for h in row]
            missing = [c for c in CSV_COLS if c not in header]
            if missing:
                raise SystemExit(f"CSV header is missing columns: {', '.join(missing)}. "
                                 f"Expected: {','.join(CSV_COLS)}")
            idx = {c: header.index(c) for c in CSV_COLS}
            continue
        stats["lines"] += 1
        if len(row) < len(header):
            stats["malformed"] += 1
            if len(stats["malformed_examples"]) < 5:
                stats["malformed_examples"].append(n)
            continue
        yield {"ip": row[idx["ip"]], "ts": row[idx["timestamp"]], "method": row[idx["method"]],
               "path": row[idx["path"]], "status": row[idx["status"]], "ua": row[idx["user_agent"]]}


def detect_format(path):
    with open_text(path) as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            low = s.lower()
            if "user_agent" in low and "timestamp" in low:
                return "csv"
            return "combined"
    return "combined"


# ---------------------------------------------------------------------------
# Analysis and reporting
# ---------------------------------------------------------------------------

def analyze(paths, fmt, ranges, use_dns, top_n=5):
    stats = {"lines": 0, "malformed": 0, "malformed_examples": [], "crawler_hits": 0, "files": []}
    fam = defaultdict(lambda: {
        "hits": 0, "verified": 0, "failed": 0, "unverifiable": 0,
        "first": None, "last": None, "paths": Counter(), "status": Counter(),
        "special": Counter(), "special_verified": Counter(), "failed_ips": Counter(),
        "reasons": Counter(),
    })
    hits = []
    for path in paths:
        f = fmt if fmt != "auto" else detect_format(path)
        stats["files"].append((path, f))
        with open_text(path) as fh:
            it = iter_csv(fh, stats) if f == "csv" else iter_combined(fh, stats)
            for rec in it:
                family = classify(rec["ua"])
                if not family:
                    continue
                stats["crawler_hits"] += 1
                ip = parse_ip(rec["ip"])
                status, detail = verify(ip, family, ranges, use_dns)
                d = fam[family]
                d["hits"] += 1
                d[status] += 1
                d["reasons"][detail if status != "verified" else "verified"] += 1
                ts = parse_ts(rec["ts"])
                if ts:
                    d["first"] = ts if d["first"] is None or ts < d["first"] else d["first"]
                    d["last"] = ts if d["last"] is None or ts > d["last"] else d["last"]
                p = clean_path(rec["path"])
                d["paths"][p] += 1
                d["status"][rec["status"]] += 1
                if p in SPECIAL_PATHS:
                    d["special"][SPECIAL_PATHS[p]] += 1
                    if status == "verified":
                        d["special_verified"][SPECIAL_PATHS[p]] += 1
                if status == "failed":
                    d["failed_ips"][str(ip) if ip else rec["ip"]] += 1
                hits.append({"timestamp": ts.isoformat() if ts else rec["ts"], "ip": rec["ip"],
                             "family": family, "vendor": FAMILY_INFO[family][1], "path": p,
                             "status": rec["status"], "verification": status, "detail": detail,
                             "user_agent": rec["ua"]})
    return stats, fam, hits


def fmt_dt(dt):
    return dt.strftime("%Y-%m-%d %H:%M UTC") if dt else "n/a"


def status_mix(counter):
    return ", ".join(f"{k}: {v}" for k, v in sorted(counter.items())) or "none"


def render_markdown(stats, fam, ranges, use_dns, top_n):
    out = []
    w = out.append
    w("# AI crawler log check\n")
    w("## Inputs\n")
    for p, f in stats["files"]:
        w(f"- `{os.path.basename(p)}` ({f})")
    w(f"- Log lines read: {stats['lines']}; malformed and skipped: {stats['malformed']}"
      + (f" (first at line {', '.join(map(str, stats['malformed_examples']))})" if stats["malformed_examples"] else ""))
    w(f"- Lines whose user agent matched a known crawler: {stats['crawler_hits']}")
    w(f"- DNS verification: {'on' if use_dns else 'off (--no-dns)'}")
    if ranges:
        w("- Range files loaded:")
        for name, r in sorted(ranges.items()):
            note = f", note: {r['comment'].split('.')[0]}" if r.get("comment") else ""
            w(f"  - `{name}`: {len(r['nets'])} prefixes, creationTime {r.get('creationTime') or 'n/a'}{note}")
    else:
        w("- Range files loaded: none")
    w("")
    if not fam:
        w("No crawler user agents found in these logs.\n")
        return "\n".join(out)

    w("## Summary by crawler\n")
    w("| Crawler | Vendor | Purpose | Hits | Verified | Failed (likely spoofed) | Unverifiable | First seen | Last seen |")
    w("|---|---|---|---|---|---|---|---|---|")
    for name in sorted(fam, key=lambda k: -fam[k]["hits"]):
        d = fam[name]
        info = FAMILY_INFO[name]
        w(f"| {name} | {info[1]} | {info[2]} | {d['hits']} | {d['verified']} | {d['failed']} | "
          f"{d['unverifiable']} | {fmt_dt(d['first'])} | {fmt_dt(d['last'])} |")
    w("")
    w("## Detail\n")
    for name in sorted(fam, key=lambda k: -fam[k]["hits"]):
        d = fam[name]
        w(f"### {name}\n")
        w(f"- Status codes (all hits): {status_mix(d['status'])}")
        sp = ", ".join(f"{k} {v} (verified {d['special_verified'][k]})" for k, v in sorted(d["special"].items()))
        w(f"- robots.txt / llms.txt fetches: {sp or 'none'}")
        w(f"- Top paths: " + "; ".join(f"`{p}` {c}" for p, c in d["paths"].most_common(top_n)))
        reasons = [(r, c) for r, c in d["reasons"].most_common() if r != "verified"]
        if reasons:
            w(f"- Why not verified: " + "; ".join(f"{r} ({c})" for r, c in reasons))
        if d["failed_ips"]:
            w(f"- Top IPs that failed verification: " +
              ", ".join(f"{ip} ({c})" for ip, c in d["failed_ips"].most_common(top_n)))
        w("")
    w("## What this report cannot show\n")
    w("- A failed check means the IP was not in the vendor's published list (or failed reverse DNS) "
      "when checked. Range files change; a stale cached file can fail genuine traffic.")
    w("- Unverifiable is not the same as genuine. These hits are counted by user agent only.")
    w("- Crawling is not citation. These logs show fetches, not whether any AI answer used the page.")
    w("- If the logs come from an origin server behind a CDN or proxy, the IP may be the proxy's, "
      "and every check will fail. Log the real client IP.")
    return "\n".join(out) + "\n"


SUMMARY_COLS = ["crawler", "vendor", "purpose", "hits", "verified", "failed", "unverifiable",
                "first_seen", "last_seen", "robots_txt", "llms_txt", "status_2xx", "status_3xx",
                "status_4xx", "status_5xx"]


def write_summary_csv(path, fam):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(SUMMARY_COLS)
        for name in sorted(fam, key=lambda k: -fam[k]["hits"]):
            d = fam[name]
            info = FAMILY_INFO[name]
            sc = Counter()
            for code, c in d["status"].items():
                sc[code[:1] + "xx"] += c
            wr.writerow([name, info[1], info[2], d["hits"], d["verified"], d["failed"], d["unverifiable"],
                         d["first"].isoformat() if d["first"] else "", d["last"].isoformat() if d["last"] else "",
                         d["special"]["robots.txt"], d["special"]["llms.txt"],
                         sc["2xx"], sc["3xx"], sc["4xx"], sc["5xx"]])


def write_hits_csv(path, hits):
    cols = ["timestamp", "ip", "family", "vendor", "path", "status", "verification", "detail", "user_agent"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=cols)
        wr.writeheader()
        wr.writerows(hits)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="+", help="log files (.gz is detected automatically)")
    ap.add_argument("--format", choices=["auto", "combined", "csv"], default="auto")
    ap.add_argument("--ranges-dir", default="ranges", help="folder of cached range JSON files")
    ap.add_argument("--fetch-ranges", action="store_true", help="download vendor range files into --ranges-dir first")
    ap.add_argument("--no-dns", action="store_true", help="skip reverse/forward DNS checks")
    ap.add_argument("--dns-timeout", type=float, default=3.0)
    ap.add_argument("--out-md", help="write markdown report here (default: stdout)")
    ap.add_argument("--out-csv", help="write per-crawler summary CSV here")
    ap.add_argument("--out-hits", help="write one CSV row per crawler hit here")
    ap.add_argument("--top", type=int, default=5)
    args = ap.parse_args(argv)

    for p in args.logs:
        if not os.path.isfile(p):
            ap.error(f"no such file: {p}")
    if args.fetch_ranges:
        for name, res in fetch_ranges(args.ranges_dir).items():
            print(f"range fetch {name}: {res}", file=sys.stderr)
    socket.setdefaulttimeout(args.dns_timeout)
    ranges = load_ranges(args.ranges_dir)
    use_dns = not args.no_dns
    stats, fam, hits = analyze(args.logs, args.format, ranges, use_dns, args.top)
    md = render_markdown(stats, fam, ranges, use_dns, args.top)
    if args.out_md:
        with open(args.out_md, "w", encoding="utf-8") as fh:
            fh.write(md)
    else:
        sys.stdout.write(md)
    if args.out_csv:
        write_summary_csv(args.out_csv, fam)
    if args.out_hits:
        write_hits_csv(args.out_hits, hits)
    return 0


if __name__ == "__main__":
    sys.exit(main())

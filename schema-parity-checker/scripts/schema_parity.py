#!/usr/bin/env python3
"""schema_parity.py: check that a page's structured data says only what the visible page says.

Usage:
  python3 schema_parity.py https://example.com/page
  python3 schema_parity.py saved-page.html --base-url https://example.com/page
  python3 schema_parity.py URL --render          # also render with Playwright, if installed
  python3 schema_parity.py URL --check-links     # HEAD request sameAs and logo URLs
  python3 schema_parity.py URL --json            # machine-readable output

Standard library only. Playwright is optional (--render) and the script carries on
without it. Reads raw HTML, never a Markdown or text conversion.
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pagekit as pk  # noqa: E402

MATCH = 0.90     # at or above: treated as the same text
CHANGED = 0.60   # between CHANGED and MATCH: reported as changed wording

ORG_TYPES = {"Organization", "Corporation", "LocalBusiness", "NGO", "OnlineBusiness",
             "OnlineStore", "EducationalOrganization", "MedicalOrganization", "Store",
             "Restaurant", "Dentist", "Physician", "LegalService", "Attorney",
             "ProfessionalService", "HomeAndConstructionBusiness", "Plumber", "Electrician",
             "AutoRepair", "HealthAndBeautyBusiness", "FinancialService", "AccountingService",
             "RealEstateAgent", "TravelAgency", "FoodEstablishment", "CafeOrCoffeeShop",
             "BikeStore", "SportingGoodsStore", "LodgingBusiness", "Hotel"}
ARTICLE_TYPES = {"Article", "NewsArticle", "BlogPosting", "TechArticle", "Report",
                 "ScholarlyArticle", "SocialMediaPosting", "LiveBlogPosting"}
PRODUCT_TYPES = {"Product", "ProductGroup", "IndividualProduct", "Vehicle", "SoftwareApplication"}
CURRENCY_SYMBOLS = {"USD": ["$", "usd", "us$"], "EUR": ["€", "eur"], "GBP": ["£", "gbp"],
                    "CAD": ["$", "cad", "c$"], "AUD": ["$", "aud", "a$"], "JPY": ["¥", "jpy", "yen"],
                    "INR": ["₹", "inr", "rs"], "ZAR": ["r", "zar"], "CHF": ["chf"],
                    "SEK": ["kr", "sek"], "NZD": ["$", "nzd", "nz$"]}
IN_STOCK_WORDS = ["in stock", "available now", "ships today", "limited stock", "low stock", "only a few left"]
OUT_WORDS = ["out of stock", "sold out", "currently unavailable", "discontinued", "no longer available"]
AVAILABILITY = {  # schema value -> (words that confirm it, words that contradict it)
    "InStock": (IN_STOCK_WORDS, OUT_WORDS),
    "LimitedAvailability": (IN_STOCK_WORDS, OUT_WORDS),
    "OnlineOnly": (IN_STOCK_WORDS + ["online only"], OUT_WORDS),
    "InStoreOnly": (["in store only", "in-store only"], OUT_WORDS),
    "OutOfStock": (OUT_WORDS, ["in stock", "available now", "ships today"]),
    "SoldOut": (OUT_WORDS, ["in stock", "available now", "ships today"]),
    "Discontinued": (OUT_WORDS, ["in stock", "available now", "ships today"]),
    "PreOrder": (["pre-order", "preorder", "pre order"], OUT_WORDS),
    "BackOrder": (["backorder", "back order", "back-order"], []),
}
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                       "august", "september", "october", "november", "december"], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
MONTHS["sept"] = 9


class Report:
    def __init__(self):
        self.findings = []
        self.ok = []

    def add(self, severity, schema_type, field, issue, schema_value="", page_evidence="", score=None):
        self.findings.append({"severity": severity, "type": schema_type, "field": field,
                              "issue": issue, "schema_value": _short(schema_value),
                              "page_evidence": _short(page_evidence),
                              "score": None if score is None else round(score, 2)})

    def good(self, schema_type, field, value, how):
        self.ok.append({"type": schema_type, "field": field, "value": _short(value), "how": how})


def _short(v, n=220):
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False) if v not in (None, "") else ""
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[:n - 3] + "..."


def first(v):
    if isinstance(v, list):
        return v[0] if v else None
    return v


def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def text_of(v):
    """Text value of a schema property that may be a string, a dict with name/text, or a list."""
    v = first(v)
    if isinstance(v, dict):
        return str(v.get("text") or v.get("name") or v.get("@value") or "")
    return "" if v is None else str(v)


class Page:
    def __init__(self, parsed):
        self.p = parsed
        self.visible = parsed["visible_text"]
        self.boiler = parsed["boilerplate_text"]
        self.hidden = parsed["hidden_text"]

    def locate(self, value):
        """Where does this text appear? Returns (where, score, snippet)."""
        best = ("missing", 0.0, "")
        for where, text in (("visible", self.visible), ("navigation/header/footer", self.boiler),
                            ("hidden element", self.hidden)):
            if not text:
                continue
            score, snip = pk.find_in_text(value, text)
            if score >= MATCH:
                return where, score, snip
            if score > best[1]:
                best = (where if score >= CHANGED else "missing", score, snip)
        return best

    def all_text(self):
        return "\n".join([self.visible, self.boiler])


def check_text(rep, page, stype, field, value, missing_sev="high"):
    if not value or not str(value).strip():
        return
    where, score, snip = page.locate(value)
    if score >= MATCH and where == "visible":
        rep.good(stype, field, value, "found on page" if score == 1.0 else f"found (ratio {score:.2f})")
    elif score >= MATCH and where.startswith("navigation"):
        rep.good(stype, field, value, "found in navigation/header/footer")
    elif score >= MATCH and where == "hidden element":
        rep.add("high", stype, field, "Text is only in a hidden element (hidden, aria-hidden or display:none)",
                value, snip, score)
    elif score >= CHANGED:
        page_nums = {n for n, _, _ in numbers_in(page.all_text())}
        lost = [str(int(n) if n.is_integer() else n) for n, _, _ in numbers_in(pk.strip_tags(str(value)))
                if n not in page_nums]
        if lost:
            rep.add("high", stype, field, "Wording differs and the schema has numbers the page does not show: "
                    + ", ".join(lost), value, snip, score)
        else:
            rep.add("medium", stype, field, "Wording differs from the page", value, snip, score)
    else:
        rep.add(missing_sev, stype, field, "Not found on the visible page", value,
                snip if score > 0.3 else "", score)


# ---- numbers ---------------------------------------------------------------------

def numbers_in(text):
    out = []
    for m in re.finditer(r"(?<![\w.])(\d{1,3}(?:[,\u00a0 ]\d{3})+|\d+)(?:[.,](\d+))?(?![\w])", text):
        whole = re.sub(r"[,\u00a0 ]", "", m.group(1))
        frac = m.group(2)
        try:
            out.append((float(f"{whole}.{frac}") if frac else float(whole), m.start(), m.end()))
        except ValueError:
            pass
    return out


def to_float(v):
    try:
        return float(str(first(v)).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def check_number(rep, page, stype, field, value, sev="high", near_words=None):
    num = to_float(value)
    if num is None:
        if value not in (None, ""):
            rep.add("medium", stype, field, "Value is not a number", value)
        return None
    text = page.all_text()
    hits = [(n, s, e) for n, s, e in numbers_in(text) if abs(n - num) < 0.005]
    if hits:
        n, s, e = hits[0]
        ctx = text[max(0, s - 40):e + 40].replace("\n", " ")
        rep.good(stype, field, value, f"number found: ...{ctx.strip()}...")
        return hits
    hidden_hits = [h for h in numbers_in(page.hidden) if abs(h[0] - num) < 0.005]
    if hidden_hits:
        rep.add("high", stype, field, "Number only appears in a hidden element", value)
        return None
    nearby = ""
    if near_words:
        for w in near_words:
            i = text.lower().find(w)
            if i >= 0:
                nearby = text[max(0, i - 60):i + 80].replace("\n", " ")
                break
    rep.add(sev, stype, field, "Number not found on the visible page", value, nearby)
    return None


# ---- dates -----------------------------------------------------------------------

def parse_iso_date(v):
    s = str(first(v) or "").strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def visible_dates(page):
    found = {}
    for attr, txt in page.p["time_tags"]:
        d = parse_iso_date(attr) if attr else None
        if d and txt:
            found.setdefault(d, f"<time datetime={attr}> {txt}")
    text = page.all_text()
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        try:
            found.setdefault(date(int(m.group(1)), int(m.group(2)), int(m.group(3))), m.group(0))
        except ValueError:
            pass
    mon = "|".join(sorted(MONTHS, key=len, reverse=True))
    for m in re.finditer(rf"\b({mon})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", text, re.I):
        _add_date(found, m.group(3), MONTHS[m.group(1).lower()], m.group(2), m.group(0))
    for m in re.finditer(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({mon})\.?,?\s+(\d{{4}})\b", text, re.I):
        _add_date(found, m.group(3), MONTHS[m.group(2).lower()], m.group(1), m.group(0))
    return found


def _add_date(found, y, mth, d, raw):
    try:
        found.setdefault(date(int(y), int(mth), int(d)), raw)
    except ValueError:
        pass


# ---- per-type checks ---------------------------------------------------------------

def check_faq(rep, page, node):
    stype = "FAQPage"
    schema_qs = []
    for q in as_list(node.get("mainEntity")):
        if not isinstance(q, dict):
            continue
        qname = text_of(q.get("name"))
        ans = first(q.get("acceptedAnswer") or q.get("suggestedAnswer"))
        atext = text_of(ans.get("text")) if isinstance(ans, dict) else text_of(ans)
        schema_qs.append(qname)
        label = f"Question: {_short(qname, 70)}"
        check_text(rep, page, stype, label, qname)
        if atext:
            check_text(rep, page, stype, f"Answer to: {_short(qname, 70)}", atext)
        else:
            rep.add("medium", stype, label, "Question has no acceptedAnswer text in the schema", qname)
    if not schema_qs:
        rep.add("medium", stype, "mainEntity", "FAQPage has no Question items")
    # questions on the page that the schema does not include
    page_qs = []
    for tag, txt in page.p["headings"]:
        if txt.endswith("?") and 3 <= len(txt.split()) <= 40 and txt not in page_qs:
            page_qs.append(txt)
    for pq in page_qs:
        if not any(pk.ratio(pq, sq) >= CHANGED for sq in schema_qs):
            rep.add("low", stype, "page question", "Question-style heading on the page is not in the FAQPage schema "
                    "(fine if it is not part of the FAQ)", "", pq)


def check_offer(rep, page, offer, stype):
    if not isinstance(offer, dict):
        return
    otypes = pk.types_of(offer)
    if "AggregateOffer" in otypes:
        for f in ("lowPrice", "highPrice"):
            if offer.get(f) is not None:
                check_number(rep, page, stype, f"offers.{f}", offer[f], near_words=["price", "$", "€", "£"])
    price = offer.get("price")
    if price is None and isinstance(offer.get("priceSpecification"), dict):
        price = offer["priceSpecification"].get("price")
    if price is not None:
        hits = check_number(rep, page, stype, "offers.price", price, near_words=["price", "$", "€", "£"])
        cur = str(offer.get("priceCurrency") or "").upper()
        if cur:
            text = page.all_text()
            symbols = CURRENCY_SYMBOLS.get(cur, [cur.lower()])
            if hits:
                ctxs = [text[max(0, s - 6):e + 6].lower() for _, s, e in hits]
                if any(sym in c for c in ctxs for sym in symbols):
                    rep.good(stype, "offers.priceCurrency", cur, "currency marker next to the price")
                else:
                    other = [k for k, syms in CURRENCY_SYMBOLS.items() if k != cur
                             and any(sym in c for c in ctxs for sym in syms if len(sym) == 1 and sym not in symbols)]
                    if other:
                        rep.add("high", stype, "offers.priceCurrency", "Price on page shows a different currency marker",
                                cur, " | ".join(c.strip() for c in ctxs))
                    else:
                        rep.add("low", stype, "offers.priceCurrency", "No currency marker found next to the price",
                                cur, " | ".join(c.strip() for c in ctxs))
    avail = str(offer.get("availability") or "")
    if avail:
        key = avail.rstrip("/").split("/")[-1]
        low = page.all_text().lower()
        expected, against = AVAILABILITY.get(key, ([], []))
        # "in stock" is a substring of "out of stock": look for in-stock words only after removing out-of-stock phrases
        low_no_out = low
        for w in sorted(OUT_WORDS, key=len, reverse=True):
            low_no_out = low_no_out.replace(w, " ")
        has = lambda w: w in (low if w in OUT_WORDS else low_no_out)  # noqa: E731
        contrary = [w for w in against if has(w)]
        seen = [w for w in expected if has(w)]
        if contrary and not seen:
            rep.add("high", stype, "offers.availability", "Page wording contradicts the schema availability",
                    key, ", ".join(sorted(set(contrary))))
        elif contrary:
            rep.add("medium", stype, "offers.availability", "Page shows both matching and contradicting availability wording",
                    key, f"matching: {', '.join(seen)}; contradicting: {', '.join(sorted(set(contrary)))}")
        elif seen:
            rep.good(stype, "offers.availability", key, f"page says: {', '.join(seen)}")
        else:
            rep.add("low", stype, "offers.availability", "No availability wording found on the page to confirm it", key)


def check_rating(rep, page, rating, stype, prefix="aggregateRating"):
    if not isinstance(rating, dict):
        return
    if rating.get("ratingValue") is not None:
        check_number(rep, page, stype, f"{prefix}.ratingValue", rating["ratingValue"],
                     near_words=["rating", "stars", "out of"])
    for f in ("reviewCount", "ratingCount"):
        if rating.get(f) is not None:
            check_number(rep, page, stype, f"{prefix}.{f}", rating[f], near_words=["review", "rating"])


def check_product(rep, page, node):
    stype = "/".join(pk.types_of(node))
    check_text(rep, page, stype, "name", text_of(node.get("name")))
    for offer in as_list(node.get("offers")):
        check_offer(rep, page, offer, stype)
    if node.get("aggregateRating"):
        check_rating(rep, page, node["aggregateRating"], stype)
    for rv in as_list(node.get("review"))[:20]:
        check_review(rep, page, rv, stype + " > Review")


def check_review(rep, page, rv, stype="Review"):
    if not isinstance(rv, dict):
        return
    rr = rv.get("reviewRating")
    if isinstance(rr, dict) and rr.get("ratingValue") is not None:
        check_number(rep, page, stype, "reviewRating.ratingValue", rr["ratingValue"], sev="medium")
    author = text_of(rv.get("author"))
    if author:
        check_text(rep, page, stype, "author", author, missing_sev="medium")
    body = text_of(rv.get("reviewBody"))
    if body:
        check_text(rep, page, stype, "reviewBody", body)


def digits(s):
    return re.sub(r"\D", "", s or "")


def check_org(rep, page, node, base_url, check_links, timeout):
    stype = "/".join(pk.types_of(node))
    check_text(rep, page, stype, "name", text_of(node.get("name")))
    tel = text_of(node.get("telephone"))
    if tel:
        want = digits(tel)
        text = page.all_text()
        cands = [digits(m.group(0)) for m in re.finditer(r"[+(]?\d[\d\s().\-]{5,}\d", text)]
        tail = want[-9:] if len(want) >= 9 else want
        if any(c and (c == want or c.endswith(tail) or want.endswith(c[-9:] if len(c) >= 9 else c + "x"))
               for c in cands):
            rep.good(stype, "telephone", tel, "digits match a phone number on the page")
        elif any(digits(t).endswith(tail) for t in page.p["tel_links"]):
            shown = sorted(set(c for c in cands if 7 <= len(c) <= 15))
            if shown:
                rep.add("high", stype, "telephone", "Matches a tel: link, but the number shown on the page is different",
                        tel, f"tel: links: {', '.join(page.p['tel_links'])}; numbers shown: {', '.join(shown)}")
            else:
                rep.add("medium", stype, "telephone", "Number is only in a tel: link, not in visible text", tel,
                        ", ".join(page.p["tel_links"]))
        else:
            rep.add("high", stype, "telephone", "Phone number not found on the page", tel,
                    ", ".join(sorted(set(c for c in cands if 7 <= len(c) <= 15)))[:200])
    for addr in as_list(node.get("address")):
        if isinstance(addr, dict):
            for f in ("streetAddress", "addressLocality", "addressRegion", "postalCode"):
                if addr.get(f):
                    check_text(rep, page, stype, f"address.{f}", text_of(addr.get(f)),
                               missing_sev="high" if f in ("streetAddress", "postalCode") else "medium")
        elif isinstance(addr, str):
            check_text(rep, page, stype, "address", addr)
    if node.get("aggregateRating"):
        check_rating(rep, page, node["aggregateRating"], stype)
    links = [("sameAs", u) for u in as_list(node.get("sameAs")) if isinstance(u, str)]
    logo = node.get("logo")
    logo_url = text_of(logo.get("url") if isinstance(logo, dict) else logo) if logo else ""
    if logo_url:
        links.append(("logo", logo_url))
    for field, u in links:
        absu = urllib.parse.urljoin(base_url, u) if base_url else u
        if not pk.looks_like_url(absu):
            rep.add("low", stype, field, "Relative URL and no base URL given, not checked (use --base-url)", u)
            continue
        if not check_links:
            continue
        r = pk.fetch(absu, method="HEAD", timeout=timeout)
        if r["status"] in (405, 501) or (r["status"] == 403 and not r["error"]):
            r = pk.fetch(absu, method="GET", timeout=timeout)
        if r["error"]:
            rep.add("medium", stype, field, f"URL did not respond ({r['error']})", absu)
        elif r["status"] and r["status"] >= 400:
            rep.add("medium", stype, field, f"URL returns HTTP {r['status']}", absu, r["final_url"])
        else:
            rep.good(stype, field, absu, f"HTTP {r['status']}" + (f" after {len(r['hops'])} redirect(s)" if r["hops"] else ""))


def check_article(rep, page, node):
    stype = "/".join(pk.types_of(node))
    headline = text_of(node.get("headline") or node.get("name"))
    if headline:
        cands = [("h1", h) for h in page.p["h1"]] + [("title", page.p["title"])]
        scored = sorted(((pk.ratio(headline, c), w, c) for w, c in cands if c), reverse=True)
        nh = pk.norm(headline)
        contained = [(w, c) for w, c in cands if c and (nh in pk.norm(c) or (pk.norm(c) and pk.norm(c) in nh))]
        if contained:
            rep.good(stype, "headline", headline, f"matches {contained[0][0]}: {contained[0][1]}")
        elif scored and scored[0][0] >= 0.8:
            rep.add("medium", stype, "headline", f"Close to the {scored[0][1]} but not the same", headline, scored[0][2], scored[0][0])
        else:
            where, score, snip = page.locate(headline)
            shown = " | ".join(f"{w}: {c}" for w, c in cands if c)
            if score >= MATCH and where != "hidden element":
                rep.add("medium", stype, "headline", "Headline is on the page but is not the h1 or the title",
                        headline, shown, scored[0][0] if scored else 0)
            else:
                rep.add("high", stype, "headline", "Headline does not match the h1 or the title and is not on the page",
                        headline, shown, scored[0][0] if scored else 0)
    vdates = visible_dates(page)
    for f in ("datePublished", "dateModified"):
        if not node.get(f):
            continue
        d = parse_iso_date(node[f])
        if not d:
            rep.add("medium", stype, f, "Date is not in ISO 8601 form (YYYY-MM-DD...)", node[f])
            continue
        if d in vdates:
            rep.good(stype, f, node[f], f"page shows {vdates[d]}")
        elif not vdates:
            rep.add("medium", stype, f, "No date is shown on the page at all", node[f])
        else:
            rep.add("high" if f == "datePublished" else "medium", stype, f, "Date not shown on the page",
                    node[f], "dates on page: " + ", ".join(f"{k.isoformat()} ({v})" for k, v in sorted(vdates.items())[:6]))
    for a in as_list(node.get("author")):
        name = text_of(a)
        if name:
            check_text(rep, page, stype, "author", name, missing_sev="medium")


# ---- rendering ---------------------------------------------------------------------

def render_html(url_or_path, timeout):
    """Return (html, note). html is None when rendering is not possible."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, "Playwright is not installed (pip install playwright && playwright install chromium); used raw HTML only"
    target = url_or_path if pk.looks_like_url(url_or_path) else "file://" + os.path.abspath(url_or_path)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            pg = browser.new_page()
            pg.goto(target, wait_until="networkidle", timeout=timeout * 1000)
            content = pg.content()
            browser.close()
            return content, "rendered with Playwright (Chromium)"
    except Exception as e:
        return None, f"Rendering failed ({type(e).__name__}: {e}); used raw HTML only"


# ---- main --------------------------------------------------------------------------

def analyze(text, base_url, check_links, timeout):
    parsed = pk.parse_page(text)
    page = Page(parsed)
    rep = Report()
    checked = []
    for node in parsed["jsonld_nodes"]:
        types = set(pk.types_of(node))
        if "FAQPage" in types:
            check_faq(rep, page, node); checked.append("FAQPage")
        if types & PRODUCT_TYPES:
            check_product(rep, page, node); checked.append("/".join(types))
        if types & ORG_TYPES or (types and not types & (PRODUCT_TYPES | ARTICLE_TYPES | {"Person", "PostalAddress", "WebSite", "WebPage", "Place"})
                                  and ("telephone" in node or "address" in node) and node.get("__top__")):
            check_org(rep, page, node, base_url, check_links, timeout); checked.append("/".join(types))
        if types & ARTICLE_TYPES:
            check_article(rep, page, node); checked.append("/".join(types))
        if "Review" in types and node.get("__top__"):
            check_review(rep, page, node); checked.append("Review")
        if "AggregateRating" in types and node.get("__top__"):
            check_rating(rep, page, node, "AggregateRating", prefix="AggregateRating"); checked.append("AggregateRating")
    return parsed, rep, checked


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check structured data against the visible page.")
    ap.add_argument("source", help="URL or path to a saved raw .html file")
    ap.add_argument("--base-url", help="page URL, for resolving relative logo/sameAs URLs when reading a file")
    ap.add_argument("--render", action="store_true", help="also render with Playwright (optional dependency)")
    ap.add_argument("--check-links", action="store_true", help="request each sameAs and logo URL")
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--user-agent", default=pk.DEFAULT_UA)
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = ap.parse_args(argv)

    try:
        raw, info = pk.load_html(args.source, timeout=args.timeout, user_agent=args.user_agent)
    except OSError as e:
        print(f"Could not read {args.source}: {e}", file=sys.stderr)
        return 2
    if info.get("error"):
        print(f"Could not fetch {args.source}: {info['error']}", file=sys.stderr)
        return 2
    base = args.base_url or (info["final_url"] if pk.looks_like_url(info["final_url"]) else None)
    warnings = pk.input_warnings(raw)
    if info.get("status") and info["status"] >= 400:
        warnings.append(f"HTTP {info['status']} returned; results describe the error page.")

    parsed, rep, checked = analyze(raw, base, args.check_links, args.timeout)
    render_note, render_diff = None, None
    if args.render:
        rendered, render_note = render_html(args.source, args.timeout)
        if rendered:
            parsed_r, rep_r, checked_r = analyze(rendered, base, args.check_links, args.timeout)
            render_diff = {
                "raw_jsonld_types": parsed["jsonld_types"],
                "rendered_jsonld_types": parsed_r["jsonld_types"],
                "only_after_render": sorted(set(parsed_r["jsonld_types"]) - set(parsed["jsonld_types"])),
                "raw_word_count": parsed["word_count"],
                "rendered_word_count": parsed_r["word_count"],
            }
            if render_diff["only_after_render"]:
                warnings.append("Some JSON-LD only exists after JavaScript runs: " + ", ".join(render_diff["only_after_render"])
                                + ". Crawlers that do not render JavaScript will not see it.")
            # report on the rendered view (what a rendering crawler sees), raw view summarized above
            parsed, rep, checked = parsed_r, rep_r, checked_r
    for e in parsed["jsonld_errors"]:
        rep.add("high", "JSON-LD", "syntax", "Block cannot be parsed, so no tool can read it", e)
    if not parsed["jsonld_nodes"] and not parsed["jsonld_errors"]:
        if render_diff:
            warnings.append("No JSON-LD found in the raw or the rendered HTML.")
        else:
            warnings.append("No JSON-LD found in the raw HTML. If you expected some, it may be injected by JavaScript: "
                            "re-run with --render, or check Google's Rich Results Test (URL input), which renders the page.")

    sev_order = {"high": 0, "medium": 1, "low": 2}
    rep.findings.sort(key=lambda f: (sev_order.get(f["severity"], 9), f["type"], f["field"]))
    out = {
        "source": args.source, "final_url": info.get("final_url"), "http_status": info.get("status"),
        "view": "rendered" if render_diff else "raw HTML (no JavaScript)", "render_note": render_note,
        "render_diff": render_diff, "warnings": warnings,
        "jsonld_blocks": parsed["jsonld_blocks"], "jsonld_errors": parsed["jsonld_errors"],
        "jsonld_types": parsed["jsonld_types"], "checked": sorted(set(checked)),
        "microdata": {"items": parsed["microdata_items"], "types": parsed["microdata_types"]},
        "rdfa": {"attributes": parsed["rdfa_attrs"], "types": parsed["rdfa_types"]},
        "counts": {s: sum(1 for f in rep.findings if f["severity"] == s) for s in ("high", "medium", "low")},
        "confirmed": len(rep.ok), "findings": rep.findings, "confirmed_items": rep.ok,
    }
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
        return 0
    print_text(out)
    return 0


def print_text(o):
    print(f"Schema parity check: {o['source']}")
    if o["final_url"] and o["final_url"] != o["source"]:
        print(f"Final URL: {o['final_url']}")
    if o["http_status"]:
        print(f"HTTP status: {o['http_status']}")
    print(f"View checked: {o['view']}")
    if o["render_note"]:
        print(f"Render: {o['render_note']}")
    if o["render_diff"]:
        d = o["render_diff"]
        print(f"  raw JSON-LD types: {', '.join(d['raw_jsonld_types']) or 'none'}; rendered: {', '.join(d['rendered_jsonld_types']) or 'none'}")
        print(f"  words raw: {d['raw_word_count']}; rendered: {d['rendered_word_count']}")
    print(f"JSON-LD blocks: {o['jsonld_blocks']}; types: {', '.join(o['jsonld_types']) or 'none'}")
    for e in o["jsonld_errors"]:
        print(f"  JSON-LD error: {e}")
    print(f"Microdata items: {o['microdata']['items']}" + (f" ({', '.join(o['microdata']['types'])})" if o['microdata']['types'] else "")
          + f"; RDFa attributes: {o['rdfa']['attributes']}" + (f" ({', '.join(o['rdfa']['types'])})" if o['rdfa']['types'] else ""))
    if o["microdata"]["items"] or o["rdfa"]["attributes"]:
        print("  Note: microdata/RDFa presence is reported but not compared in this version.")
    print(f"Checked: {', '.join(o['checked']) or 'nothing (no supported types)'}")
    for w in o["warnings"]:
        print(f"WARNING: {w}")
    c = o["counts"]
    print(f"\nFindings: {c['high']} high, {c['medium']} medium, {c['low']} low. Confirmed on page: {o['confirmed']}.")
    for f in o["findings"]:
        print(f"\n[{f['severity'].upper()}] {f['type']} | {f['field']}")
        print(f"  {f['issue']}" + (f" (similarity {f['score']})" if f["score"] is not None and f["score"] < 1 else ""))
        if f["schema_value"]:
            print(f"  schema: \"{f['schema_value']}\"")
        if f["page_evidence"]:
            print(f"  page:   \"{f['page_evidence']}\"")
    if o["confirmed_items"]:
        print("\nConfirmed:")
        for g in o["confirmed_items"]:
            print(f"  ok  {g['type']} | {g['field']}: {g['how']}")


if __name__ == "__main__":
    sys.exit(main())

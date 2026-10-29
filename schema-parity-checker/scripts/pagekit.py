"""pagekit: small shared helper for fetching raw HTML and reading what is on a page.

Standard library only. The same file ships in more than one skill so that each
skill folder works on its own. If you change it, copy it to the other skills.

What it does:
  fetch(url)            raw HTTP fetch, follows redirects by hand so every hop is recorded
  load_html(source)     a URL or a saved .html file
  parse_page(html)      title, h1s, canonical, robots meta, JSON-LD blocks, microdata and
                        RDFa presence, visible text (script/style/nav removed), hidden text,
                        dates, question-like headings, word counts
  norm(text)            normalize whitespace, case, quotes and punctuation for comparison
  find_in_text(n, h)    exact-after-normalizing, then fuzzy (difflib) best window match
"""

import difflib
import gzip
import html
import json
import re
import ssl
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zlib
from html.parser import HTMLParser

DEFAULT_UA = "Mozilla/5.0 (compatible; pagekit/1.0; raw-html-check)"
MAX_HOPS = 10
MAX_BYTES = 8 * 1024 * 1024

VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
             "meta", "param", "source", "track", "wbr"}
SKIP_TAGS = {"script", "style", "template", "svg", "head", "iframe", "object", "canvas"}
BLOCK_TAGS = {"p", "div", "li", "ul", "ol", "dl", "dt", "dd", "h1", "h2", "h3", "h4", "h5",
              "h6", "section", "article", "main", "header", "footer", "nav", "aside", "tr",
              "td", "th", "table", "br", "summary", "details", "blockquote", "figcaption",
              "address", "form", "button", "label", "option", "pre", "hr", "time"}
BOILERPLATE_TAGS = {"nav", "header", "footer", "aside"}


# --------------------------------------------------------------------------- fetching

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _decode_body(raw, headers):
    enc = (headers.get("Content-Encoding") or "").lower()
    try:
        if "gzip" in enc:
            raw = gzip.decompress(raw)
        elif "deflate" in enc:
            raw = zlib.decompress(raw)
    except (OSError, zlib.error):
        pass
    ctype = headers.get("Content-Type") or ""
    m = re.search(r"charset=([\w.-]+)", ctype, re.I)
    charset = m.group(1) if m else None
    if not charset:
        m = re.search(rb'<meta[^>]+charset=["\']?([\w.-]+)', raw[:4096], re.I)
        charset = m.group(1).decode("ascii", "ignore") if m else "utf-8"
    try:
        return raw.decode(charset, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def fetch(url, method="GET", timeout=20, user_agent=DEFAULT_UA, follow=True, max_hops=MAX_HOPS):
    """Fetch a URL without letting urllib hide redirects.

    Returns a dict: url, final_url, status, headers (of the final response), body (str,
    '' for HEAD), hops (list of {url, status, location}), error (str or None).
    A 4xx/5xx is a normal result, not an exception.
    """
    opener = urllib.request.build_opener(_NoRedirect,
                                         urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    hops = []
    current = url
    seen = set()
    result = {"url": url, "final_url": url, "status": None, "headers": {}, "body": "",
              "hops": hops, "error": None}
    for _ in range(max_hops + 1):
        req = urllib.request.Request(current, method=method, headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        })
        try:
            resp = opener.open(req, timeout=timeout)
            status, headers = resp.status, resp.headers
            raw = resp.read(MAX_BYTES) if method != "HEAD" else b""
        except urllib.error.HTTPError as e:
            status, headers = e.code, e.headers
            try:
                raw = e.read(MAX_BYTES) if method != "HEAD" else b""
            except Exception:
                raw = b""
        except Exception as e:  # DNS, refused, timeout, TLS
            result["error"] = f"{type(e).__name__}: {e}"
            result["final_url"] = current
            return result
        location = headers.get("Location")
        if status in (301, 302, 303, 307, 308) and location:
            nxt = urllib.parse.urljoin(current, location)
            hops.append({"url": current, "status": status, "location": nxt})
            if not follow:
                result.update(status=status, headers=dict(headers), final_url=current)
                return result
            if nxt in seen:
                result.update(status=status, headers=dict(headers), final_url=nxt,
                              error="redirect loop")
                return result
            seen.add(current)
            current = nxt
            continue
        result.update(status=status, headers=dict(headers), final_url=current,
                      body=_decode_body(raw, headers) if raw else "")
        return result
    result["error"] = f"more than {max_hops} redirects"
    result["final_url"] = current
    return result


def looks_like_url(s):
    return bool(re.match(r"^https?://", (s or "").strip(), re.I))


def load_html(source, timeout=20, user_agent=DEFAULT_UA):
    """Return (html_text, info) for a URL or a local file path."""
    if looks_like_url(source):
        r = fetch(source, timeout=timeout, user_agent=user_agent)
        return r["body"], r
    with open(source, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    return text, {"url": source, "final_url": source, "status": None, "headers": {},
                  "hops": [], "error": None, "file": True}


def input_warnings(text):
    """Spot inputs that are not raw HTML (for example a Markdown conversion)."""
    warnings = []
    if not text.strip():
        warnings.append("Input is empty.")
        return warnings
    low = text[:200000].lower()
    if "<html" not in low and "<body" not in low and "<head" not in low:
        warnings.append("Input has no <html>, <head> or <body> tag. It may be converted text "
                        "(for example Markdown from a fetch tool) rather than raw HTML. "
                        "Structured data in <script> tags is lost in that conversion.")
    elif "<script" not in low:
        warnings.append("Input has no <script> tags at all. Either the page has no JSON-LD or "
                        "the tool that saved it stripped scripts. Re-save the raw HTML "
                        "(view-source or curl) if unsure.")
    return warnings


# --------------------------------------------------------------------------- parsing

def _is_hidden(attrs):
    a = dict(attrs)
    if "hidden" in a:
        return True
    if (a.get("aria-hidden") or "").lower() == "true":
        return True
    style = (a.get("style") or "").replace(" ", "").lower()
    return "display:none" in style or "visibility:hidden" in style


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []  # (tag, flags dict)
        self.title = ""
        self.h1 = []
        self.headings = []  # (tag, text)
        self.canonical = []
        self.robots_meta = {}
        self.refresh = None
        self.jsonld_raw = []
        self.microdata_types = []
        self.itemscope_count = 0
        self.rdfa_attrs = 0
        self.rdfa_types = []
        self.time_tags = []  # (datetime attr, text)
        self.tel_links = []
        self.visible = []
        self.boiler = []
        self.hidden = []
        self.main = []
        self._capture = None  # (kind, buffer)
        self._script_type = None
        self._script_buf = []
        self._time_attr = None
        self._time_buf = None
        self._has_main = False

    # flags of the current context
    def _ctx(self):
        f = {"skip": False, "boiler": False, "hidden": False, "main": False}
        for _, fl in self.stack:
            for k in f:
                f[k] = f[k] or fl.get(k, False)
        return f

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        # structured data presence
        if "itemscope" in a:
            self.itemscope_count += 1
            if a.get("itemtype"):
                self.microdata_types.extend(a["itemtype"].split())
        for k in ("vocab", "typeof", "property"):
            if k in a and not (tag == "meta" and k == "property"):  # og: meta tags are not RDFa use
                self.rdfa_attrs += 1
                if k == "typeof" and a[k]:
                    self.rdfa_types.extend(a[k].split())
        if tag == "meta":
            name = (a.get("name") or "").lower()
            if name in ("robots", "googlebot", "bingbot"):
                self.robots_meta[name] = (self.robots_meta.get(name, "") + "," + (a.get("content") or "")).strip(",")
            if (a.get("http-equiv") or "").lower() == "refresh":
                self.refresh = a.get("content")
        if tag == "link" and "canonical" in (a.get("rel") or "").lower().split():
            self.canonical.append(a.get("href") or "")
        if tag == "a" and (a.get("href") or "").lower().startswith("tel:"):
            self.tel_links.append(a["href"][4:])
        if tag in VOID_TAGS:
            if tag == "br":
                self._text("\n")
            return
        flags = {}
        if tag in SKIP_TAGS:
            flags["skip"] = True
        if tag in BOILERPLATE_TAGS:
            flags["boiler"] = True
        if _is_hidden(attrs):
            flags["hidden"] = True
        if tag in ("main", "article") or (a.get("role") or "").lower() == "main":
            flags["main"] = True
            self._has_main = True
        self.stack.append((tag, flags))
        if tag == "script":
            self._script_type = (a.get("type") or "").lower().strip()
            self._script_buf = []
        if tag == "title" and not self.title:
            self._capture = ("title", [])
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6", "summary", "dt", "button", "strong") and self._capture is None:
            self._capture = (tag, [])
        if tag == "time":
            self._time_attr = a.get("datetime")
            self._time_buf = []
        if tag in BLOCK_TAGS:
            self._text("\n")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if not any(t == tag for t, _ in self.stack):
            return
        if tag == "script":
            if self._script_type == "application/ld+json":
                self.jsonld_raw.append("".join(self._script_buf))
            self._script_type = None
        if self._capture and self._capture[0] == tag:
            text = re.sub(r"\s+", " ", "".join(self._capture[1])).strip()
            kind = self._capture[0]
            self._capture = None
            if kind == "title":
                self.title = text
            else:
                if kind == "h1":
                    self.h1.append(text)
                self.headings.append((kind, text))
        if tag == "time" and self._time_buf is not None:
            self.time_tags.append((self._time_attr, re.sub(r"\s+", " ", "".join(self._time_buf)).strip()))
            self._time_buf = None
        if tag in BLOCK_TAGS:
            self._text("\n")
        while self.stack:
            t, _ = self.stack.pop()
            if t == tag:
                break

    def _text(self, data):
        ctx = self._ctx()
        if ctx["skip"]:
            return
        if ctx["hidden"]:
            self.hidden.append(data)
        elif ctx["boiler"]:
            self.boiler.append(data)
        else:
            self.visible.append(data)
            if ctx["main"]:
                self.main.append(data)

    def handle_data(self, data):
        if self._script_type is not None:
            self._script_buf.append(data)
            return
        if self._capture is not None:
            self._capture[1].append(data)
        if self._time_buf is not None:
            self._time_buf.append(data)
        self._text(data)


def _clean_lines(parts):
    text = "".join(parts)
    lines = [re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def word_count(text):
    return len(re.findall(r"\w+", text or ""))


def parse_jsonld(raw_blocks):
    """Parse JSON-LD blocks. Returns (nodes, errors). nodes = every dict that has @type,
    found anywhere (top level, @graph, nested)."""
    nodes, errors = [], []
    for i, raw in enumerate(raw_blocks):
        s = raw.strip()
        s = re.sub(r"^\s*<!--|-->\s*$", "", s)
        s = re.sub(r"^\s*//\s*<!\[CDATA\[|//\s*\]\]>\s*$", "", s).strip()
        if not s:
            errors.append(f"block {i + 1}: empty")
            continue
        try:
            data = json.loads(s)
        except json.JSONDecodeError as e:
            errors.append(f"block {i + 1}: invalid JSON ({e.msg} at line {e.lineno} col {e.colno})")
            continue
        _collect(data, nodes, block=i + 1, top=True)
    return nodes, errors


def _collect(obj, out, block, top=False):
    if isinstance(obj, list):
        for x in obj:
            _collect(x, out, block, top)
    elif isinstance(obj, dict):
        if "@type" in obj:
            obj.setdefault("__block__", block)
            obj.setdefault("__top__", top)
            out.append(obj)
        for k, v in obj.items():
            if k.startswith("__"):
                continue
            _collect(v, out, block, top=(k == "@graph" and top))


def types_of(node):
    t = node.get("@type")
    if isinstance(t, list):
        return [str(x) for x in t]
    return [str(t)] if t else []


def parse_page(text):
    p = _PageParser()
    try:
        p.feed(text)
        p.close()
    except Exception as e:  # html.parser is forgiving; keep whatever was read
        p.visible.append(f"\n[parse stopped: {e}]\n")
    nodes, errors = parse_jsonld(p.jsonld_raw)
    visible = _clean_lines(p.visible)
    main = _clean_lines(p.main) if p._has_main else visible
    page = {
        "title": p.title,
        "h1": p.h1,
        "headings": p.headings,
        "canonical": p.canonical,
        "robots_meta": p.robots_meta,
        "meta_refresh": p.refresh,
        "jsonld_blocks": len(p.jsonld_raw),
        "jsonld_nodes": nodes,
        "jsonld_errors": errors,
        "jsonld_types": sorted({t for n in nodes if n.get("__top__") for t in types_of(n)}),
        "jsonld_types_all": sorted({t for n in nodes for t in types_of(n)}),
        "microdata_items": p.itemscope_count,
        "microdata_types": sorted(set(p.microdata_types)),
        "rdfa_attrs": p.rdfa_attrs,
        "rdfa_types": sorted(set(p.rdfa_types)),
        "time_tags": p.time_tags,
        "tel_links": p.tel_links,
        "visible_text": visible,
        "boilerplate_text": _clean_lines(p.boiler),
        "hidden_text": _clean_lines(p.hidden),
        "main_text": main,
        "word_count": word_count(visible) + word_count(_clean_lines(p.boiler)),
        "main_word_count": word_count(main),
    }
    return page


# --------------------------------------------------------------------------- comparing

_QUOTES = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-",
           "\u2014": "-", "\u00a0": " ", "\u2026": "..."}


def strip_tags(s):
    return re.sub(r"<[^>]+>", " ", html.unescape(s or ""))


def norm(s):
    s = unicodedata.normalize("NFKC", strip_tags(str(s)))
    for k, v in _QUOTES.items():
        s = s.replace(k, v)
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def ratio(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def find_in_text(needle, haystack):
    """Return (score, snippet). score 1.0 = found verbatim after normalizing.
    Otherwise the best difflib ratio over windows of the haystack the same length
    (in words) as the needle."""
    n = norm(needle)
    h = norm(haystack)
    if not n:
        return 0.0, ""
    if n in h:
        return 1.0, needle
    nt, ht = n.split(), h.split()
    if not ht:
        return 0.0, ""
    w = len(nt)
    if len(ht) <= w:
        return difflib.SequenceMatcher(None, n, h).ratio(), " ".join(ht)
    # 1) linear pass: word overlap (multiset) for every window of w words
    need = {}
    for t in nt:
        need[t] = need.get(t, 0) + 1
    win, overlap, scores = {}, 0, []
    for k, t in enumerate(ht):
        if t in need:
            if win.get(t, 0) < need[t]:
                overlap += 1
            win[t] = win.get(t, 0) + 1
        if k >= w:
            o = ht[k - w]
            if o in need:
                win[o] -= 1
                if win[o] < need[o]:
                    overlap -= 1
        if k >= w - 1:
            scores.append((overlap, k - w + 1))
    # 2) difflib only on the best few windows by overlap, spaced apart
    scores.sort(reverse=True)
    picked = []
    for ov, start in scores:
        if all(abs(start - q) >= max(1, w // 2) for q in picked):
            picked.append(start)
        if len(picked) >= 8:
            break
    best, best_i, w_best = 0.0, 0, w
    sm = difflib.SequenceMatcher(None, autojunk=False)
    sm.set_seq2(n)
    for start in picked:
        for i in range(max(0, start - 2), min(len(ht), start + 3)):
            for ww in (w - 1, w, w + 1, w + 2):
                if ww < 1 or i + ww > len(ht):
                    continue
                sm.set_seq1(" ".join(ht[i:i + ww]))
                if sm.real_quick_ratio() <= best or sm.quick_ratio() <= best:
                    continue
                r = sm.ratio()
                if r > best:
                    best, best_i, w_best = r, i, ww
    return best, " ".join(ht[best_i:best_i + w_best])


def title_similarity(a, b):
    """max of difflib ratio and word overlap (Jaccard), both on normalized text."""
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    sa, sb = set(na.split()), set(nb.split())
    jac = len(sa & sb) / len(sa | sb)
    return max(difflib.SequenceMatcher(None, na, nb).ratio(), jac)


def norm_url(u):
    """Lowercase scheme and host, drop fragment and default port. Path is kept as is
    except that an empty path becomes '/'."""
    try:
        p = urllib.parse.urlsplit((u or "").strip())
    except ValueError:
        return (u or "").strip()
    host = (p.hostname or "").lower()
    port = p.port
    netloc = host
    if port and not ((p.scheme == "http" and port == 80) or (p.scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    return urllib.parse.urlunsplit((p.scheme.lower(), netloc, p.path or "/", p.query, ""))

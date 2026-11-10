#!/usr/bin/env python3
"""Tests for geo_check.py against a local test server. No outside network.
Run from the skill folder: python3 -m unittest discover -s tests"""
import http.server
import os
import sys
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import geo_check as G  # noqa: E402

WORDS = " ".join(["Larkspur Ridge Cycles repairs road and gravel bikes in Kilkenny."] * 20)
GOOD = f"""<!doctype html><html><head><title>Bike repair prices</title>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"LocalBusiness",
"name":"Larkspur Ridge Cycles","telephone":"+353 56 555 0100"}}</script></head>
<body><main><h1>Bike repair prices</h1><p>Larkspur Ridge Cycles. Call +353 56 555 0100.</p><p>{WORDS}</p></main></body></html>"""
MISMATCH = GOOD.replace("Call +353 56 555 0100", "Call +353 56 555 0199")
SHELL = "<!doctype html><html><head><title>App</title><script src=a.js></script><script src=b.js></script></head><body><div id=root></div></body></html>"

ROBOTS_OPEN = "User-agent: *\nAllow: /\n"
ROBOTS_BLOCK = "User-agent: *\nAllow: /\n\nUser-agent: OAI-SearchBot\nUser-agent: GPTBot\nDisallow: /\n"


class Site:
    """Routes: path -> (status, headers, body). 'waf' makes GPTBot user agents get 403."""
    def __init__(self):
        self.routes, self.waf = {}, False


SITE = Site()


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if SITE.waf and "GPTBot" in (self.headers.get("User-Agent") or ""):
            self.send_response(403)
            self.end_headers()
            return
        status, headers, body = SITE.routes.get(self.path, (404, {}, "not found"))
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Type", "text/html; charset=utf-8" if body.lstrip().startswith("<") else "text/plain")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *a):
        pass


class GeoCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        SITE.routes = {"/": (200, {}, GOOD), "/robots.txt": (200, {}, ROBOTS_OPEN)}
        SITE.waf = False

    def run_check(self, path="/"):
        return G.run(self.base + path, {"timeout": 5, "user_agent": "test-browser", "no_probe": False})

    def found(self, res, tier, check):
        return [f for f in res["findings"] if f["tier"] == tier and f["check"] == check]

    def test_clean_page_has_no_blockers_and_no_score(self):
        res = self.run_check()
        self.assertEqual(res["counts"][G.BLOCKS], 0)
        self.assertEqual(res["counts"][G.FIX], 0)
        md = G.render_markdown(res)
        self.assertNotIn("/100", md)
        self.assertIn("No score", md)
        self.assertEqual(len(res["robots"]), len(G.AGENTS))

    def test_noindex_header_blocks(self):
        SITE.routes["/"] = (200, {"X-Robots-Tag": "noindex, nofollow"}, GOOD)
        self.assertTrue(self.found(self.run_check(), G.BLOCKS, "Indexing"))

    def test_noindex_meta_blocks(self):
        SITE.routes["/"] = (200, {}, GOOD.replace("<head>", '<head><meta name="robots" content="noindex">'))
        self.assertTrue(self.found(self.run_check(), G.BLOCKS, "Indexing"))

    def test_nosnippet_is_fix_not_block(self):
        SITE.routes["/"] = (200, {}, GOOD.replace("<head>", '<head><meta name="robots" content="max-snippet:0">'))
        res = self.run_check()
        self.assertTrue(self.found(res, G.FIX, "Snippets"))
        self.assertEqual(res["counts"][G.BLOCKS], 0)

    def test_search_crawler_block_is_blocking_training_block_is_info(self):
        SITE.routes["/robots.txt"] = (200, {}, ROBOTS_BLOCK)
        res = self.run_check()
        blocks = self.found(res, G.BLOCKS, "robots.txt")
        self.assertEqual(len(blocks), 1)
        self.assertIn("OAI-SearchBot", blocks[0]["found"])
        infos = [f for f in self.found(res, G.INFO, "robots.txt") if "GPTBot" in f["found"]]
        self.assertEqual(len(infos), 1)
        self.assertEqual(blocks[0]["evidence_grade"], "[P]")

    def test_unreachable_site_is_not_reported_as_blocked(self):
        res = G.run("http://127.0.0.1:9/", {"timeout": 2, "user_agent": "t", "no_probe": False})
        self.assertTrue(res["unreachable"])
        self.assertEqual(res["counts"][G.BLOCKS], 0)
        self.assertEqual(G.badge_markdown(res, "2026-11-10"), "")
        self.assertEqual(G.main(["http://127.0.0.1:9/", "--timeout", "2", "--out-md", os.devnull]), 3)

    def test_robots_500_blocks_and_404_does_not(self):
        SITE.routes["/robots.txt"] = (500, {}, "oops")
        self.assertTrue(self.found(self.run_check(), G.BLOCKS, "robots.txt"))
        del SITE.routes["/robots.txt"]
        self.assertFalse(self.found(self.run_check(), G.BLOCKS, "robots.txt"))

    def test_javascript_shell_is_flagged(self):
        SITE.routes["/"] = (200, {}, SHELL)
        f = self.found(self.run_check(), G.FIX, "Text in raw HTML")
        self.assertTrue(f)
        self.assertEqual(f[0]["evidence_grade"], "[S]")

    def test_404_page_blocks(self):
        self.assertTrue(self.found(self.run_check("/missing"), G.BLOCKS, "Page request"))

    def test_firewall_probe(self):
        SITE.waf = True
        f = self.found(self.run_check(), G.CHECK, "Firewall or CDN")
        self.assertEqual(len(f), 1)
        self.assertIn("GPTBot", f[0]["found"])
        self.assertEqual(f[0]["evidence_grade"], "[U]")

    def test_schema_mismatch_reported_when_parity_checker_present(self):
        if G.load_schema_parity() is None:
            self.skipTest("schema-parity-checker not next to this skill")
        SITE.routes["/"] = (200, {}, MISMATCH)
        res = self.run_check()
        hits = [f for f in res["findings"] if f["check"] == "Structured data" and f["tier"] in (G.FIX, G.CHECK)]
        self.assertTrue(hits)
        self.assertIn("telephone", hits[0]["found"])

    def test_llms_txt_is_never_a_finding(self):
        SITE.routes["/llms.txt"] = (200, {}, "# Site\n")
        res = self.run_check()
        self.assertTrue(res["llms_txt"])
        self.assertTrue(self.found(res, G.INFO, "llms.txt"))
        self.assertEqual(res["counts"][G.FIX] + res["counts"][G.BLOCKS], 0)

    def test_canonical_same_page_is_quiet_and_other_page_is_flagged(self):
        SITE.routes["/"] = (200, {}, GOOD.replace("<head>", f'<head><link rel="canonical" href="{self.base}/">'))
        self.assertFalse(self.found(self.run_check(), G.CHECK, "Canonical"))
        SITE.routes["/"] = (200, {}, GOOD.replace("<head>", '<head><link rel="canonical" href="/other/">'))
        f = self.found(self.run_check(), G.CHECK, "Canonical")
        self.assertEqual(len(f), 1)
        self.assertIn("/other/", f[0]["found"])

    def test_badge_only_when_nothing_blocks_and_states_a_count(self):
        ok = G.badge_markdown(self.run_check(), "2026-11-10")
        self.assertIn("0%20blocking", ok)
        self.assertIn("2026--11--10-2ea44f", ok)      # date dashes doubled for shields.io
        self.assertIn("0 blocking findings, 2026-11-10", ok)
        self.assertNotIn("100", ok)
        SITE.routes["/"] = (200, {"X-Robots-Tag": "noindex"}, GOOD)
        self.assertEqual(G.badge_markdown(self.run_check(), "2026-11-10"), "")

    def test_robots_longest_match(self):
        g = G.parse_robots("User-agent: *\nDisallow: /private\nAllow: /private/open\n")
        self.assertFalse(G.robots_allowed(g, "Googlebot", "/private/x")[0])
        self.assertTrue(G.robots_allowed(g, "Googlebot", "/private/open/x")[0])


if __name__ == "__main__":
    unittest.main()

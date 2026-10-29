"""Tests for crawler_check.py. Run: python3 -m unittest discover -s tests

All IPs are documentation (RFC 5737 / RFC 3849) or private addresses. The
range files used here are TEST FIXTURES in examples/sample-ranges, not real
vendor ranges.
"""

import csv
import gzip
import io
import os
import socket
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import crawler_check as cc  # noqa: E402

SAMPLE = os.path.join(ROOT, "examples", "sample-synthetic-access.log")
RANGES = os.path.join(ROOT, "examples", "sample-ranges")
GBOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
BING = "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"


def line(ip, ua, path="/", status="200"):
    return f'{ip} - - [18/Oct/2026:06:00:00 +0000] "GET {path} HTTP/1.1" {status} 10 "-" "{ua}"\n'


class ParseTests(unittest.TestCase):
    def test_parse_ip_variants(self):
        self.assertEqual(str(cc.parse_ip("2001:db8::1")), "2001:db8::1")
        self.assertEqual(str(cc.parse_ip("[2001:db8::1]")), "2001:db8::1")
        self.assertEqual(str(cc.parse_ip("fe80::1%eth0")), "fe80::1")
        self.assertEqual(str(cc.parse_ip("::ffff:192.0.2.5")), "192.0.2.5")
        self.assertEqual(str(cc.parse_ip("192.0.2.5:443")), "192.0.2.5")
        self.assertIsNone(cc.parse_ip("not-an-ip"))
        self.assertIsNone(cc.parse_ip(""))

    def test_classify_order(self):
        self.assertEqual(cc.classify("compatible; Claude-User/1.0"), "Claude-User")
        self.assertEqual(cc.classify("compatible; ClaudeBot/1.0"), "ClaudeBot")
        self.assertEqual(cc.classify("compatible; Claude-SearchBot/1.0"), "Claude-SearchBot")
        self.assertEqual(cc.classify("Perplexity-User/1.0"), "Perplexity-User")
        self.assertEqual(cc.classify("compatible; GoogleOther"), "GoogleOther")
        self.assertEqual(cc.classify(GBOT), "Googlebot")
        self.assertIsNone(cc.classify("Mozilla/5.0 Chrome/141"))
        self.assertIsNone(cc.classify(""))

    def test_timestamps(self):
        self.assertEqual(cc.parse_ts("14/Oct/2026:03:12:09 +0100").isoformat(), "2026-10-14T02:12:09+00:00")
        self.assertEqual(cc.parse_ts("2026-10-14T03:12:09Z").isoformat(), "2026-10-14T03:12:09+00:00")
        self.assertEqual(cc.parse_ts("1792033929").year, 2026)
        self.assertIsNone(cc.parse_ts("yesterday"))

    def test_clean_path(self):
        self.assertEqual(cc.clean_path("/a/?x=1"), "/a/")
        self.assertEqual(cc.clean_path("https://example.com/llms.txt"), "/llms.txt")
        self.assertEqual(cc.clean_path(""), "/")


class SampleRunTests(unittest.TestCase):
    def setUp(self):
        self.ranges = cc.load_ranges(RANGES)

    def test_sample_counts_no_dns(self):
        stats, fam, hits = cc.analyze([SAMPLE], "auto", self.ranges, use_dns=False)
        self.assertEqual(stats["malformed"], 1)
        g = fam["GPTBot"]
        self.assertEqual((g["hits"], g["verified"], g["failed"], g["unverifiable"]), (7, 4, 3, 0))
        self.assertEqual(g["failed_ips"]["203.0.113.77"], 3)
        self.assertEqual(fam["Googlebot"]["verified"], 2)  # one IPv4, one IPv6 in fixture
        self.assertEqual(fam["Googlebot"]["failed"], 2)
        self.assertEqual(fam["Bytespider"]["unverifiable"], 1)
        self.assertEqual(fam["Applebot"]["unverifiable"], 1)  # no file, no DNS
        self.assertEqual(fam["OAI-SearchBot"]["unverifiable"], 1)  # file not cached
        self.assertEqual(fam["ClaudeBot"]["special"]["llms.txt"], 1)

    def test_no_ranges_means_unverifiable_not_failed(self):
        stats, fam, hits = cc.analyze([SAMPLE], "auto", {}, use_dns=False)
        for name, d in fam.items():
            self.assertEqual(d["verified"], 0, name)
            self.assertEqual(d["failed"], 0, name)

    def test_gzip_matches_plain(self):
        with tempfile.TemporaryDirectory() as td:
            gz = os.path.join(td, "access.log.gz")
            with open(SAMPLE, "rb") as src, gzip.open(gz, "wb") as dst:
                dst.write(src.read())
            _, fam_gz, _ = cc.analyze([gz], "auto", self.ranges, use_dns=False)
        _, fam_plain, _ = cc.analyze([SAMPLE], "auto", self.ranges, use_dns=False)
        self.assertEqual({k: v["hits"] for k, v in fam_gz.items()}, {k: v["hits"] for k, v in fam_plain.items()})

    def test_csv_format(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "export.csv")
            with open(p, "w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["timestamp", "ip", "method", "path", "status", "user_agent", "extra"])
                w.writerow(["2026-10-14T03:12:09Z", "192.0.2.10", "GET", "/robots.txt", "200", "GPTBot/1.4", "x"])
                w.writerow(["1792033929", "203.0.113.5", "GET", "/", "200", "GPTBot/1.4", "x"])
                w.writerow(["short", "row"])
            stats, fam, _ = cc.analyze([p], "auto", self.ranges, use_dns=False)
        self.assertEqual(stats["files"][0][1], "csv")
        self.assertEqual(stats["malformed"], 1)
        self.assertEqual((fam["GPTBot"]["verified"], fam["GPTBot"]["failed"]), (1, 1))

    def test_csv_missing_columns(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "bad.csv")
            with open(p, "w") as fh:
                fh.write("timestamp,ip,user_agent\n2026-10-14T03:12:09Z,192.0.2.10,GPTBot\n")
            with self.assertRaises(SystemExit):
                cc.analyze([p], "csv", self.ranges, use_dns=False)

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "empty.log")
            open(p, "w").close()
            stats, fam, hits = cc.analyze([p], "auto", self.ranges, use_dns=False)
            md = cc.render_markdown(stats, fam, self.ranges, False, 5)
        self.assertEqual(stats["lines"], 0)
        self.assertIn("No crawler user agents found", md)

    def test_cli_writes_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            md, sc, hc = (os.path.join(td, n) for n in ("r.md", "s.csv", "h.csv"))
            rc = cc.main([SAMPLE, "--ranges-dir", RANGES, "--no-dns", "--out-md", md, "--out-csv", sc, "--out-hits", hc])
            self.assertEqual(rc, 0)
            with open(sc) as fh:
                rows = list(csv.DictReader(fh))
            with open(hc) as fh:
                self.assertEqual(len(list(csv.DictReader(fh))), 26)
        self.assertEqual(rows[0]["crawler"], "GPTBot")


class DnsTests(unittest.TestCase):
    """Reverse DNS plus forward confirmation, with socket calls mocked."""

    PTR = {
        "198.51.100.200": "crawl-198-51-100-200.googlebot.com",
        "198.51.100.201": "evil.example.net",
        "198.51.100.202": "crawl-198-51-100-202.googlebot.com",  # forward points elsewhere
        "2001:db8:1::5": "crawl-2001-db8-1--5.googlebot.com",
        "198.51.100.44": "msnbot-198-51-100-44.search.msn.com",
    }
    FWD = {
        "crawl-198-51-100-200.googlebot.com": ["198.51.100.200"],
        "crawl-198-51-100-202.googlebot.com": ["192.0.2.99"],
        "crawl-2001-db8-1--5.googlebot.com": ["2001:db8:1::5"],
        "msnbot-198-51-100-44.search.msn.com": ["198.51.100.44"],
    }

    def fake_rev(self, ip):
        if ip == "198.51.100.250":
            raise socket.timeout("timed out")
        if ip not in self.PTR:
            raise socket.herror(1, "Unknown host")
        return (self.PTR[ip], [], [ip])

    def fake_fwd(self, host, port, *a, **k):
        if host not in self.FWD:
            raise socket.gaierror(-2, "Name or service not known")
        return [(0, 0, 0, "", (addr, 0)) for addr in self.FWD[host]]

    def setUp(self):
        cc._dns_cache.clear()
        self.p1 = mock.patch.object(cc.socket, "gethostbyaddr", side_effect=self.fake_rev)
        self.p2 = mock.patch.object(cc.socket, "getaddrinfo", side_effect=self.fake_fwd)
        self.p1.start()
        self.p2.start()

    def tearDown(self):
        self.p1.stop()
        self.p2.stop()

    def run_lines(self, text, ranges=None):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "a.log")
            with open(p, "w") as fh:
                fh.write(text)
            return cc.analyze([p], "combined", ranges or {}, use_dns=True)

    def test_dns_paths(self):
        text = (line("198.51.100.200", GBOT) + line("198.51.100.201", GBOT) + line("198.51.100.202", GBOT)
                + line("198.51.100.203", GBOT) + line("2001:db8:1::5", GBOT) + line("198.51.100.250", GBOT)
                + line("198.51.100.44", BING))
        _, fam, hits = self.run_lines(text)
        by_ip = {h["ip"]: (h["verification"], h["detail"]) for h in hits}
        self.assertEqual(by_ip["198.51.100.200"][0], "verified")
        self.assertEqual(by_ip["198.51.100.201"][0], "failed")
        self.assertIn("not in", by_ip["198.51.100.201"][1])
        self.assertEqual(by_ip["198.51.100.202"][0], "failed")
        self.assertEqual(by_ip["198.51.100.203"], ("failed", "no PTR record"))
        self.assertEqual(by_ip["2001:db8:1::5"][0], "verified")
        self.assertEqual(by_ip["198.51.100.250"][0], "unverifiable")  # DNS timeout is not a fail
        self.assertEqual(fam["Bingbot"]["verified"], 1)

    def test_range_match_skips_dns(self):
        ranges = cc.load_ranges(RANGES)
        _, fam, hits = self.run_lines(line("198.51.100.5", GBOT), ranges)
        self.assertEqual(hits[0]["verification"], "verified")
        self.assertEqual(hits[0]["detail"], "in google-common-crawlers.json")
        cc.socket.gethostbyaddr.assert_not_called()

    def test_dns_not_used_for_range_only_vendors(self):
        _, fam, hits = self.run_lines(line("203.0.113.5", "compatible; GPTBot/1.4"))
        self.assertEqual(hits[0]["verification"], "unverifiable")
        cc.socket.gethostbyaddr.assert_not_called()

    def test_dns_cache(self):
        self.run_lines(line("198.51.100.200", GBOT) * 5)
        self.assertEqual(cc.socket.gethostbyaddr.call_count, 1)


if __name__ == "__main__":
    unittest.main()

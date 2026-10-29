#!/usr/bin/env python3
"""Tests for analyze.py. Run: python3 -m unittest scripts/test_analyze.py (from the skill folder)."""
import csv
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = os.path.join(HERE, "..", "examples")

BRANDS = {
    "brand": {"name": "Liffey Ledger Accountants", "aliases": ["Liffey Ledger"],
              "domains": ["https://www.liffeyledger.example/"]},
    "competitors": [
        {"name": "Liffey Ledger Tax Clinic", "domains": ["taxclinic.example"]},
        {"name": "Northside Numbers", "domains": ["northsidenumbers.example"]},
    ],
}
HEADER = ["run_date", "engine", "question_id", "intent", "run_number", "answer_text", "cited_urls"]


def slurp(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.brands = os.path.join(self.dir, "brands.json")
        with open(self.brands, "w") as fh:
            json.dump(BRANDS, fh)

    def write(self, rows, header=HEADER, name="a.csv"):
        path = os.path.join(self.dir, name)
        with open(path, "w", newline="") as fh:
            w = csv.writer(fh)
            if header:
                w.writerow(header)
            w.writerows(rows)
        return path

    def run_tool(self, path, *extra):
        md, out = os.path.join(self.dir, "r.md"), os.path.join(self.dir, "c.csv")
        code = A.main([path, "--brands", self.brands, "--out-md", md, "--out-csv", out] + list(extra))
        cells = read_csv(out) if code == 0 else None
        return code, (slurp(md) if code == 0 else None), cells


class TestStats(unittest.TestCase):
    def test_wilson_known_values(self):
        lo, hi = A.wilson(3, 5)
        self.assertAlmostEqual(lo, 0.2307, places=3)
        self.assertAlmostEqual(hi, 0.8824, places=3)
        self.assertEqual(A.wilson(0, 0), (None, None))
        lo, hi = A.wilson(0, 10)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.2775, places=3)

    def test_two_proportion(self):
        z, p = A.two_proportion(20, 100, 40, 100)
        self.assertAlmostEqual(p, 0.0021, places=3)
        self.assertEqual(A.two_proportion(0, 50, 0, 50), (0.0, 1.0))

    def test_verdict_thin(self):
        self.assertEqual(A.verdict((1, 10), (9, 10))[0], "too thin to compare")
        self.assertTrue(A.verdict((10, 100), (60, 100))[0].startswith("change outside noise"))
        self.assertEqual(A.verdict((30, 100), (33, 100))[0], "within noise")


class TestNormalize(unittest.TestCase):
    def test_hosts(self):
        for u in ["https://www.liffeyledger.example/", "http://liffeyledger.example",
                  "liffeyledger.example/fees?x=1", "WWW.LiffeyLedger.example:443/a#b"]:
            self.assertEqual(A.norm_host(u), "liffeyledger.example", u)
        self.assertTrue(A.host_matches("blog.liffeyledger.example", "liffeyledger.example"))
        self.assertFalse(A.host_matches("notliffeyledger.example", "liffeyledger.example"))
        self.assertFalse(A.host_matches("", "liffeyledger.example"))

    def test_alias_matching(self):
        m = A.Matcher(A.load_brands_from(BRANDS))
        self.assertEqual(set(m.find("Try LIFFEY  LEDGER first.")), {"Liffey Ledger Accountants"})
        self.assertEqual(m.find("Liffey Ledgers are rivers of books"), {})
        # Longest alias wins: the competitor name contains the brand alias.
        self.assertEqual(set(m.find("Ask Liffey Ledger Tax Clinic.")), {"Liffey Ledger Tax Clinic"})
        found = m.find("Northside Numbers and Liffey Ledger Accountants")
        self.assertLess(found["Northside Numbers"], found["Liffey Ledger Accountants"])


class TestEndToEnd(Base):
    def test_empty_file(self):
        path = os.path.join(self.dir, "empty.csv")
        open(path, "w").close()
        self.assertEqual(self.run_tool(path)[0], 2)

    def test_header_only(self):
        self.assertEqual(self.run_tool(self.write([]))[0], 2)

    def test_missing_columns(self):
        path = self.write([["2026-09-01", "chatgpt", "x"]], header=["run_date", "engine", "foo"])
        self.assertEqual(self.run_tool(path)[0], 2)

    def test_outcomes_duplicates_and_malformed(self):
        rows = [
            # named and cited (subdomain)
            ["2026-09-01", "e1", "Q1", "vendor", "1", "Liffey Ledger is good.", "https://blog.liffeyledger.example/x"],
            # exact duplicate of the row above: dropped
            ["2026-09-01", "e1", "Q1", "vendor", "1", "Liffey Ledger is good.", "https://blog.liffeyledger.example/x"],
            # cited, not named, other brand named: read but credited someone else
            ["2026-09-01", "e1", "Q1", "vendor", "2", "Northside Numbers is good.", "liffeyledger.example"],
            # cited, nobody named
            ["2026-09-01", "e1", "Q1", "vendor", "3", "Get quotes.", "www.liffeyledger.example/"],
            # absent; lookalike domain does not count
            ["2026-09-01", "e1", "Q2", "educational", "1", "Ask around.", "https://notliffeyledger.example"],
            # malformed: missing engine
            ["2026-09-01", "", "Q2", "educational", "2", "x", ""],
        ]
        code, md, cells = self.run_tool(self.write(rows))
        self.assertEqual(code, 0)
        self.assertIn("Exact duplicates dropped: 1. Rows skipped as malformed: 1.", md)
        c = [r for r in cells if r["question_id"] == "Q1" and r["is_primary"] == "1"][0]
        self.assertEqual((c["runs"], c["named"], c["cited"]), ("3", "1", "3"))
        self.assertEqual((c["named_and_cited"], c["cited_not_named"],
                          c["cited_not_named_other_brand_named"]), ("1", "2", "1"))
        q2 = [r for r in cells if r["question_id"] == "Q2" and r["is_primary"] == "1"][0]
        self.assertEqual((q2["absent"], q2["thin_cell"]), ("1", "1"))
        self.assertIn("Questions where Liffey Ledger Accountants was never named", md)
        self.assertIn("| Q2 |", md.split("never named")[1])

    def test_brands_named_mode_and_no_citations(self):
        header = ["run_date", "engine", "question_id", "brands_named"]
        rows = [["2026-09-01", "e1", "Q1", "Northside Numbers; Liffey Ledger; Some Other Firm"],
                ["2026-10-01", "e1", "Q1", ""]]
        code, md, cells = self.run_tool(self.write(rows, header=header))
        self.assertEqual(code, 0)
        self.assertIn("brands_named list", md)
        self.assertIn("no `cited_urls` column", md)
        sep = [r for r in cells if r["period"] == "2026-09" and r["is_primary"] == "1"][0]
        self.assertEqual((sep["named"], sep["mean_position"], sep["cited"]), ("1", "2.0", ""))

    def test_compare_bad_period(self):
        path = self.write([["2026-09-01", "e1", "Q1", "v", "1", "x", ""]])
        self.assertEqual(self.run_tool(path, "--compare", "2026-01", "2026-02")[0], 2)

    def test_sample_runs(self):
        sample = os.path.join(EXAMPLES, "sample-answers.csv")
        brands = os.path.join(EXAMPLES, "brands.json")
        md = os.path.join(self.dir, "r.md")
        out = os.path.join(self.dir, "c.csv")
        self.assertEqual(A.main([sample, "--brands", brands, "--out-md", md, "--out-csv", out]), 0)
        text = slurp(md)
        self.assertIn("Answers analyzed: 216", text)
        self.assertNotIn("\u2014", text)  # no em dashes in output


if __name__ == "__main__":
    unittest.main()

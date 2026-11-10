#!/usr/bin/env python3
"""Tests for the SV-001 analysis. Run: python3 -m unittest discover -s . -p "test_*.py" """
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A  # noqa: E402


class TestStats(unittest.TestCase):
    def test_ranks_share_ties(self):
        self.assertEqual(A.ranks([10, 20, 20, 30]), [1.0, 2.5, 2.5, 4.0])

    def test_spearman_known_values(self):
        self.assertAlmostEqual(A.spearman([1, 2, 3, 4, 5], [2, 4, 6, 8, 100]), 1.0)
        self.assertAlmostEqual(A.spearman([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]), -1.0)
        # Textbook example: d^2 sums to 194 over n=10, rho = 1 - 6*194/990
        iq = [106, 100, 86, 101, 99, 103, 97, 113, 112, 110]
        tv = [7, 27, 2, 50, 28, 29, 20, 12, 6, 17]
        self.assertAlmostEqual(A.spearman(iq, tv), 1 - 6 * 194 / 990, places=6)

    def test_constant_input_is_nan(self):
        self.assertTrue(math.isnan(A.spearman([1, 1, 1], [1, 2, 3])))

    def test_permutation_p(self):
        x = list(range(20))
        rho, p = A.perm_p(x, x, n_perm=2000)
        self.assertAlmostEqual(rho, 1.0)
        self.assertLess(p, 0.001)
        y = [3, 17, 8, 1, 12, 19, 5, 14, 0, 10, 7, 16, 2, 11, 18, 4, 13, 6, 15, 9]
        rho, p = A.perm_p(x, y, n_perm=2000)
        self.assertGreater(p, 0.2)
        self.assertEqual(A.perm_p(x, y, n_perm=500), A.perm_p(x, y, n_perm=500))   # seeded

    def test_partial_removes_a_shared_driver(self):
        z = list(range(1, 21))
        x = [v * 2 + (1 if v % 2 else -1) for v in z]
        y = [v * 3 + (1 if v % 3 else -2) for v in z]
        self.assertGreater(A.spearman(x, y), 0.9)
        self.assertLess(abs(A.partial_spearman(x, y, z)), A.spearman(x, y))


class TestVerdicts(unittest.TestCase):
    def test_rule(self):
        self.assertEqual(A.verdict(20, 0.7, 0.001), "score goes with the outcome")
        self.assertEqual(A.verdict(20, -0.7, 0.001), "score goes against the outcome")
        self.assertEqual(A.verdict(20, 0.4, 0.03), "no relationship detected")
        self.assertTrue(A.verdict(14, 0.9, 0.001).startswith("not testable"))

    def test_analyze_end_to_end(self):
        doms = [f"d{i}.example" for i in range(20)]
        scores = {"s": {d: float(i) for i, d in enumerate(doms)}}
        outcomes = {d: {"chatgpt": (100, i * 4, i * 2), "gemini": (100, i * 3, i)} for i, d in enumerate(doms)}
        for d in outcomes:
            outcomes[d]["all"] = tuple(sum(v[k] for v in outcomes[d].values()) for k in range(3))
        rows = A.analyze(scores, outcomes, {d: 50.0 + i % 3 for i, d in enumerate(doms)}, n_perm=1000)
        primary = [r for r in rows if r["primary"]]
        self.assertEqual(len(primary), 1)
        self.assertEqual(primary[0]["verdict"], "score goes with the outcome")
        self.assertEqual(len(rows), 6)          # 3 engines x 2 outcomes
        self.assertIn("| s | 20 |", A.render(rows))


if __name__ == "__main__":
    unittest.main()

"""Tests for readout.py. Run: python3 -m unittest discover -s tests"""

import io
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import readout as ro  # noqa: E402

Z95 = 1.959963984540054


class WilsonTests(unittest.TestCase):
    def test_known_values(self):
        # Reference values for the Wilson score interval at 95%.
        p, lo, hi = ro.wilson(5, 10, Z95)
        self.assertAlmostEqual(lo, 0.2366, places=4)
        self.assertAlmostEqual(hi, 0.7634, places=4)
        p, lo, hi = ro.wilson(0, 10, Z95)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.2775, places=4)
        p, lo, hi = ro.wilson(10, 10, Z95)
        self.assertAlmostEqual(lo, 0.7225, places=4)
        self.assertEqual(hi, 1.0)

    def test_bounds_contain_estimate(self):
        for k, n in [(1, 3), (7, 40), (39, 40), (0, 1), (1, 1)]:
            p, lo, hi = ro.wilson(k, n, Z95)
            self.assertTrue(0 <= lo <= p <= hi <= 1, (k, n))


class MoverTests(unittest.TestCase):
    def test_difference_matches_newcombe_example(self):
        # Newcombe (1998) example: 56/70 vs 48/80, hybrid score interval
        # 0.0524 to 0.3339 for the difference.
        a = ro.wilson(56, 70, Z95)
        b = ro.wilson(48, 80, Z95)
        est, lo, hi = ro.mover([(1,) + a, (-1,) + b])
        self.assertAlmostEqual(est, 0.2, places=4)
        self.assertAlmostEqual(lo, 0.0524, places=3)
        self.assertAlmostEqual(hi, 0.3339, places=3)

    def test_did_point_estimate(self):
        r = ro.readout((3, 40), (11, 40), (4, 40), (5, 40))
        self.assertAlmostEqual(r["test_change"][0], 0.2)
        self.assertAlmostEqual(r["control_change"][0], 0.025)
        self.assertAlmostEqual(r["did"][0], 0.175)
        est, lo, hi = r["did"]
        self.assertLess(lo, est)
        self.assertGreater(hi, est)

    def test_no_change_interval_symmetric_and_contains_zero(self):
        r = ro.readout((10, 40), (10, 40), (10, 40), (10, 40))
        est, lo, hi = r["did"]
        self.assertAlmostEqual(est, 0.0)
        self.assertAlmostEqual(-lo, hi, places=9)


class LabelTests(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(ro.suggest_label(0.25, 0.05, 0.45, 0.10)[0], "worked")
        self.assertEqual(ro.suggest_label(-0.25, -0.45, -0.05, 0.10)[0], "made it worse")
        self.assertEqual(ro.suggest_label(0.01, -0.04, 0.06, 0.10)[0], "no detectable effect")
        self.assertEqual(ro.suggest_label(0.10, -0.10, 0.30, 0.10)[0], "inconclusive")
        self.assertEqual(ro.suggest_label(0.05, 0.01, 0.12, 0.10)[0], "inconclusive")

    def test_lower_is_better(self):
        self.assertEqual(ro.suggest_label(-0.25, -0.45, -0.05, 0.10, lower_is_better=True)[0], "worked")


class CliTests(unittest.TestCase):
    def run_cli(self, args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                rc = ro.main(args)
            except SystemExit as e:
                rc = e.code
        return rc, out.getvalue(), err.getvalue()

    def test_ok(self):
        rc, out, _ = self.run_cli(["--test-before", "3/40", "--test-after", "11/40",
                                   "--control-before", "4/40", "--control-after", "5/40", "--min-effect", "0.1"])
        self.assertEqual(rc, 0)
        self.assertIn("diff-in-diff", out)
        self.assertIn("Suggested label", out)

    def test_bad_inputs(self):
        for bad in ["5/0", "6/5", "-1/5", "abc", "3"]:
            rc, _, err = self.run_cli(["--test-before", bad, "--test-after", "1/5",
                                       "--control-before", "1/5", "--control-after", "1/5"])
            self.assertEqual(rc, 2, bad)

    def test_small_sample_note(self):
        rc, out, _ = self.run_cli(["--test-before", "1/8", "--test-after", "4/8",
                                   "--control-before", "1/8", "--control-after", "2/8"])
        self.assertIn("directional", out)


if __name__ == "__main__":
    unittest.main()

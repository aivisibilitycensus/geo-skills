#!/usr/bin/env python3
"""Tests for collect.py. No network: providers are replaced with fakes.
Run from the skill folder: python3 -m unittest discover -s tests"""
import csv
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "answer-log-analyzer", "scripts"))
import collect as C  # noqa: E402

QUESTIONS = "id,service,intent,question\nACC01,accounting,vendor selection,Which accounting firms in Dublin work with small tech companies?\nACC02,accounting,pricing,How much does a small company accountant cost in Dublin?\n"
OPTS = {"location_code": 2372, "language_code": "en", "gl": "ie", "hl": "en", "location": "",
        "wait": 5, "poll_every": 0, "delay": 0, "note": ""}


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.q = os.path.join(self.tmp.name, "questions.csv")
        with open(self.q, "w", encoding="utf-8") as f:
            f.write(QUESTIONS)
        self.out = os.path.join(self.tmp.name, "answers.csv")
        self.env = dict(os.environ)
        os.environ.update(DATAFORSEO_LOGIN="u", DATAFORSEO_PASSWORD="p", SERPAPI_KEY="k")

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)
        self.tmp.cleanup()


class TestQuestions(Base):
    def test_reads_builder_columns(self):
        qs = C.read_questions(self.q)
        self.assertEqual([q["question_id"] for q in qs], ["ACC01", "ACC02"])
        self.assertEqual(qs[1]["intent"], "pricing")

    def test_duplicate_id_refused(self):
        with open(self.q, "a", encoding="utf-8") as f:
            f.write("ACC01,accounting,pricing,Again?\n")
        with self.assertRaises(C.CollectError):
            C.read_questions(self.q)

    def test_unknown_engine_refused(self):
        with self.assertRaises(C.CollectError):
            C.parse_engines("chatgpt,perplexity")


class TestPlan(Base):
    def test_counts(self):
        qs = C.read_questions(self.q)
        _, per, calls = C.plan(qs, ["chatgpt", "google_ai_overview"], 3)
        self.assertEqual(per, {"chatgpt": 6, "google_ai_overview": 6})
        self.assertEqual(calls, {"dataforseo": 6, "serpapi": 12})

    def test_plan_makes_no_calls_and_run_needs_yes(self):
        self.assertEqual(C.main(["plan", self.q, "--engines", "chatgpt", "--repeats", "3"]), 0)
        self.assertEqual(C.main(["run", self.q, "--engines", "chatgpt", "--out", self.out]), 1)
        self.assertFalse(os.path.exists(self.out))

    def test_warns_under_three_repeats(self):
        self.assertIn("fewer than 3", C.plan_text(C.read_questions(self.q), ["mock"], 1))


class TestMock(Base):
    def test_mock_run_writes_canonical_csv_and_is_resumable(self):
        args = ["run", self.q, "--engines", "mock", "--repeats", "3", "--out", self.out,
                "--run-date", "2026-11-10"]
        self.assertEqual(C.main(args), 0)
        first = rows(self.out)
        self.assertEqual(len(first), 6)
        self.assertEqual(list(first[0].keys()), C.FIELDS)
        self.assertEqual(C.main(args), 0)          # second run adds nothing
        self.assertEqual(len(rows(self.out)), 6)
        self.assertEqual(len(os.listdir(C.raw_dir_for(self.out))), 6)

    def test_output_is_readable_by_the_analyzer(self):
        import analyze as A
        C.main(["run", self.q, "--engines", "mock", "--repeats", "3", "--out", self.out,
                "--run-date", "2026-11-10"])
        loaded = A.read_rows(self.out)
        self.assertTrue(loaded)


class TestDataForSEO(Base):
    def fake(self, ready_after=1):
        state = {"posts": [], "gets": 0}

        def fetch(url, method="GET", headers=None, body=None, timeout=120):
            self.assertTrue(headers["Authorization"].startswith("Basic "))
            if method == "POST":
                self.assertIn("/ai_optimization/chat_gpt/llm_scraper/task_post", url)
                state["posts"].append(body[0])
                return {"status_code": 20000, "tasks": [{"status_code": 20100, "id": f"t{len(state['posts'])}"}]}
            state["gets"] += 1
            if state["gets"] <= ready_after:
                return {"status_code": 20000, "tasks": [{"status_code": 40602, "status_message": "Task In Queue."}]}
            return {"status_code": 20000, "tasks": [{"status_code": 20000, "result": [{
                "markdown": "Try Liffey Ledger.", "model": "gpt-x",
                "sources": [{"url": "https://liffeyledger.example/"}, {"url": "https://liffeyledger.example/"}],
                "search_results": [1, 2]}]}]}
        return fetch, state

    def test_post_then_poll(self):
        fetch, state = self.fake()
        cells = C.build_cells(C.read_questions(self.q)[:1], ["chatgpt"], 2, "2026-11-10")
        c = C.collect(cells, self.out, OPTS, fetch=fetch, log=lambda *_: None, sleep=lambda *_: None)
        self.assertEqual((c["posted"], c["written"], c["still_pending"]), (2, 2, 0))
        self.assertEqual(state["posts"][0]["location_code"], 2372)
        r = rows(self.out)[0]
        self.assertEqual(r["answer_text"], "Try Liffey Ledger.")
        self.assertEqual(r["cited_urls"], "https://liffeyledger.example/")
        self.assertIn("model=gpt-x", r["data_note"])
        self.assertFalse(os.path.exists(C.pending_path(self.out)))

    def test_pending_tasks_are_kept_for_resume_and_not_reposted(self):
        fetch, state = self.fake(ready_after=10 ** 6)
        cells = C.build_cells(C.read_questions(self.q)[:1], ["chatgpt"], 1, "2026-11-10")
        opts = dict(OPTS, wait=0)
        c = C.collect(cells, self.out, opts, fetch=fetch, log=lambda *_: None, sleep=lambda *_: None)
        self.assertEqual(c["still_pending"], 1)
        self.assertEqual(len(json.load(open(C.pending_path(self.out)))), 1)
        C.collect(cells, self.out, opts, fetch=fetch, log=lambda *_: None, sleep=lambda *_: None)
        self.assertEqual(len(state["posts"]), 1)   # a second run does not pay for the task again

    def test_missing_key_is_an_error_not_a_crash(self):
        del os.environ["DATAFORSEO_LOGIN"]
        cells = C.build_cells(C.read_questions(self.q)[:1], ["chatgpt"], 1, "2026-11-10")
        c = C.collect(cells, self.out, OPTS, log=lambda *_: None, sleep=lambda *_: None)
        self.assertEqual(c["errors"], 1)


class TestSerpApi(Base):
    def test_ai_overview_second_call_and_parse(self):
        calls = []

        def fetch(url, method="GET", headers=None, body=None, timeout=120):
            calls.append(url)
            if "engine=google_ai_overview" in url:
                return {"ai_overview": {"text_blocks": [
                    {"snippet": "Firms often named:"},
                    {"list": [{"title": "Liffey Ledger", "snippet": "fixed fees"},
                              {"snippet": ": startups", "snippet_links": [{"link": "https://www.northsidenumbers.example/x"}]}]}],
                    "references": [{"link": "https://liffeyledger.example/"}]}}
            return {"search_metadata": {"id": "s1"}, "ai_overview": {"page_token": "tok"}}
        cell = C.build_cells(C.read_questions(self.q)[:1], ["google_ai_overview"], 1, "2026-11-10")[0]
        answer, urls, notes, _ = C.serp_run(cell, OPTS, fetch)
        self.assertEqual(len(calls), 2)
        self.assertIn("gl=ie", calls[0])
        self.assertIn("- Liffey Ledger fixed fees", answer)
        self.assertIn("- [northsidenumbers.example]: startups", answer)
        self.assertEqual(urls, ["https://liffeyledger.example/"])

    def test_no_overview_is_logged_as_an_empty_answer(self):
        cells = C.build_cells(C.read_questions(self.q)[:1], ["google_ai_overview"], 1, "2026-11-10")
        C.collect(cells, self.out, OPTS, fetch=lambda *a, **k: {"search_metadata": {"id": "s"}},
                  log=lambda *_: None, sleep=lambda *_: None)
        r = rows(self.out)[0]
        self.assertEqual(r["answer_text"], "")
        self.assertIn("no AI Overview shown", r["data_note"])

    def test_copilot_uses_reconstructed_markdown(self):
        cell = C.build_cells(C.read_questions(self.q)[:1], ["copilot"], 1, "2026-11-10")[0]
        seen = []

        def fetch(url, **k):
            seen.append(url)
            return {"reconstructed_markdown": "Northside Numbers.", "references": [{"link": "https://a.example/"}]}
        answer, urls, _, _ = C.serp_run(cell, OPTS, fetch)
        self.assertEqual(answer, "Northside Numbers.")
        self.assertIn("engine=bing_copilot", seen[0])
        self.assertNotIn("gl=", seen[0])

    def test_provider_error_is_counted(self):
        cells = C.build_cells(C.read_questions(self.q)[:1], ["copilot"], 1, "2026-11-10")
        c = C.collect(cells, self.out, OPTS, fetch=lambda *a, **k: {"error": "Invalid API key."},
                      log=lambda *_: None, sleep=lambda *_: None)
        self.assertEqual((c["errors"], c["written"]), (1, 0))


if __name__ == "__main__":
    unittest.main()

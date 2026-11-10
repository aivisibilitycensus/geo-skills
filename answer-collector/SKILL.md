---
name: answer-collector
description: Run a fixed set of buyer questions on AI engines (ChatGPT and Gemini through DataForSEO; Google AI Overviews, Google AI Mode and Microsoft Copilot through SerpApi) with repeats, and log every answer and its cited URLs to a CSV, using the user's own API keys. Use when someone wants to collect AI answers for tracking AI visibility, has a question set and needs the data, asks how to run prompts on ChatGPT or Gemini repeatedly, or wants to build an AI visibility tracker without paying for a dashboard.
---

# Answer collector

Asks AI engines the same questions several times and saves every answer. This is the "collect" step between two other skills: build the questions with question-set-builder, collect with this, then read the result with answer-log-analyzer.

It does one thing: turn a question set into a log of answers you can count. It does not score anything, and it does not decide what the answers mean.

## What you need

- A question set CSV with columns `id`, `intent`, `question` (question-set-builder writes this).
- An account with at least one provider, and its key in an environment variable. The script never takes keys as arguments and never writes them to a file.

| Engine label | Goes through | Environment variables |
|---|---|---|
| `chatgpt` | DataForSEO | `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD` |
| `gemini` | DataForSEO | `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD` |
| `google_ai_overview` | SerpApi | `SERPAPI_KEY` |
| `google_ai_mode` | SerpApi | `SERPAPI_KEY` |
| `copilot` | SerpApi | `SERPAPI_KEY` |
| `mock` | Nothing (fake answers) | None |

Both providers charge per call. This skill does not quote prices because they change: open the provider's pricing page before a run.

## Step 1: Agree the run before spending anything

Settle these with the user and write them down, because changing any of them later breaks comparison between check dates:

- **Engines.** Only the ones their buyers use.
- **Repeats.** At least 3 per question per engine per date. AI answers change from one run to the next, so one answer per question is not a measurement.
- **Location and language.** Where the buyers are. DataForSEO takes a location code (`--location-code`, default 2840 for the United States; the provider's locations list has the others). SerpApi takes `--gl`, `--hl` and `--location`.
- **Check dates.** Fixed in advance (for example the second Monday of each month).

## Step 2: Count the calls

```
python3 scripts/collect.py plan questions.csv --engines chatgpt,gemini,google_ai_overview --repeats 3
```

This makes no calls. It prints the number of answers and the largest number of billable calls per provider. Show the user this output and get a yes before Step 3. A Google AI Overview can need two calls, so its count is the worst case.

## Step 3: Collect

```
export DATAFORSEO_LOGIN=...  DATAFORSEO_PASSWORD=...  SERPAPI_KEY=...
python3 scripts/collect.py run questions.csv --engines chatgpt,gemini,google_ai_overview \
    --repeats 3 --out answers.csv --location-code 2372 --gl ie --hl en --yes
```

- Without `--yes` the script prints the plan and stops.
- Every answer is appended to `answers.csv` as soon as it arrives, and the raw provider response is saved in `answers-raw/`. Keep the raw folder: answers cannot be collected again later.
- It is safe to run the same command twice. Answers already in the file are skipped, and DataForSEO tasks already paid for are not posted again.
- DataForSEO works as a queue: the script posts the tasks, then waits for results (10 minutes by default, `--wait` to change). If some are still running, finish later with `python3 scripts/collect.py resume --out answers.csv`.
- Next check date: run the same command again with the same `--out`. Rows are added under the new date.

To try the whole flow with no account and no cost, use `--engines mock`. It writes fake answers about fictional businesses.

## Step 4: Check the log, then hand it on

Before analysis, look at the file:

- Count the rows against the plan. Say how many answers are missing and why (provider errors are printed during the run).
- Rows with an empty `answer_text` and "no AI Overview shown" in `data_note` are real results, not errors: Google showed no AI Overview for that question on that run. Keep them.
- Read three or four answers in full. If the engine is answering a different question from the one the buyer would mean, fix the question set and start a new series; do not edit questions mid-series.

Then run answer-log-analyzer on `answers.csv`. The columns already match.

## What the output is, and is not

| Column | What it holds |
|---|---|
| `run_date`, `engine`, `question_id`, `intent`, `run_number`, `question` | Which answer this is |
| `answer_text` | The full answer as the provider returned it |
| `cited_urls` | Source URLs the answer listed, separated by `; ` |
| `data_note` | Provider, location settings, model name when the provider reports one, and anything unusual |

Limits to tell the user:

- **These are answers collected through a provider, not through the user's own logged-in account.** They show what a logged-out visitor in the chosen location is likely to get. Personalized answers can differ.
- **ChatGPT decides for itself whether to search the web**, as it does for a person. `--force-web-search` makes it search every time, which gives more citations but is not what users see. Pick one setting and keep it.
- **Perplexity and Claude are not supported.** The script only includes engines the AI Visibility Census runs in its own collection, so the request and response handling is taken from working code.
- **An answer naming a brand is a count, not a ranking factor.** This skill does not explain why a brand was named.

## Verification status

The request and response handling for all five engines is the same as the AI Visibility Census uses in its own collection (DataForSEO task post and get; SerpApi `google`, `google_ai_overview`, `google_ai_mode` and `bing_copilot`), as of 10 November 2026. The script's tests run against recorded response shapes, not live calls. Providers change their APIs: if a field goes missing, the raw response in `answers-raw/` shows what came back, and the run prints the error instead of writing a wrong row.

## Files

- `scripts/collect.py`: the collector. Python 3, standard library only.
- `tests/test_collect.py`: 15 tests, no network.
- `examples/sample-questions.csv`, `examples/output-plan.txt`, `examples/sample-answers.csv`: a worked example using the mock engine.

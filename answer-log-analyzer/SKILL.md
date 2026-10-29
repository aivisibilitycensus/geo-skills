---
name: answer-log-analyzer
description: Analyze logged AI answers from repeated runs of a fixed question set (a tracker export or a manual CSV) and report how often a brand is named and cited, per question, intent and engine, with run-to-run variance, confidence intervals and an honest month-on-month comparison. Use when someone has AI visibility tracking data and wants to know what it actually shows, whether a change is real or noise, or where the content gaps are.
---

# Answer log analyzer

Takes the answers you logged from asking the same questions of AI assistants, again and again, and reports what they show for one brand and its competitors. This is the "analyze" half of a measure-then-analyze pair: build the questions with the question-set-builder skill, collect the answers, then run this.

Every number in the report is a count from the log, or a rate with a 95% interval around it. The skill does not invent a visibility score. It also says when the data is too thin to support a conclusion, which is often.

## Step 1: Check how the runs were collected

The analysis is only as good as the log. Before running anything, ask how the answers were collected and note any gaps in the report. A sound log has:

- **A fixed question set** with stable IDs and the same wording every time (question-set-builder, Step 6). If the wording changed between periods, the periods are not comparable for that question.
- **Fixed check dates**, decided in advance (for example the second Monday of each month), not "when we remembered".
- **At least 3 runs per question, per engine, per date.** AI answers vary from one run to the next. One run per question tells you what one answer said, not what the engine usually says.
- **Logged out, or a clean session, where possible**, so personalization and chat history do not leak into answers. Note where that was not possible.
- **The same engines and settings** (model, location, web search on or off) across periods.
- **The full answer text and the cited URLs**, saved at the time. Answers cannot be recollected later.

If the data comes from a tracker (Peec, Profound, Otterly, Temso, Searchable, or similar), the tool chose the runs, the sampling and often the brand detection. Ask what the vendor documents about this and record it as a limit. Treat the tracker's own sampling as a black box unless its documentation says otherwise.

## Step 2: Put the log into the canonical CSV

One row per answer. Column names are case-insensitive. Extra columns are ignored.

| Column | Required | What it holds |
|---|---|---|
| `run_date` | Yes | Date of the run, `YYYY-MM-DD` |
| `engine` | Yes | Engine label, used as given (for example `chatgpt`, `perplexity`) |
| `question_id` | Yes | Stable ID from the question set (for example `ACC01`) |
| `answer_text` | One of these two | Full answer text. Mentions are detected from it |
| `brands_named` | One of these two | Brands named in the answer, in order of first mention, separated by `;` |
| `cited_urls` | Recommended | URLs the answer cited as sources, separated by `;`. Without it, cited measures are not reported |
| `intent` | Recommended | Intent label from the question set. Missing means `unlabeled` |
| `run_number` | Optional | Run number within a date. Assigned in file order if missing |
| `period` | Optional | Label for grouping runs (for example `month-1`). Default: the month of `run_date` |
| `question` | Optional | Question text, shown in the content-gaps list |

Tracker exports differ and change over time. This skill does not list vendor column names, because they were not verified against each vendor's documentation. Open your export, map its columns to the schema above, and rename them in a spreadsheet or with a small script. `references/mapping.md` covers common export shapes (one row per answer, one row per citation, wide files with one column per brand).

## Step 3: Write the brand config

A JSON file. The first brand is the one the report is about; competitors are compared alongside it.

```json
{
  "brand": {"name": "Liffey Ledger Accountants", "aliases": ["Liffey Ledger"], "domains": ["liffeyledger.example"]},
  "competitors": [
    {"name": "Harbour & Quay Accounting", "aliases": ["Harbour and Quay"], "domains": ["harbourquay.example"]}
  ]
}
```

- **Aliases:** every way the brand appears in answers. Add `&` and `and` versions, abbreviations and old names. Detection is literal.
- **Domains:** the brand's own sites. Subdomains count (`blog.x.com` matches `x.com`). `www.`, scheme, port, path and trailing slash are ignored. A lookalike (`notx.com`) does not match.

How mentions are detected from `answer_text`: a case-insensitive alias match on whole words, so "Liffey Ledger" does not match "Liffey Ledgers". When aliases overlap, the longer one wins, so a competitor called "Liffey Ledger Tax Clinic" is not also counted as "Liffey Ledger". Limits to know:

- Misspellings, possessives written without the apostrophe, and transliterations are missed unless added as aliases.
- Brand names that are ordinary words ("Summit", "Ledger") will match unrelated text. Use the full name, and check a sample of matches by hand. The script warns about aliases under 4 letters.
- Brands not in the config are invisible in text mode. They are only counted from a `brands_named` list.
- Position from text counts configured brands only. From a `brands_named` list it is the list order.

If both `answer_text` and `brands_named` are present, text is used (`--mentions auto`), because the alias rules are yours and are the same across vendors. Use `--mentions list` to use the tracker's own extraction instead.

## Step 4: Run the script

```
python3 scripts/analyze.py answers.csv --brands brands.json --out-md report.md --out-csv cells.csv
```

Options: `--period-by column|month|date`, `--compare EARLIER LATER` (default: the last two periods), `--mentions auto|text|list`. Python 3 standard library only.

The script drops exact duplicate rows, skips malformed rows (missing required values, bad dates, too many cells) and lists them, warns when the same run key appears twice with different content, and stops with a clear error on an empty file or missing columns. Run the tests with `python3 -m unittest scripts/test_analyze.py`.

## Step 5: Read the report

Every answer falls into exactly one of four outcomes for each brand:

| Outcome | Meaning |
|---|---|
| Named and cited | The answer names the brand and cites its site |
| Named, not cited | The answer names the brand; its site is not among the sources |
| Cited, not named | The brand's site is a source, but the brand is not named |
| Absent | Neither |

Within "cited, not named", the report separates answers that named a different brand: **read but credited someone else**. This split matters because a citation count alone looks like success. In the monitoring data the Census published (aivisibilitycensus.com/keyword-research-for-ai-search/), 494 of 3,832 answers (12.9%) used one firm's own website as a source while naming a different firm in the text.

How to read the rest:

- **Rates and intervals.** "33% (25-43%)" means 33% of answers, with a 95% Wilson score interval of 25% to 43%. The Wilson interval behaves sensibly at 0%, 100% and small counts, where the usual plus-or-minus formula does not.
- **Question x engine cells** show runs naming the brand over runs, such as 2/3. A mixed cell (some runs yes, some no) means a single check would have given a different answer from the next one. Cells with fewer than 3 runs are marked. Do not compare cells against each other or across periods: 1/3 to 2/3 is one answer.
- **"(thin)"** marks any aggregate under 30 answers. Report it, but do not compare it.
- **Period comparison.** For each group (all answers, each engine, each intent) the report gives both rates, the change in points, a two-proportion test p-value and a reading. It says "change outside noise" only when p<0.05 and the two intervals do not overlap, "provisional" when the test passes but the intervals overlap, and "within noise" otherwise. Say it plainly: a change within noise is not evidence of a change, in either direction.
- **Why to be cautious even then.** Runs of the same question are not independent samples, so true uncertainty is wider than the intervals show. Many rows are tested at once, so one in twenty can cross p<0.05 by chance. Engine updates between periods change everything at once.
- **Questions never naming the brand** are listed separately with who was named instead. These are candidate content gaps: for each, list the 3 to 5 sub-questions an AI tool would need answered first (question-set-builder, Step 4) and check whether the site answers them. Publishing pages that answer those sub-questions is a reasonable bet, not a proven fix [U]. Evidence grades: see ../tactics/EVIDENCE.md.

When writing up results for someone else, quote counts with rates ("26 of 108 answers, 24%"), keep the intervals, and keep thin and within-noise results labeled as such. `references/methods.md` has the formulas and the reasoning behind the thresholds.

## Step 6: Output

1. **The markdown report** (`report.md`): data summary, the brand by period, all brands by period, by engine, by intent, the period comparison, the question x engine grid, the read-but-credited-someone-else table, never-named questions, and thin-data flags.
2. **The cell CSV** (`cells.csv`): one row per period x question x engine x brand, with runs, counts, rates, Wilson bounds, the four outcomes, mean position and a thin-cell flag. Use it for charts or a spreadsheet.

See `examples/example-report.md` for a full run on synthetic data (`examples/sample-answers.csv`, `examples/brands.json`).

## What this skill does not do

- It does not query AI engines or collect answers.
- It does not estimate how often any question is asked. As far as the Census knows, no AI assistant publishes prompt volumes.
- It cannot explain why a rate changed. It can only say whether the change is larger than run-to-run noise.
- It cannot see inside a tracker's sampling, model settings or brand extraction. Those stay a black box unless the vendor documents them.
- It does not combine the measures into a single score.
- It does not catch mentions its aliases do not cover.

## Credit

Method from the AI Visibility Census, aivisibilitycensus.com, licensed under CC BY 4.0. This credit is for the person installing the skill. Do not add it to the reports or other output the skill produces.

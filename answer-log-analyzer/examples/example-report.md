# Example: Dublin accounting firm (synthetic data)

A real run of `scripts/analyze.py` on synthetic data. Liffey Ledger Accountants and its competitors are fictional, and so are their domains (`.example` is a reserved test domain). 12 questions, 3 engines, 3 runs per question per engine, on two check dates (2026-09-14 and 2026-10-12). One exact duplicate row was planted to show it being dropped.

Command, run from the skill folder:

```
python3 scripts/analyze.py examples/sample-answers.csv --brands examples/brands.json --out-md report.md --out-csv examples/example-cells.csv
```

What this example shows: the brand rose from 24% to 33% of answers, and on Perplexity from 31% to 47%, yet none of these changes is outside noise. ACC10 and ACC12 never named the brand, and ACC12 cited its site in 6 of 18 answers while naming competitors.

Everything below the line is the unedited script output.

---

# AI answer log report: Liffey Ledger Accountants

## Data

- Answers file: `examples/sample-answers.csv`
- Rows read: 217. Exact duplicates dropped: 1. Rows skipped as malformed: 0.
- Answers analyzed: 216, over 12 question(s), 3 engine(s) (chatgpt, copilot, perplexity), 2 period(s) (2026-09, 2026-10).
- Mentions detected from: answer_text, by case-insensitive whole-word alias match. Position counts only configured brands, and brands not in the config are not detected.
- Citations: from `cited_urls`, matched by domain and subdomain.
- Runs per question x engine x period cell: 3 run(s) in 72 cell(s).

Rates show the share of answers, with a 95% Wilson interval in parentheses. "(thin)" marks any aggregate under 30 answers: too few to compare. Cells with fewer than 3 runs are marked with `*`.

## Liffey Ledger Accountants by period

| Period | Answers | Named | Cited | Named and cited | Named not cited | Cited not named | of which named another brand | Absent | Mean position when named | Named first |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09 | 108 | 24% (17-33%) | 33% (25-43%) | 14 | 12 | 22 | 16 | 60 | 1.9 | 9 of 26 |
| 2026-10 | 108 | 33% (25-43%) | 33% (25-43%) | 21 | 15 | 15 | 14 | 57 | 1.8 | 16 of 36 |

Named and cited + named not cited + cited not named + absent = answers. "Named another brand" is the read-but-credited-someone-else case: the site was a source, and the answer named a different brand but not this one.

## All configured brands by period

| Brand | Named 2026-09 | Cited 2026-09 | Named 2026-10 | Cited 2026-10 |
|---|---|---|---|---|
| Liffey Ledger Accountants (yours) | 24% (17-33%) | 33% (25-43%) | 33% (25-43%) | 33% (25-43%) |
| Harbour & Quay Accounting | 54% (44-63%) | 31% (23-41%) | 51% (42-60%) | 25% (18-34%) |
| Grangegorman Tax Partners | 54% (44-63%) | 32% (24-42%) | 48% (39-57%) | 34% (26-44%) |
| Northside Numbers | 59% (50-68%) | 37% (29-46%) | 57% (48-66%) | 32% (24-42%) |

## Liffey Ledger Accountants by engine

| Engine | Named 2026-09 | Cited 2026-09 | Named 2026-10 | Cited 2026-10 |
|---|---|---|---|---|
| chatgpt | 28% (16-44%), n=36 | 39% (25-55%) | 33% (20-50%), n=36 | 39% (25-55%) |
| copilot | 14% (6-29%), n=36 | 33% (20-50%) | 19% (10-35%), n=36 | 25% (14-41%) |
| perplexity | 31% (18-47%), n=36 | 28% (16-44%) | 47% (32-63%), n=36 | 36% (22-52%) |

## Liffey Ledger Accountants by intent

| Intent | Named 2026-09 | Cited 2026-09 | Named 2026-10 | Cited 2026-10 |
|---|---|---|---|---|
| comparison | 11% (3-33%), n=18 (thin) | 17% (6-39%) | 28% (12-51%), n=18 (thin) | 28% (12-51%) |
| educational | 6% (1-26%), n=18 (thin) | 50% (29-71%) | 0% (0-18%), n=18 (thin) | 44% (25-66%) |
| specific need | 17% (6-39%), n=18 (thin) | 17% (6-39%) | 17% (6-39%), n=18 (thin) | 17% (6-39%) |
| vendor selection | 37% (25-50%), n=54 | 39% (27-52%) | 52% (39-65%), n=54 | 37% (25-50%) |

## Period comparison

Comparing 2026-09 with 2026-10 for Liffey Ledger Accountants. A change is called "outside noise" only when a two-proportion test gives p<0.05 and the two 95% intervals do not overlap. Anything else is reported as within noise or provisional.

| Group | Measure | 2026-09 | 2026-10 | Change | p | Reading |
|---|---|---|---|---|---|---|
| All answers | Named | 24% (17-33%), n=108 | 33% (25-43%), n=108 | +9 pts | 0.133 | within noise |
| All answers | Cited | 33% (25-43%), n=108 | 33% (25-43%), n=108 | +0 pts | 1.000 | within noise |
| Engine: chatgpt | Named | 28% (16-44%), n=36 | 33% (20-50%), n=36 | +6 pts | 0.609 | within noise |
| Engine: chatgpt | Cited | 39% (25-55%), n=36 | 39% (25-55%), n=36 | +0 pts | 1.000 | within noise |
| Engine: copilot | Named | 14% (6-29%), n=36 | 19% (10-35%), n=36 | +6 pts | 0.527 | within noise |
| Engine: copilot | Cited | 33% (20-50%), n=36 | 25% (14-41%), n=36 | -8 pts | 0.437 | within noise |
| Engine: perplexity | Named | 31% (18-47%), n=36 | 47% (32-63%), n=36 | +17 pts | 0.147 | within noise |
| Engine: perplexity | Cited | 28% (16-44%), n=36 | 36% (22-52%), n=36 | +8 pts | 0.448 | within noise |
| Intent: comparison | Named | 11% (3-33%), n=18 | 28% (12-51%), n=18 | +17 pts | n/a | too thin to compare |
| Intent: comparison | Cited | 17% (6-39%), n=18 | 28% (12-51%), n=18 | +11 pts | n/a | too thin to compare |
| Intent: educational | Named | 6% (1-26%), n=18 | 0% (0-18%), n=18 | -6 pts | n/a | too thin to compare |
| Intent: educational | Cited | 50% (29-71%), n=18 | 44% (25-66%), n=18 | -6 pts | n/a | too thin to compare |
| Intent: specific need | Named | 17% (6-39%), n=18 | 17% (6-39%), n=18 | +0 pts | n/a | too thin to compare |
| Intent: specific need | Cited | 17% (6-39%), n=18 | 17% (6-39%), n=18 | +0 pts | n/a | too thin to compare |
| Intent: vendor selection | Named | 37% (25-50%), n=54 | 52% (39-65%), n=54 | +15 pts | 0.121 | within noise |
| Intent: vendor selection | Cited | 39% (27-52%), n=54 | 37% (25-50%), n=54 | -2 pts | 0.843 | within noise |

Read this cautiously. Repeated runs of the same question are not independent samples, so the real uncertainty is wider than these intervals suggest, and with many rows a few will cross p<0.05 by chance. Question x engine cells (a few runs each) are never compared on their own. The test says whether a difference is larger than run-to-run noise. It cannot say why it happened.

## Question x engine runs naming Liffey Ledger Accountants

Each cell is runs naming the brand / runs. `*` = fewer than 3 runs.

| Question | Intent | chatgpt 2026-09 | chatgpt 2026-10 | copilot 2026-09 | copilot 2026-10 | perplexity 2026-09 | perplexity 2026-10 |
|---|---|---|---|---|---|---|---|
| ACC01 | vendor selection | 1/3 | 2/3 | 0/3 | 1/3 | 2/3 | 2/3 |
| ACC02 | vendor selection | 1/3 | 0/3 | 0/3 | 0/3 | 1/3 | 3/3 |
| ACC03 | vendor selection | 1/3 | 2/3 | 1/3 | 0/3 | 2/3 | 2/3 |
| ACC04 | vendor selection | 0/3 | 1/3 | 2/3 | 2/3 | 2/3 | 3/3 |
| ACC05 | vendor selection | 2/3 | 1/3 | 1/3 | 1/3 | 2/3 | 2/3 |
| ACC06 | vendor selection | 1/3 | 2/3 | 0/3 | 1/3 | 1/3 | 3/3 |
| ACC07 | comparison | 1/3 | 2/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| ACC08 | comparison | 1/3 | 2/3 | 0/3 | 1/3 | 0/3 | 0/3 |
| ACC09 | specific need | 1/3 | 0/3 | 1/3 | 1/3 | 1/3 | 2/3 |
| ACC10 | specific need | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| ACC11 | educational | 1/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| ACC12 | educational | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |

37 of 72 cells are mixed (named in some runs, not others). A mixed cell means one run would have given a different answer from the next.

## Read but credited someone else

30 answer(s) used a Liffey Ledger Accountants page as a source and named another brand, but not Liffey Ledger Accountants.

| Question | Engine | Answers | Named instead | Your host cited |
|---|---|---|---|---|
| ACC01 | chatgpt | 1 | Northside Numbers (1) | liffeyledger.example |
| ACC01 | copilot | 1 | Harbour & Quay Accounting (1), Northside Numbers (1) | liffeyledger.example |
| ACC02 | chatgpt | 2 | Harbour & Quay Accounting (2), Grangegorman Tax Partners (2), Northside Numbers (1) | liffeyledger.example |
| ACC02 | copilot | 1 | Harbour & Quay Accounting (1), Grangegorman Tax Partners (1), Northside Numbers (1) | liffeyledger.example |
| ACC02 | perplexity | 1 | Harbour & Quay Accounting (1), Grangegorman Tax Partners (1), Northside Numbers (1) | liffeyledger.example |
| ACC03 | chatgpt | 1 | Harbour & Quay Accounting (1) | liffeyledger.example |
| ACC03 | copilot | 1 | Harbour & Quay Accounting (1), Grangegorman Tax Partners (1) | liffeyledger.example |
| ACC04 | chatgpt | 3 | Northside Numbers (3), Harbour & Quay Accounting (2), Grangegorman Tax Partners (1) | liffeyledger.example |
| ACC04 | copilot | 1 | Grangegorman Tax Partners (1) | liffeyledger.example |
| ACC05 | copilot | 1 | Harbour & Quay Accounting (1) | liffeyledger.example |
| ACC05 | perplexity | 1 | Harbour & Quay Accounting (1), Grangegorman Tax Partners (1) | liffeyledger.example |
| ACC07 | copilot | 1 | Grangegorman Tax Partners (1), Northside Numbers (1) | liffeyledger.example |
| ACC07 | perplexity | 1 | Harbour & Quay Accounting (1), Grangegorman Tax Partners (1), Northside Numbers (1) | liffeyledger.example |
| ACC08 | chatgpt | 1 | Harbour & Quay Accounting (1), Grangegorman Tax Partners (1) | liffeyledger.example |
| ACC10 | copilot | 2 | Grangegorman Tax Partners (2), Northside Numbers (2), Harbour & Quay Accounting (1) | blog.liffeyledger.example |
| ACC11 | chatgpt | 1 | Northside Numbers (1) | liffeyledger.example |
| ACC11 | copilot | 4 | Northside Numbers (4) | blog.liffeyledger.example, liffeyledger.example |
| ACC11 | perplexity | 2 | Grangegorman Tax Partners (2) | blog.liffeyledger.example, liffeyledger.example |
| ACC12 | chatgpt | 1 | Northside Numbers (1) | liffeyledger.example |
| ACC12 | copilot | 3 | Northside Numbers (1), Harbour & Quay Accounting (1), Grangegorman Tax Partners (1) | liffeyledger.example |

## Questions where Liffey Ledger Accountants was never named

Candidate content gaps. For each, list the 3 to 5 sub-questions an AI tool would need answered first (question-set-builder, Step 4) and check whether the site answers them.

| Question | Intent | Text | Answers | Named instead (answers) | Answers citing your site |
|---|---|---|---|---|---|
| ACC10 | specific need | Which Dublin accountants do fixed-fee monthly bookkeeping under 300 euro? | 18 | Harbour & Quay Accounting (12), Grangegorman Tax Partners (12), Northside Numbers (12) | 2 |
| ACC12 | educational | What should I look for when choosing an accountant in Dublin? | 18 | Harbour & Quay Accounting (8), Northside Numbers (6), Grangegorman Tax Partners (5) | 6 |

## Thin data

- Cells with fewer than 3 runs: 0 of 72.
- Engine or intent aggregates under 30 answers: 2026-09 / comparison (n=18); 2026-09 / educational (n=18); 2026-09 / specific need (n=18); 2026-10 / comparison (n=18); 2026-10 / educational (n=18); 2026-10 / specific need (n=18).


---
name: geo-check
description: Check in one command whether AI search engines can reach and read a page. Tests the page response, noindex and snippet limits, robots.txt rules for 11 search and AI crawler tokens, whether the text arrives without JavaScript, structured data against the visible page, and whether a firewall answers AI crawler user agents differently. Returns findings in four tiers, each with an evidence grade, and no score. Use when someone asks for a GEO audit, an AI search or AI visibility check of a URL, asks "can ChatGPT see my site", "why is AI not citing my page", or wants a quick first look before deeper work.
---

# GEO check

One command, one page, a short list of findings. This is the place to start: it finds the things that stop an AI engine from using a page at all, and points to the other skills in this repo for everything it cannot see from outside.

It gives no score. A page blocked from ChatGPT's search crawler is not "85 out of 100", and no audit score has been shown to predict whether a business gets named in AI answers. The AI Visibility Census is testing that claim on live data (experiment SV-001 on its [experiments page](https://aivisibilitycensus.com/experiments/)); until there is a result, this skill reports findings and nothing more.

## Run it

```
python3 scripts/geo_check.py https://example.com/the-page-that-matters
```

Options: `--out-md report.md`, `--json-out report.json`, `--no-probe` (skip the crawler user-agent requests), `--timeout`, `--badge` (when nothing blocks, print a README badge line that states "0 blocking" and the date; it is a count for one page on one day, not a rating).

The repository root also works as a GitHub Action (`uses: aivisibilitycensus/geo-skills@v1` with a `urls` input), which writes the findings to the job summary and fails the job on a blocking finding.

Pick the page, not the homepage by habit. Check the page you want named: the service page, the pricing page, the article. Run it once per page for up to five pages, then stop and read the findings before checking more.

The script needs to reach the site, so it runs where there is open network access (the user's machine, Claude Code, a CI job). If the environment blocks outside requests, say so and give the user the command to run.

## What it checks

| Check | A finding means | Evidence |
|---|---|---|
| Page request | The page does not return 200 | [P] |
| Indexing | `noindex` in the robots meta tag or `X-Robots-Tag` header | [P] |
| Snippets | `nosnippet` or `max-snippet:0` | [P] |
| robots.txt | A search or AI crawler token is blocked from this page, or robots.txt cannot be read | [P] |
| Text in raw HTML | Under 100 words arrive without JavaScript | [S] |
| Structured data | A JSON-LD block does not parse, or says something the page does not show | [P] |
| Firewall or CDN | A request with an AI crawler token in the user agent gets a different status | [U] |
| Canonical, redirects | The canonical points elsewhere, or there is more than one redirect | None claimed |
| llms.txt | Recorded as present or absent. Never a finding | [U] |

Grades come from `tactics/EVIDENCE.md`: [P] the platform's own documentation says so, [S] a published study with a stated method, [U] untested.

## Reading the result

Four tiers, in this order:

- **BLOCKS**: stops an engine from using the page. Fix these first. Nothing else matters for that engine until they are fixed.
- **FIX**: likely to cost you.
- **CHECK**: cannot be decided from outside. Someone has to look.
- **INFO**: recorded, no action implied. A block on a training crawler (GPTBot, ClaudeBot, Google-Extended) is here: it is the site owner's choice and does not affect search answers.

When you report to the user:

1. Lead with the count per tier and the blocking findings, in plain words.
2. For each finding give what was found, what to do and the evidence grade. Do not turn the tiers into a number or a percentage.
3. Say what was not checked. The script prints that list; keep it in the answer.
4. Do not promise an outcome. Fixing a BLOCKS finding makes a page eligible. It does not make an engine name it.

## Limits

- **One address, no JavaScript.** The script sees what a simple crawler sees from wherever it runs. A site that serves different content by country, or that builds the page in the browser, will look different to a person.
- **The firewall check is a hint.** It sends a short user agent containing the crawler's token from the machine it runs on. Real crawlers use their full user agent and their own IP ranges, and a firewall may treat them differently in either direction. Confirm with server logs using ai-crawler-log-check.
- **robots.txt rules say what a crawler is asked to do.** Operators document that their search crawlers follow them; several say user-triggered fetches may not.
- **It does not measure visibility.** Whether engines name the business takes logged answers: question-set-builder, then answer-collector, then answer-log-analyzer.

## Where to go next

| Finding | Next skill |
|---|---|
| Structured data mismatches | schema-parity-checker, for the full field-by-field list and `--render` |
| Firewall or crawler questions | ai-crawler-log-check, on real access logs |
| Planning a replatform | geo-migration-guard |
| "Fine, but are we named?" | question-set-builder, answer-collector, answer-log-analyzer |
| "Will changing X help?" | geo-experiment-kit |

## Files

- `scripts/geo_check.py`: the check. Python 3, standard library only.
- `scripts/pagekit.py`: shared page fetch and parse helper (the same file as in schema-parity-checker).
- `tests/test_geo_check.py`: 13 tests against a local test server.
- `examples/output-report.md`: real output for a fictional bike shop page with three planted problems.

# Example: synthetic log for an invented cleaning company site

An example run of the ai-crawler-log-check skill. Everything here is synthetic: the site is invented, the log was written by hand for testing, and every IP is a documentation-only (RFC 5737, RFC 3849) or private address. The range files in `sample-ranges/` are test fixtures, not real vendor ranges. Do not read anything about real crawler behavior into these numbers.

## Inputs

- Log: `sample-synthetic-access.log` (Nginx/Apache combined format, 30 lines plus one comment line; includes one garbage line and one line with an empty request).
- Ranges: `sample-ranges/` (test fixtures for GPTBot, Anthropic, PerplexityBot, Google common crawlers, Bingbot). No fixture for OAI-SearchBot, ChatGPT-User, Applebot, CCBot or Meta, to show how missing files are handled.
- DNS off, so the run is reproducible offline. The DNS path is covered by the mocked tests in `tests/`.

## Command

```
python3 scripts/crawler_check.py examples/sample-synthetic-access.log \
  --ranges-dir examples/sample-ranges --no-dns \
  --out-md examples/output-report.md --out-csv examples/output-summary.csv --out-hits examples/output-hits.csv
```

## Output: report (verbatim, `output-report.md`)

````markdown
# AI crawler log check

## Inputs

- `sample-synthetic-access.log` (combined)
- Log lines read: 30; malformed and skipped: 1 (first at line 30)
- Lines whose user agent matched a known crawler: 26
- DNS verification: off (--no-dns)
- Range files loaded:
  - `anthropic-bots.json`: 1 prefixes, creationTime 2026-10-01T00:00:00Z, note: TEST FIXTURE
  - `bing-bingbot.json`: 1 prefixes, creationTime 2026-10-01T00:00:00Z, note: TEST FIXTURE
  - `google-common-crawlers.json`: 2 prefixes, creationTime 2026-10-01T00:00:00Z, note: TEST FIXTURE
  - `openai-gptbot.json`: 1 prefixes, creationTime 2026-10-01T00:00:00Z, note: TEST FIXTURE
  - `perplexity-perplexitybot.json`: 1 prefixes, creationTime 2026-10-01T00:00:00Z, note: TEST FIXTURE

## Summary by crawler

| Crawler | Vendor | Purpose | Hits | Verified | Failed (likely spoofed) | Unverifiable | First seen | Last seen |
|---|---|---|---|---|---|---|---|---|
| GPTBot | OpenAI | training | 7 | 4 | 3 | 0 | 2026-10-14 03:12 UTC | 2026-10-15 22:05 UTC |
| ClaudeBot | Anthropic | training | 4 | 3 | 1 | 0 | 2026-10-16 11:30 UTC | 2026-10-17 01:00 UTC |
| Googlebot | Google | search | 4 | 2 | 2 | 0 | 2026-10-18 06:00 UTC | 2026-10-18 06:10 UTC |
| PerplexityBot | Perplexity | search | 2 | 1 | 1 | 0 | 2026-10-17 15:00 UTC | 2026-10-17 15:00 UTC |
| Bingbot | Microsoft | search | 2 | 2 | 0 | 0 | 2026-10-19 08:00 UTC | 2026-10-19 08:00 UTC |
| OAI-SearchBot | OpenAI | search | 1 | 0 | 0 | 1 | 2026-10-16 09:00 UTC | 2026-10-16 09:00 UTC |
| ChatGPT-User | OpenAI | user-triggered fetch | 1 | 0 | 0 | 1 | 2026-10-16 09:00 UTC | 2026-10-16 09:00 UTC |
| Claude-User | Anthropic | user-triggered fetch | 1 | 1 | 0 | 0 | 2026-10-17 14:22 UTC | 2026-10-17 14:22 UTC |
| Applebot | Apple | search | 1 | 0 | 0 | 1 | 2026-10-20 12:00 UTC | 2026-10-20 12:00 UTC |
| CCBot | Common Crawl | open web crawl archive | 1 | 0 | 0 | 1 | 2026-10-20 12:00 UTC | 2026-10-20 12:00 UTC |
| Meta-ExternalAgent | Meta | training and indexing | 1 | 0 | 0 | 1 | 2026-10-21 12:00 UTC | 2026-10-21 12:00 UTC |
| Bytespider | ByteDance | not documented by vendor | 1 | 0 | 0 | 1 | 2026-10-21 13:00 UTC | 2026-10-21 13:00 UTC |

## Detail

### GPTBot

- Status codes (all hits): 200: 4, 403: 1, 404: 2
- robots.txt / llms.txt fetches: robots.txt 1 (verified 1)
- Top paths: `/pricing/` 2; `/robots.txt` 1; `/services/office-cleaning/` 1; `/old-page/` 1; `/wp-login.php` 1
- Why not verified: not in openai-gptbot.json (3)
- Top IPs that failed verification: 203.0.113.77 (3)

### ClaudeBot

- Status codes (all hits): 200: 3, 404: 1
- robots.txt / llms.txt fetches: llms.txt 1 (verified 1), robots.txt 1 (verified 1)
- Top paths: `/services/office-cleaning/` 2; `/robots.txt` 1; `/llms.txt` 1
- Why not verified: not in anthropic-bots.json (1)
- Top IPs that failed verification: 203.0.113.9 (1)

### Googlebot

- Status codes (all hits): 200: 4
- robots.txt / llms.txt fetches: none
- Top paths: `/pricing/` 2; `/` 1; `/contact/` 1
- Why not verified: not in google-common-crawlers.json (2)
- Top IPs that failed verification: 198.51.100.200 (1), 2001:db8:dead::1 (1)

### PerplexityBot

- Status codes (all hits): 200: 2
- robots.txt / llms.txt fetches: none
- Top paths: `/faq/` 2
- Why not verified: not in perplexity-perplexitybot.json (1)
- Top IPs that failed verification: 172.16.5.5 (1)

### Bingbot

- Status codes (all hits): 200: 1, 301: 1
- robots.txt / llms.txt fetches: robots.txt 1 (verified 1)
- Top paths: `/robots.txt` 1; `/services/` 1

### OAI-SearchBot

- Status codes (all hits): 200: 1
- robots.txt / llms.txt fetches: llms.txt 1 (verified 0)
- Top paths: `/llms.txt` 1
- Why not verified: range file not available (use --fetch-ranges) (1)

### ChatGPT-User

- Status codes (all hits): 200: 1
- robots.txt / llms.txt fetches: none
- Top paths: `/about/` 1
- Why not verified: range file not available (use --fetch-ranges) (1)

### Claude-User

- Status codes (all hits): 200: 1
- robots.txt / llms.txt fetches: none
- Top paths: `/faq/` 1

### Applebot

- Status codes (all hits): 200: 1
- robots.txt / llms.txt fetches: none
- Top paths: `/` 1
- Why not verified: range file missing and --no-dns set (1)

### CCBot

- Status codes (all hits): 200: 1
- robots.txt / llms.txt fetches: robots.txt 1 (verified 0)
- Top paths: `/robots.txt` 1
- Why not verified: range file missing and --no-dns set (1)

### Meta-ExternalAgent

- Status codes (all hits): 200: 1
- robots.txt / llms.txt fetches: none
- Top paths: `/blog/` 1
- Why not verified: no published range file; build meta-as32934.json from the vendor's ASN routes (1)

### Bytespider

- Status codes (all hits): 200: 1
- robots.txt / llms.txt fetches: none
- Top paths: `/blog/` 1
- Why not verified: vendor publishes no verification method (1)

## What this report cannot show

- A failed check means the IP was not in the vendor's published list (or failed reverse DNS) when checked. Range files change; a stale cached file can fail genuine traffic.
- Unverifiable is not the same as genuine. These hits are counted by user agent only.
- Crawling is not citation. These logs show fetches, not whether any AI answer used the page.
- If the logs come from an origin server behind a CDN or proxy, the IP may be the proxy's, and every check will fail. Log the real client IP.
````

## Output: summary CSV (verbatim, `output-summary.csv`)

```
crawler,vendor,purpose,hits,verified,failed,unverifiable,first_seen,last_seen,robots_txt,llms_txt,status_2xx,status_3xx,status_4xx,status_5xx
GPTBot,OpenAI,training,7,4,3,0,2026-10-14T03:12:09+00:00,2026-10-15T22:05:02+00:00,1,0,4,0,3,0
ClaudeBot,Anthropic,training,4,3,1,0,2026-10-16T11:30:00+00:00,2026-10-17T01:00:00+00:00,1,1,3,0,1,0
Googlebot,Google,search,4,2,2,0,2026-10-18T06:00:00+00:00,2026-10-18T06:10:09+00:00,0,0,4,0,0,0
PerplexityBot,Perplexity,search,2,1,1,0,2026-10-17T15:00:00+00:00,2026-10-17T15:00:30+00:00,0,0,2,0,0,0
Bingbot,Microsoft,search,2,2,0,0,2026-10-19T08:00:00+00:00,2026-10-19T08:00:03+00:00,1,0,1,1,0,0
OAI-SearchBot,OpenAI,search,1,0,0,1,2026-10-16T09:00:00+00:00,2026-10-16T09:00:00+00:00,0,1,1,0,0,0
ChatGPT-User,OpenAI,user-triggered fetch,1,0,0,1,2026-10-16T09:00:05+00:00,2026-10-16T09:00:05+00:00,0,0,1,0,0,0
Claude-User,Anthropic,user-triggered fetch,1,1,0,0,2026-10-17T14:22:00+00:00,2026-10-17T14:22:00+00:00,0,0,1,0,0,0
Applebot,Apple,search,1,0,0,1,2026-10-20T12:00:00+00:00,2026-10-20T12:00:00+00:00,0,0,1,0,0,0
CCBot,Common Crawl,open web crawl archive,1,0,0,1,2026-10-20T12:00:00+00:00,2026-10-20T12:00:00+00:00,1,0,1,0,0,0
Meta-ExternalAgent,Meta,training and indexing,1,0,0,1,2026-10-21T12:00:00+00:00,2026-10-21T12:00:00+00:00,0,0,1,0,0,0
Bytespider,ByteDance,not documented by vendor,1,0,0,1,2026-10-21T13:00:00+00:00,2026-10-21T13:00:00+00:00,0,0,1,0,0,0
```

## How to read this run

- GPTBot: 7 hits claimed the user agent; 4 came from inside the (fixture) GPTBot range and 3 came from 203.0.113.77, which also probed `/wp-login.php` and `/.env`. A user-agent-only count would report 7 GPTBot visits, including a scanner.
- Googlebot: one verified hit is IPv6, showing IPv6 range matching. The two failures would get a reverse DNS check if DNS were on.
- OAI-SearchBot, ChatGPT-User, Applebot, CCBot and Meta-ExternalAgent are unverifiable here only because their range files were not supplied and DNS was off. With `--fetch-ranges` (and DNS on, for Apple and Common Crawl) they would be checked.
- Bytespider is unverifiable in every run: no vendor verification method was found.
- ClaudeBot fetched `/llms.txt` and got a 404, so the file does not exist on this (invented) site.

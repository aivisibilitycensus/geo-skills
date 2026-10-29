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

---
name: ai-crawler-log-check
description: Analyze server or CDN access logs for AI and search crawler activity (GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-User, PerplexityBot, Googlebot, Bingbot, Applebot, CCBot, Meta and others) and verify each hit against the vendor's published IP ranges or reverse DNS instead of trusting the user agent. Use when someone asks whether AI bots are crawling their site, wants to check for spoofed bot traffic, or wants a crawler report from Apache, Nginx or CDN logs.
---

# AI crawler log check

Reads access logs, finds requests whose user agent claims to be a known AI or search crawler, and checks whether each request really came from that vendor. Anyone can send `User-Agent: GPTBot`. Counting user agents alone counts the spoofers too. This skill separates hits into three groups and never merges them:

- **Verified:** the IP is inside the vendor's published ranges, or its reverse DNS ends in the vendor's domain and forward DNS confirms it.
- **Failed verification (likely spoofed):** a method exists, it was run, and the IP did not pass.
- **Unverifiable:** the vendor publishes no method, the range file isn't available, or the method needs DNS and DNS was turned off. Not a pass and not a fail.

The script is `scripts/crawler_check.py`. Python 3.8+, standard library only.

## Step 1: Get the right logs

Ask for:

- **The log files.** Apache or Nginx "combined" format, or a CSV export. `.gz` files are fine. Several files at once are fine.
- **Where the logs were recorded.** This matters more than anything else. If the site sits behind a CDN or reverse proxy and the logs come from the origin server, the IP in each line may be the proxy's, not the crawler's. Then every check fails. Use the CDN's own logs, or origin logs that record the real client IP (for example from a forwarded-for header the proxy sets).
- **The date range covered.** At least a week is useful; crawlers visit unevenly.

If the export is from a CDN or log tool, map its columns to the CSV header `timestamp,ip,method,path,status,user_agent`. `references/crawlers.md` has the mapping for Cloudflare Logpush (field names checked against Cloudflare's docs). For any other provider, look up its current field names rather than guessing.

## Step 2: Get current IP ranges

Vendor range files change often. Before a real analysis, download fresh copies:

```
python3 scripts/crawler_check.py access.log --fetch-ranges --ranges-dir ranges
```

This saves each file into `ranges/` under a fixed local name. Later runs can reuse the folder offline with `--ranges-dir ranges`. If a download fails, the script says which one and carries on; hits for that vendor become unverifiable, not failed.

The vendor sources, and which method each vendor publishes, are in `references/crawlers.md`. Summary as checked on 2026-10-29:

| Vendor | Bots classified | Verification published |
|---|---|---|
| OpenAI | GPTBot (training), OAI-SearchBot (search), ChatGPT-User (user-triggered), OAI-AdsBot (ads) | One IP range JSON per bot |
| Anthropic | ClaudeBot (training), Claude-SearchBot (search), Claude-User (user-triggered) | One IP range JSON covering all three |
| Perplexity | PerplexityBot (search), Perplexity-User (user-triggered) | One IP range JSON per bot |
| Google | Googlebot, GoogleOther, Google-CloudVertexBot | IP range JSON and reverse DNS |
| Microsoft | Bingbot | IP range JSON and reverse DNS |
| Apple | Applebot | IP range JSON and reverse DNS |
| Common Crawl | CCBot | IP range JSON and reverse DNS (IPv4 only for DNS) |
| Meta | meta-externalagent, meta-externalfetcher, meta-webindexer, meta-externalads, facebookexternalhit | ASN routes via whois; no JSON. Build the file yourself (see references) |
| ByteDance | Bytespider | None found. Always unverifiable |

Two names that look like crawlers are not: **Google-Extended** and **Applebot-Extended** are robots.txt tokens with no user agent of their own (both vendors say so). They never appear in logs. A request using either as its user agent did not come from Google or Apple.

## Step 3: Run the check

```
python3 scripts/crawler_check.py access.log access.log.1.gz \
  --ranges-dir ranges --out-md report.md --out-csv summary.csv --out-hits hits.csv
```

Options:

- `--format auto|combined|csv`: auto-detects by default (a header containing `timestamp` and `user_agent` means CSV).
- `--no-dns`: skip reverse DNS. Use it offline or for very large logs. Vendors that rely on DNS are then checked by range file only; if that file is missing, their hits become unverifiable.
- `--dns-timeout`: seconds per lookup (default 3). A timeout counts as unverifiable, never as failed. Results are cached per IP.
- `--top N`: how many top paths and failing IPs to list.

Malformed lines are counted and skipped (the report gives the first line numbers). Lines starting with `#` are treated as comments. IPv6, bracketed addresses, IPv4-mapped IPv6 and `ip:port` forms are handled.

## Step 4: Read the report

For each crawler the report gives: hits, verified, failed, unverifiable, first and last seen, status code mix, robots.txt and llms.txt fetches, top paths, the reason hits were not verified, and the IPs that failed most.

How to read it:

1. **Start with the failed column.** Those hits are almost certainly not the bot they claim to be. Look at their paths. Probing for `/wp-login.php` or `/.env` under a GPTBot user agent is a scanner, not OpenAI.
2. **Report verified numbers as the crawler's activity.** Report unverifiable numbers separately, labeled as "claimed by user agent, not verified".
3. **Check the status mix for verified hits.** Verified crawlers getting many 403s or 404s means the site is blocking them or sending them to dead pages. Whether to block or allow a crawler is the site owner's decision; the report shows what is happening, not what should happen.
4. **robots.txt and llms.txt fetches** show whether a crawler looked for those files, and what status it got. A 404 on llms.txt means the file isn't there. Fetching llms.txt is not evidence that any AI system uses it.
5. **Anthropic's file is shared.** A verified ClaudeBot hit means "from an Anthropic IP"; the list does not say which of its bots uses which address.

When writing up findings, keep crawling and citation apart. A crawler fetching a page says nothing on its own about whether an AI answer named or cited the site. Pair this report with answer monitoring if that's the question.

## Step 5: Output

Hand over:

1. The markdown report (as produced; do not round or merge the three groups).
2. `summary.csv`: one row per crawler, with hits, the three verification groups, first and last seen, robots.txt and llms.txt counts, and status code classes.
3. Optionally `hits.csv`: one row per crawler hit with the verification result and the reason, for anyone who wants to check the work.
4. A short note of what was not checked: vendors whose range files were missing, whether DNS was on, and whether the IPs are true client IPs.

See `examples/worked-example.md` for a run on synthetic data.

## Tests

```
python3 -m unittest discover -s tests -v
```

The tests use a synthetic log and range files in `examples/sample-ranges/`. Those range files are test fixtures built from documentation-only IP blocks (RFC 5737 and RFC 3849). They are not vendor ranges and must never be used on real logs. The DNS tests mock the socket calls.

## What this skill does not do

- It does not tell you whether AI tools cite or recommend the site. Crawling is not citation.
- It does not keep vendor ranges current by itself. Fetch them before each real analysis; a stale file can fail genuine traffic.
- It does not verify bots it doesn't know. Unknown user agents are ignored, not reported as humans or bots.
- It does not attribute a hit to a specific Anthropic bot by IP, or verify Meta without the ASN file, or verify Bytespider at all.
- It does not block anything or edit robots.txt.
- It does not invent a score. Every number in the report is a count from the logs.

## Credit

Method from the AI Visibility Census, aivisibilitycensus.com, licensed under CC BY 4.0. This credit is for the person installing the skill. Do not add it to the reports or other output the skill produces.

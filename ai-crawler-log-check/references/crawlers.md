# Crawler reference

Checked against each vendor's own documentation on 2026-10-29. Vendors rename bots, add new ones and move files. Re-check these pages before relying on this table, and update `FAMILIES` and `RANGE_SOURCES` in `scripts/crawler_check.py` to match.

"Fetched" means the JSON file was opened on 2026-10-29 and had the format `{"creationTime": ..., "prefixes": [{"ipv4Prefix": ...} or {"ipv6Prefix": ...}]}`, which is the format the script reads.

## OpenAI

Source: https://developers.openai.com/api/docs/bots (platform.openai.com/docs/bots redirects here)

| User agent token | Purpose (vendor's words, summarized) | IP range file |
|---|---|---|
| GPTBot | Crawls content that may be used to train OpenAI's foundation models | https://openai.com/gptbot.json (fetched) |
| OAI-SearchBot | Search | https://openai.com/searchbot.json (fetched) |
| ChatGPT-User | User actions in ChatGPT; not automatic crawling | https://openai.com/chatgpt-user.json (listed on the docs page; the fetch tool returned non-text, so the format was not confirmed) |
| OAI-AdsBot | Reviews ad landing pages; not used for training | https://openai.com/adsbot.json (listed on the docs page; not fetched) |

Verification method: IP ranges only. No reverse DNS method is documented.

## Anthropic

Source: https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler

| User agent token | Purpose | IP range file |
|---|---|---|
| ClaudeBot | Collects public web content that could be used for training | https://claude.com/crawling/bots.json (fetched; one file for all three bots, IPv4 only at time of check) |
| Claude-User | Fetches pages when a Claude user's question needs it | same file |
| Claude-SearchBot | Improves search result relevance | same file |

Anthropic does publish IP addresses now. The help article says a source IP on the list indicates the crawler is coming from Anthropic. It does not split the list by bot, so the script can verify "this is Anthropic", not "this is ClaudeBot rather than Claude-User". No reverse DNS method is documented.

## Perplexity

Source: https://docs.perplexity.ai/guides/bots

| User agent token | Purpose | IP range file |
|---|---|---|
| PerplexityBot | Surfaces and links sites in Perplexity search; the page says it is not used to crawl content for foundation models | https://www.perplexity.ai/perplexitybot.json (fetched) |
| Perplexity-User | Fetches pages when a user asks a question; the page says it generally ignores robots.txt because a user triggers it | https://www.perplexity.ai/perplexity-user.json (fetched) |

## Google

Sources:
- Verification: https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot
- Crawler list: https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers

Verification: reverse DNS on the IP, hostname must end in `googlebot.com`, `google.com` or `googleusercontent.com`, then forward DNS on that hostname must return the original IP. Or match the IP against the published files.

IP range files (Google moved these; older guides cite `/static/search/apis/ipranges/googlebot.json`, which the current verification page no longer lists):

| File | Covers |
|---|---|
| https://developers.google.com/static/crawling/ipranges/common-crawlers.json (fetched) | Common crawlers, including Googlebot |
| https://developers.google.com/static/crawling/ipranges/special-crawlers.json | Special-case crawlers such as AdsBot |
| https://developers.google.com/static/crawling/ipranges/user-triggered-fetchers.json | User-triggered fetchers |
| https://developers.google.com/static/crawling/ipranges/user-triggered-fetchers-google.json | User-triggered fetchers (Google) |
| https://developers.google.com/static/crawling/ipranges/user-triggered-agents.json | User-triggered agents |

Only common-crawlers.json is wired into the script, because the crawlers it classifies (Googlebot, GoogleOther, Google-CloudVertexBot) are common crawlers.

**Google-Extended is not a crawler.** Google's crawler page says it "doesn't have a separate HTTP request user agent string". It is a robots.txt token that controls whether content crawled by existing Google user agents may be used for Gemini training and grounding. It will never appear as a user agent in logs. A log line claiming to be "Google-Extended" is not from Google.

## Microsoft (Bing)

Sources:
- Verification method: https://blogs.bing.com/webmaster/2012/08/31/how-to-verify-that-bingbot-is-bingbot (reverse DNS must end in `search.msn.com`, then forward lookup must resolve back to the same IP)
- IP list: https://www.bing.com/toolbox/bingbot.json (fetched)

The current Bing Webmaster help pages could not be read by the fetch tool, so the user agent string and purpose come from the log token `bingbot`; check current Bing documentation for any additional Microsoft crawlers.

## Apple

Source: https://support.apple.com/en-us/119829

- Applebot: Apple's crawler (search and other features). Verify with reverse DNS in `*.applebot.apple.com` plus forward confirm, or the IP list at https://search.developer.apple.com/applebot.json (fetched).
- **Applebot-Extended is not a crawler.** Apple's page says it "does not crawl webpages"; it only controls how data crawled by Applebot may be used. It will not appear as a fetching user agent.

## Common Crawl

Source: https://commoncrawl.org/ccbot

- CCBot, user agent `CCBot/2.0 (https://commoncrawl.org/faq/)`, crawls for Common Crawl's open web archive.
- Verify with reverse DNS (example hostname pattern `*.crawl.commoncrawl.org`) plus forward confirm. The page says reverse DNS is not set up over IPv6.
- IP list: https://index.commoncrawl.org/ccbot.json (named on the CCBot page; the fetch tool was refused by that host's robots.txt, so the format was not confirmed).

## Meta

Source: https://developers.facebook.com/docs/sharing/webmasters/web-crawlers

| User agent token | Purpose |
|---|---|
| meta-externalagent | Training foundation models or indexing content |
| meta-externalfetcher | Fetches individual links at a user's request; may bypass robots.txt |
| meta-webindexer | Meta AI search quality and citations |
| meta-externalads | Advertising and business products |
| facebookexternalhit | Link previews for shared URLs |

Verification: Meta publishes no JSON file. Its page says to list routes announced by AS32934:

```
whois -h whois.radb.net -- '-i origin AS32934' | grep ^route
```

To use this in the script, turn the output into `meta-as32934.json` in your ranges folder, in the same format as the vendor files:

```
whois -h whois.radb.net -- '-i origin AS32934' | grep ^route | awk '{print $2}' | python3 -c "import sys,json; print(json.dumps({'creationTime':'(your date)','prefixes':[{('ipv6Prefix' if ':' in l else 'ipv4Prefix'):l.strip()} for l in sys.stdin if l.strip()]}, indent=1))" > ranges/meta-as32934.json
```

Without that file, Meta hits are reported as unverifiable.

## ByteDance

No official ByteDance documentation for Bytespider was found (only third-party bot directories). The script matches the `Bytespider` token and always reports it as unverifiable. Check current docs.

## Mapping CDN exports to the CSV format

The script reads a CSV with the header `timestamp,ip,method,path,status,user_agent` (extra columns are ignored). Rename your export's columns to these.

Cloudflare Logpush, HTTP requests dataset (field names from https://developers.cloudflare.com/logs/logpush/logpush-job/datasets/zone/http_requests/, checked 2026-10-29):

| CSV column | Cloudflare field |
|---|---|
| timestamp | EdgeStartTimestamp (type "int or string" depending on job settings; the script accepts ISO 8601, epoch seconds, milliseconds or nanoseconds) |
| ip | ClientIP |
| method | ClientRequestMethod |
| path | ClientRequestPath (or ClientRequestURI; the query string is stripped) |
| status | EdgeResponseStatus |
| user_agent | ClientRequestUserAgent |

Cloudflare also has verified-bot fields (`VerifiedBotCategory`, and `BotScoreSrc` / `BotTags` for Bot Management customers). These are Cloudflare's own judgment and can be compared with this script's result, not substituted for it.

For other CDNs and hosts (Fastly, Akamai, CloudFront, Vercel, Netlify and others), check the provider's current log field documentation and map the equivalent fields. The fields that matter are the client IP as seen by the edge, the request path, the status returned and the user agent.

# Example: replatform of a fictional bike shop (local test run)

Larkspur Ridge Cycles is a fictional business. `local-test-server.py` serves its site on 127.0.0.1:8766 in two modes: `before` (old URL structure) and `after` (new platform, same host). Inputs are the `sample-*` files in this folder; all data is synthetic. Every output below is pasted unedited from a real run.

Planted problems in the "after" site:

| Old URL | Priority | What the new site does |
|---|---|---|
| /guides/bike-sizing | P1 (cited) | Correct 301 to /learn/bike-sizing, same content and schema (should pass) |
| /guides/tubeless-setup | P1 (cited) | 302 then 301 (two hops, one temporary); new page renders its text with JavaScript |
| /services/bike-fitting | P1 (cited) | 301 to the homepage instead of the mapped page |
| /shop/gravel-bikes | P2 | Target page is `noindex` |
| /blog/winter-riding-tips | P2 | Canonical points to /journal/, Article schema dropped, half the text gone |
| /about | P2 | Correct 301 to /about-us (should pass) |
| /old-promo | P3 | 404 (map says /offers) |
| robots.txt | | New file blocks GPTBot and PerplexityBot site-wide and Claude-SearchBot on /learn/ |

Commands were run from this `examples/` folder.

## `python3 ../scripts/migration_check.py columns sample-organic-pages.csv`

```
File: sample-organic-pages.csv
Rows: 6
Columns:
  'Landing page': e.g. 'http://127.0.0.1:8766/guides/bike-sizing' <- looks like URLs
  'Clicks (synthetic)': e.g. '1,240' <- numeric
Problem: line 7: 1 fields, header has 2

Add this file to sources.json with the column names you confirm, for example:
{
  "file": "sample-organic-pages.csv",
  "url_column": "Landing page",
  "metric_column": "Clicks (synthetic)",
  "kind": "ai_citations | organic | other",
  "label": "describe the source"
}
```

## `python3 ../scripts/migration_check.py baseline --sources sample-sources.json --out output-baseline.csv   (server in before mode)`

```
Note: organic clicks export: 1 row(s) without a valid http(s) URL skipped
Note: organic clicks export: line 7: 1 fields, header has 2
Baseline written: output-baseline.csv
URLs: 7 (P1 cited by AI: 3, P2 organic: 3, P3 other: 1)
pri status  words  main  schema                      url
P1  200       415   409  Article|FAQPage             http://127.0.0.1:8766/guides/bike-sizing
P1  200       306   300  Article                     http://127.0.0.1:8766/guides/tubeless-setup
P1  200       132   126  Service                     http://127.0.0.1:8766/services/bike-fitting
P2  200       128   122  -                           http://127.0.0.1:8766/shop/gravel-bikes
P2  200       159   153  Article                     http://127.0.0.1:8766/blog/winter-riding-tips
P2  200        61    55  -                           http://127.0.0.1:8766/about
P3  200        69    63  -                           http://127.0.0.1:8766/old-promo
```

## `python3 ../scripts/migration_check.py redirects --map sample-redirect-map.csv --baseline output-baseline.csv --stage pre   (still before mode)`

```
Redirect map: sample-redirect-map.csv (7 rows)

Redirect check
0 launch blocker(s), 0 fix soon, 7 to check

== CHECK ==
[P1] http://127.0.0.1:8766/guides/bike-sizing
     redirect: Not redirecting yet (pre-launch run)
     evidence: HTTP 200
[P1] http://127.0.0.1:8766/guides/tubeless-setup
     redirect: Not redirecting yet (pre-launch run)
     evidence: HTTP 200
[P1] http://127.0.0.1:8766/services/bike-fitting
     redirect: Not redirecting yet (pre-launch run)
     evidence: HTTP 200
[P2] http://127.0.0.1:8766/about
     redirect: Not redirecting yet (pre-launch run)
     evidence: HTTP 200
[P2] http://127.0.0.1:8766/blog/winter-riding-tips
     redirect: Not redirecting yet (pre-launch run)
     evidence: HTTP 200
[P2] http://127.0.0.1:8766/shop/gravel-bikes
     redirect: Not redirecting yet (pre-launch run)
     evidence: HTTP 200
[P3] http://127.0.0.1:8766/old-promo
     redirect: Not redirecting yet (pre-launch run)
     evidence: HTTP 200
```

## `python3 ../scripts/migration_check.py launch --baseline output-baseline.csv --map sample-redirect-map.csv --old-robots sample-robots-old.txt --new-robots http://127.0.0.1:8766/robots.txt --csv-out output-launch-findings.csv   (server in after mode)`

```
Baseline: output-baseline.csv (7 URLs) | Map: sample-redirect-map.csv (7 rows)

No-JavaScript word counts (main content):
pri  old words new words  old URL -> new URL
P1         409       409  http://127.0.0.1:8766/guides/bike-sizing -> http://127.0.0.1:8766/learn/bike-sizing
P1         300         0  http://127.0.0.1:8766/guides/tubeless-setup -> http://127.0.0.1:8766/learn/tubeless-setup
P1         126        54  http://127.0.0.1:8766/services/bike-fitting -> http://127.0.0.1:8766/
P2          55        55  http://127.0.0.1:8766/about -> http://127.0.0.1:8766/about-us
P2         153        80  http://127.0.0.1:8766/blog/winter-riding-tips -> http://127.0.0.1:8766/journal/winter-riding
P2         122       122  http://127.0.0.1:8766/shop/gravel-bikes -> http://127.0.0.1:8766/bikes/gravel

robots.txt sources:
  old: sample-robots-old.txt: file
  new: http://127.0.0.1:8766/robots.txt: HTTP 200
  paths checked per crawler: 8 (including /)
token             operator   status             role
Googlebot         Google     unchanged          Google Search crawler; also the control for AI Overviews and AI Mode
Bingbot           Microsoft  unchanged          Bing search crawler
OAI-SearchBot     OpenAI     unchanged          ChatGPT search results
Claude-SearchBot  Anthropic  newly blocked (2)  Claude search result quality
PerplexityBot     Perplexity newly blocked (8)  Perplexity search results
ChatGPT-User      OpenAI     unchanged          user-triggered fetches (OpenAI: robots.txt rules may not apply)
Claude-User       Anthropic  unchanged          user-triggered fetches for Claude users
Perplexity-User   Perplexity unchanged          user-triggered fetches (Perplexity: generally ignores robots.txt)
GPTBot            OpenAI     newly blocked (8)  model training
ClaudeBot         Anthropic  unchanged          model training
Google-Extended   Google     unchanged          Gemini training and grounding control (not a separate crawler)

Migration launch check
10 launch blocker(s), 6 fix soon, 3 to check

== LAUNCH BLOCKER ==
[P1] http://127.0.0.1:8766/guides/tubeless-setup
     parity: Main-content words in the no-JavaScript view fell 100% (almost no text without JavaScript: content may be rendered client-side)
     evidence: 300 -> 0 words
[P1] http://127.0.0.1:8766/services/bike-fitting
     parity: Main-content words in the no-JavaScript view fell 57% (escalated: URL is cited by AI)
     evidence: 126 -> 54 words
[P1] http://127.0.0.1:8766/guides/tubeless-setup
     redirect: Temporary redirect (302), use 301 or 308 for a permanent move (escalated: URL is cited by AI)
     evidence: http://127.0.0.1:8766/guides/tubeless-setup -> 302 http://127.0.0.1:8766/learn/tubeless -> 301 http://127.0.0.1:8766/learn/tubeless-setup
[P1] http://127.0.0.1:8766/services/bike-fitting
     redirect: Lands on a different URL than the redirect map says (escalated: URL is cited by AI)
     evidence: map: http://127.0.0.1:8766/services/fitting | actual: http://127.0.0.1:8766/
[P1] http://127.0.0.1:8766/services/bike-fitting
     redirect: Redirects to the homepage
     evidence: http://127.0.0.1:8766/services/bike-fitting -> 301 http://127.0.0.1:8766/
[P1] http://127.0.0.1:8766/services/bike-fitting
     redirect: Target title looks unrelated to the old page (similarity 0.29) (escalated: URL is cited by AI)
     evidence: old: 'Professional Bike Fitting | Larkspur Ridge Cycles' | new: 'Larkspur Ridge Cycles | Bike Shop'
[P1] robots.txt [Claude-SearchBot]
     robots: Claude-SearchBot newly blocked (Claude search result quality)
     evidence: 2 path(s): /learn/bike-sizing (disallow: /learn/ (group: Claude-SearchBot)); /learn/tubeless-setup (disallow: /learn/ (group: Claude-SearchBot))
[P1] robots.txt [PerplexityBot]
     robots: PerplexityBot newly blocked (Perplexity search results)
     evidence: 8 path(s): / (disallow: / (group: PerplexityBot)); /learn/bike-sizing (disallow: / (group: PerplexityBot)); /learn/tubeless-setup (disallow: / (group: PerplexityBot)); /services/fitting (disallow: / (group: PerplexityBot)) and 4 more
[P2] http://127.0.0.1:8766/shop/gravel-bikes
     target: Target page is noindex
     evidence: http://127.0.0.1:8766/bikes/gravel | meta: robots: noindex, follow | X-Robots-Tag: -
[P3] http://127.0.0.1:8766/old-promo
     redirect: Ends in HTTP 404
     evidence: http://127.0.0.1:8766/old-promo

== FIX SOON ==
[P1] http://127.0.0.1:8766/guides/tubeless-setup
     parity: h1 missing in the no-JavaScript view
     evidence: old h1: 'How to set up tubeless tires'
[P1] http://127.0.0.1:8766/services/bike-fitting
     parity: JSON-LD types missing on the new page: Service
     evidence: old: Service | new: BikeStore
[P1] http://127.0.0.1:8766/guides/tubeless-setup
     redirect: Redirect chain of 2 hops (redirect straight to the final URL)
     evidence: http://127.0.0.1:8766/guides/tubeless-setup -> 302 http://127.0.0.1:8766/learn/tubeless -> 301 http://127.0.0.1:8766/learn/tubeless-setup
[P2] http://127.0.0.1:8766/blog/winter-riding-tips
     parity: JSON-LD types missing on the new page: Article
     evidence: old: Article | new: none
[P2] http://127.0.0.1:8766/blog/winter-riding-tips
     parity: Main-content words in the no-JavaScript view fell 48%
     evidence: 153 -> 80 words
[P2] http://127.0.0.1:8766/blog/winter-riding-tips
     target: Target canonical points to a different URL
     evidence: http://127.0.0.1:8766/journal/winter-riding canonical -> http://127.0.0.1:8766/journal/

== CHECK ==
[P1] http://127.0.0.1:8766/services/bike-fitting
     parity: Title changed
     evidence: old: 'Professional Bike Fitting | Larkspur Ridge Cycles' | new: 'Larkspur Ridge Cycles | Bike Shop'
[P1] http://127.0.0.1:8766/services/bike-fitting
     parity: h1 changed
     evidence: old: 'Bike fitting' | new: 'Larkspur Ridge Cycles'
[P1] robots.txt [GPTBot]
     robots: Training crawler newly blocked: confirm this is a deliberate decision
     evidence: 8 path(s): / (disallow: / (group: GPTBot)); /learn/bike-sizing (disallow: / (group: GPTBot)); /learn/tubeless-setup (disallow: / (group: GPTBot)); /services/fitting (disallow: / (group: GPTBot)) and 4 more
CSV written: output-launch-findings.csv
```

The baseline file it wrote is `output-baseline.csv`; the findings CSV is `output-launch-findings.csv`. The `redirects`, `parity` and `robots` subcommands print the same findings separately (the `launch` run above combines them and removes duplicates).

## Edge cases

```
$ python3 migration_check.py columns empty.csv
empty.csv: file is empty
(exit code 1)

$ python3 migration_check.py baseline --input empty.csv --out /dev/null
Note: empty.csv: file is empty
No URLs found in the inputs.
(exit code 1)

$ python3 migration_check.py baseline --input nope.csv
File not found: nope.csv
(exit code 2)

$ python3 migration_check.py redirects --map badmap.csv
Map problem: line 2: old URL missing or not http(s): 'not-a-url'
Redirect map: badmap.csv (0 rows)

Redirect check
0 launch blocker(s), 0 fix soon, 0 to check
No issues found by the checks this script runs.
(exit code 0)

$ python3 migration_check.py redirects --map sample-ai-citations.csv
sample-ai-citations.csv: needs columns 'old_url' and 'new_url'; found Page, AI citations (synthetic). Use --old-col / --new-col.
(exit code 1)

$ python3 migration_check.py robots --new http://127.0.0.1:1/robots.txt
robots.txt sources:
  old: no old robots.txt given (assumed allow all)
  new: http://127.0.0.1:1/robots.txt: URLError: <urlopen error [Errno 111] Connection refused> (RFC 9309: treat an unreachable robots.txt as complete disallow)
  paths checked per crawler: 1 (including /)
token             operator   status             role
Googlebot         Google     newly blocked (1)  Google Search crawler; also the control for AI Overviews and AI Mode
Bingbot           Microsoft  newly blocked (1)  Bing search crawler
OAI-SearchBot     OpenAI     newly blocked (1)  ChatGPT search results
Claude-SearchBot  Anthropic  newly blocked (1)  Claude search result quality
PerplexityBot     Perplexity newly blocked (1)  Perplexity search results
ChatGPT-User      OpenAI     newly blocked (1)  user-triggered fetches (OpenAI: robots.txt rules may not apply)
Claude-User       Anthropic  newly blocked (1)  user-triggered fetches for Claude users
(exit code 1)

```

The last case is cut to its first 12 lines: an unreachable robots.txt is treated as complete disallow (RFC 9309), so every crawler shows as newly blocked.

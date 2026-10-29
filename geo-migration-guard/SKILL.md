---
name: geo-migration-guard
description: Protect AI search and organic visibility through a site migration, replatform or URL restructure. Records a no-JavaScript baseline of the URLs that get AI citations or search traffic, checks the redirect map, compares old and new pages after launch, and checks robots.txt for newly blocked search and AI crawlers, then gives a prioritized list of launch blockers and fix-soon items. Use when someone is planning, launching or recovering from a website migration, redesign, CMS change or domain move.
---

# GEO migration guard

A migration is where sites quietly lose the pages AI assistants and search engines cite: a redirect goes to the homepage, a template drops the structured data, the new front end renders text with JavaScript, a staging `noindex` or robots.txt block ships to production. This skill checks for those failures in four stages and hands back one list, ordered by what must be fixed before launch.

Everything is measured, not scored. Each finding names the URL, the check, and the evidence (status codes, the redirect chain, the old and new values).

## Step 1: Gather the inputs

Ask for anything missing. Do not guess which pages matter.

- **Pages that get AI citations.** Any export that lists cited URLs: an AI visibility tracker, the AI performance report in Bing Webmaster Tools (check current docs for what it exports), or a manual list from checking answers by hand.
- **Pages that get organic traffic.** A Google Search Console or analytics export, or an SEO tool's top pages report.
- **Other URLs that must survive:** pages linked from partners, campaigns, printed material.
- **The redirect map:** old URL and new URL per row.
- **The current robots.txt**, saved before launch (the old one is gone once the new site is live).
- **The stage:** before launch (baseline, map review) or after launch (everything).

## Step 2: Map the columns

Export formats change and differ between tools, so the script does not assume any vendor's column names. Inspect each file and confirm the columns with the user:

```
python3 scripts/migration_check.py columns your-export.csv
```

It lists the columns, flags which look like URLs and which are numeric, and prints a snippet for `sources.json`. Each source gets a `kind`:

| kind | Use for | Priority it gives a URL |
|---|---|---|
| `ai_citations` | any count of AI citations or answers that cite the URL | **P1** if the count is above zero (a list with no count column counts each row as one) |
| `organic` | clicks, sessions, traffic | **P2** if above zero |
| `other` | manual lists, partner links | **P3** |

See `examples/sample-sources.json`. The column names in the sample CSVs are invented on purpose.

## Step 3: Baseline (before launch)

```
python3 scripts/migration_check.py baseline --sources sources.json --out baseline.csv
```

For every URL, cited ones first, the script makes a plain HTTP request (no JavaScript) and records: status, final URL and redirect hops, title, h1, canonical, robots meta, `X-Robots-Tag` header, JSON-LD types, word count of the raw HTML text, and main-content word count (text inside `<main>` or `<article>` if the page has one, otherwise visible text outside nav, header, footer and aside). Use `--limit` and `--delay` on large sites.

Fix baseline issues first: a cited URL that already returns an error or `noindex` will confuse every later comparison.

## Step 4: Redirect map check

```
python3 scripts/migration_check.py redirects --map redirect-map.csv --baseline baseline.csv [--stage pre]
```

Every old URL is requested and every hop recorded. Run it on staging or right after launch. With `--stage pre` an old URL that does not redirect yet is a note, not a blocker.

## Step 5: Post-launch parity

```
python3 scripts/migration_check.py parity --baseline baseline.csv --map redirect-map.csv
```

Each baseline URL is followed to where it lands now and compared: title, h1, JSON-LD types, main-content word count in the no-JavaScript view, robots meta and header.

## Step 6: robots.txt

```
python3 scripts/migration_check.py robots --old saved-old-robots.txt --new https://example.com/robots.txt --baseline baseline.csv --map redirect-map.csv
```

Each crawler is checked against the old robots.txt on the old paths and the new robots.txt on the new paths, using RFC 9309 rules (all groups naming the crawler combined, fallback to `*`, longest match wins, allow wins a tie, `*` and `$` wildcards). A robots.txt that is unreachable or returns 5xx is treated as complete disallow and a 4xx as allow all, as RFC 9309 says ([RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html)).

| Token | Operator | What it is for (from the operator's docs) | If newly blocked |
|---|---|---|---|
| Googlebot | Google | Search crawler; Google says robots.txt directives for Googlebot are the control for AI Overviews and AI Mode | Launch blocker |
| Bingbot | Microsoft | Bing's crawler | Launch blocker |
| OAI-SearchBot | OpenAI | Opted-out sites are not shown in ChatGPT search answers | Launch blocker |
| Claude-SearchBot | Anthropic | Search result quality; blocking may reduce visibility in search results | Launch blocker |
| PerplexityBot | Perplexity | Surfaces and links sites in Perplexity search results | Launch blocker |
| ChatGPT-User | OpenAI | User-triggered fetches; "robots.txt rules may not apply" | Fix soon |
| Claude-User | Anthropic | Fetches for Claude users' queries | Fix soon |
| Perplexity-User | Perplexity | User-triggered; "generally ignores robots.txt rules" | Fix soon |
| GPTBot | OpenAI | Model training | Check: confirm it is deliberate |
| ClaudeBot | Anthropic | Model training | Check: confirm it is deliberate |
| Google-Extended | Google | Control token (no separate crawler) for Gemini training and grounding; does not affect Search inclusion or ranking | Check: confirm it is deliberate |

Sources for every row are in [references/sources.md](references/sources.md). Bot names change: re-check those pages before relying on this table.

## Step 7: One prioritized list

```
python3 scripts/migration_check.py launch --baseline baseline.csv --map redirect-map.csv \
  --old-robots saved-old-robots.txt --new-robots https://example.com/robots.txt --csv-out findings.csv
```

Runs Steps 4 to 6 together and prints the findings in three tiers, P1 first within each tier. The rules:

| Finding | Tier |
|---|---|
| Old URL ends in 4xx/5xx or fails; old URL does not redirect after launch; chain of 5+ hops; redirect to the homepage; target `noindex`; target adds `nosnippet`; search or AI search crawler newly blocked; new robots.txt unreachable or 5xx; almost no text without JavaScript (under 50 words after a drop of more than 30%) | **Launch blocker** |
| Chain of 2 to 4 hops; temporary redirect (302, 303, 307); lands somewhere other than the map says; target title unrelated to the old page; target canonical points elsewhere; more than one canonical tag; main-content words down more than 30%; JSON-LD types lost or JSON-LD that does not parse; h1 missing; `nofollow` added; baseline URL missing from the map; user-triggered fetcher newly blocked | **Fix soon**. Temporary redirect, wrong target, unrelated title, canonical elsewhere, word drop and a missing map row become **launch blockers for P1 (cited) URLs** |
| Title or h1 changed; meta refresh; training crawler newly blocked; crawler newly allowed | **Check** |

The 30% word drop, the title similarity cut-off (0.30, after removing title segments both pages share, such as the brand), and the P1 escalation are tool defaults chosen for this skill, not platform rules **[U]**.

## Step 8: Report and recommend

Give the user the launch blockers first, then fix soon, then check items, each with its evidence. Recommendations and their evidence (Evidence grades: see ../tactics/EVIDENCE.md):

- Use permanent redirects (301 or 308): Google uses them as a signal that the target should be canonical, and temporary ones not. **[P]** ([Google, redirects](https://developers.google.com/search/docs/crawling-indexing/301-redirects))
- Redirect each old URL to its most relevant new page, not many URLs to the homepage, which "might be treated as a soft 404". Redirect straight to the final URL; if not possible, Google says "ideally no more than 3 and fewer than 5" hops. Keep redirects "generally at least 1 year". **[P]** ([Google, site moves](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes)). This skill flags any chain over 1 hop, which is stricter than Google's wording.
- Remove any `noindex` or robots.txt blocks that were only for the migration, and update canonicals to the new URLs. **[P]** (same source)
- Keep pages indexable and eligible for a snippet: Google requires that to appear in AI Overviews and AI Mode. **[P]** ([Google, AI features](https://developers.google.com/search/docs/appearance/ai-features))
- Keep important text in the server HTML, not only rendered by JavaScript. **[S]**, per the "server-render important content" row of ../tactics/EVIDENCE.md.
- Allow OAI-SearchBot and the other search crawlers you want to appear in. **[P]** (table above)
- Checking cited URLs first: a prioritization choice, not a documented rule **[U]**.

Do not promise that following the list keeps citations. It removes known technical causes of loss; it cannot show what AI assistants will do.

## What this skill does not do

- It does not run JavaScript. Word counts and fields are the no-JavaScript view by design; a page can look fine in a browser and still fail here.
- It requests pages with its own user agent, not as Googlebot or an AI crawler, and from your machine's IP. Servers that treat bots differently, or block by IP, can give crawlers a different answer.
- It does not check hreflang, XML sitemaps, internal links, images or page speed, and does not crawl the new site for orphaned pages.
- It does not read Search Console or any AI tracker directly; it works from the exports you give it.
- It does not tell you whether citations dropped. Re-run your AI visibility tracking after launch and compare like with like.

## Credit

Method from the AI Visibility Census, aivisibilitycensus.com, licensed under CC BY 4.0. This credit is for the person installing the skill. Do not add it to the reports or other output the skill produces.

<!-- Real output of scripts/geo_check.py against a local test page for a fictional bike shop. The local address was replaced with a .example domain. -->

# GEO check: https://larkspurridgecycles.example/repairs/

HTTP 200. Title: Bike repair prices.

**1 blocking, 1 to fix, 1 to check, 3 recorded.** No score: these are separate findings, not parts of a total.

## BLOCKS: stops an engine from using the page

- **robots.txt.** OAI-SearchBot is blocked from /repairs/ by "disallow: / (group: OAI-SearchBot)". Affects: ChatGPT search answers.
  - Do: Remove or narrow the rule if you want OpenAI to use this page.
  - Evidence [P]: OpenAI: sites opted out of OAI-SearchBot will not be shown in ChatGPT search answers.

## FIX: likely to cost you, worth fixing

- **Structured data.** LocalBusiness.telephone: Phone number not found on the page. Schema says "+353 56 555 0100". Page shows "353565550199".
  - Do: Make the markup say what the page says.
  - Evidence [P]: Google lists structured data matching the visible text among practices for AI features.

## CHECK: cannot be decided from outside, look at it

- **Firewall or CDN.** A request with "GPTBot" in the user agent gets HTTP 403; the same request with a browser-like user agent gets HTTP 200.
  - Do: Look at your CDN or firewall bot rules. Confirm with server logs (ai-crawler-log-check) before changing anything.
  - Evidence [U]: A user-agent test from one address; real crawlers come from other addresses and may be treated differently.

## INFO: recorded, no action implied

- **Text in raw HTML.** 211 words of visible text arrive without JavaScript (211 in the main content).
  - Evidence [S]: Vercel and MERJ (December 2024): most AI crawlers did not render JavaScript; Googlebot and Applebot did.
- **robots.txt.** GPTBot is blocked from /repairs/ by "disallow: / (group: GPTBot)". Affects: model training (a choice, not a fault).
  - Evidence [P]: Operators document these tokens as training controls, separate from search.
- **llms.txt.** Not present. Neither is a finding: there is no evidence it changes what AI engines show.
  - Evidence [U]: llms.txt is a proposal; no evidence found that it changes what AI engines show.

## robots.txt by crawler

| Crawler | Operator | This page | Rule |
|---|---|---|---|
| Googlebot | Google | allowed | allow: / (group: *) |
| Bingbot | Microsoft | allowed | allow: / (group: *) |
| OAI-SearchBot | OpenAI | blocked | disallow: / (group: OAI-SearchBot) |
| Claude-SearchBot | Anthropic | allowed | allow: / (group: *) |
| PerplexityBot | Perplexity | allowed | allow: / (group: *) |
| ChatGPT-User | OpenAI | allowed | allow: / (group: *) |
| Claude-User | Anthropic | allowed | allow: / (group: *) |
| Perplexity-User | Perplexity | allowed | allow: / (group: *) |
| GPTBot | OpenAI | blocked | disallow: / (group: GPTBot) |
| ClaudeBot | Anthropic | allowed | allow: / (group: *) |
| Google-Extended | Google | allowed | allow: / (group: *) |

## Not checked

- Whether AI engines name or cite you. That needs logged answers: question-set-builder, answer-collector, answer-log-analyzer.
- Whether crawlers actually visit. That needs server logs: ai-crawler-log-check.
- What a browser shows after JavaScript runs. This check reads the HTML the server sends.
- Rankings, backlinks, content quality. No score is given for any of them.

Evidence grades are explained in tactics/EVIDENCE.md: [P] platform documentation, [S] published study, [U] untested. A grade says how well the claim is supported, not that fixing the item will get a page named.

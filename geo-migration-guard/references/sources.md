# Sources checked

All pages fetched and read on 29 October 2026. "Last updated" is the date the page itself showed, where it showed one.

## Crawlers and robots.txt

| Claim used in the skill | Source | Page last updated |
|---|---|---|
| OpenAI tokens OAI-SearchBot (sites opted out are not shown in ChatGPT search answers), GPTBot (training), ChatGPT-User (user-initiated; "robots.txt rules may not apply"), OAI-AdsBot (ad safety checks, not used by this skill) | [OpenAI, Overview of OpenAI crawlers](https://developers.openai.com/api/docs/bots) (platform.openai.com/docs/bots redirects here) | not shown |
| Anthropic tokens ClaudeBot (training), Claude-User (user queries), Claude-SearchBot (search result quality); all honor robots.txt; IP blocking may not work reliably | [Anthropic, Does Anthropic crawl data from the web](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler) | not shown |
| Perplexity tokens PerplexityBot (search results, not foundation-model training) and Perplexity-User (user actions; "generally ignores robots.txt rules") | [Perplexity, Perplexity crawlers](https://docs.perplexity.ai/guides/bots) | not shown |
| Google-Extended is a robots.txt product token with no separate user agent string; controls Gemini training and grounding; "does not impact a site's inclusion in Google Search" and is not a ranking signal | [Google, Google's common crawlers](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers) | 2026-10-15 |
| "robots.txt directives for Googlebot is the control for site owners to manage access" for AI features; pages must be indexed and eligible to be shown with a snippet; no additional technical requirements | [Google, AI features and your website](https://developers.google.com/search/docs/appearance/ai-features) | 2025-12-10 |
| bingbot user agent token; bingbot-specific robots.txt rules take precedence | [Bing Webmaster Blog, Bing crawler bingbot on the horizon (2010)](https://blogs.bing.com/webmaster/June-2010/Bing-crawler-bingbot-on-the-horizon) | 2010 |
| Bing's NOCACHE and NOARCHIVE meta tags control use of content in Bing Chat answers (mentioned only as background; the script does not check them) | [Bing Webmaster Blog, September 2023](https://blogs.Bing.com/webmaster/september-2023/Announcing-new-options-for-webmasters-to-control-usage-of-their-content-in-Bing-Chat) | 2023 |
| Robots.txt rules: combine matching groups, fallback to `*`, case-insensitive user-agent match, longest match, allow wins ties, `*` and `$`; 4xx means crawlers may access everything; unreachable or 5xx means complete disallow; follow at least five redirects | [RFC 9309, Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309.html) | RFC, September 2022 |

Bing's current crawler help page (bing.com/webmasters/help/which-crawlers-does-bing-use-8c184ec0) renders with JavaScript and could not be read, so the bingbot row relies on the 2010 Bing blog post. Check current Bing documentation for any newer Bing or Copilot specific tokens. This skill makes no claim about how Copilot uses Bing's index.

## Redirects and site moves

| Claim used in the skill | Source | Page last updated |
|---|---|---|
| 301 and 308 are permanent and used as a canonical signal; 302, 303, 307 are temporary and not used as that signal; instant meta refresh treated as permanent | [Google, Redirects and Google Search](https://developers.google.com/search/docs/crawling-indexing/301-redirects) | 2026-04-14 |
| Map each old URL; don't redirect many old URLs to one irrelevant destination such as the home page, which "might be treated as a soft 404"; redirect to the final destination, chains "ideally no more than 3 and fewer than 5"; keep redirects "generally at least 1 year"; remove migration-only noindex and robots.txt blocks; update canonicals to new URLs | [Google, Site moves with URL changes](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes) | 2026-08-20 |

## Not verified, so not used

- Export column names for Bing Webmaster Tools, Google Search Console, Ahrefs or any tracker. The script asks for a column mapping instead.
- Any figure for how much visibility a migration typically loses.

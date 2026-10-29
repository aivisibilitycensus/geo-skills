---
name: schema-parity-checker
description: Check that a page's structured data (JSON-LD) says only what the visible page says, field by field, with the exact strings that differ. Use when someone asks whether their schema matches their content, is auditing FAQPage, Product, Organization, LocalBusiness, Article or Review markup, or wants to find stale prices, ratings, phone numbers, dates or FAQ answers in their structured data.
---

# Schema parity checker

Compares the structured data on a page with the text a visitor can actually see, and lists every value that is missing, changed or hidden. The output is a list of mismatches with a severity and the exact schema string next to the page string. It does not score the page.

The rule behind it comes from Google: "Don't mark up content that is not visible to readers of the page" and "Your structured data must be a true representation of the page content" ([Google, structured data policies](https://developers.google.com/search/docs/appearance/structured-data/sd-policies)). Google also lists "making sure your structured data matches the visible text on the page" among its practices for AI features ([Google, AI features](https://developers.google.com/search/docs/appearance/ai-features)).

## The pitfall this skill exists for

Two things make schema checks go wrong, so deal with them before anything else:

1. **Tools that convert HTML to Markdown or plain text delete `<script>` tags**, and JSON-LD lives in a `<script>` tag. A check run on that output will say "no schema" when there is some. Always use the raw HTML: fetch it with the script, or save it with something like `curl -o page.html URL`.
2. **Schema or content added by JavaScript is not in the raw HTML.** Google says it "can understand and process structured data that's available in the DOM when it renders the page" ([Google, JavaScript structured data](https://developers.google.com/search/docs/appearance/structured-data/generate-structured-data-with-javascript)), but crawlers that do not render JavaScript will not see it. Check both views when in doubt (Step 3).

## Step 1: Get the page

Ask for the URL, or a saved raw HTML file if the page is behind a login or not live yet. If the user pastes text or Markdown instead of HTML, say that the structured data will not be in it and ask for the raw HTML.

## Step 2: Run the script

```
python3 scripts/schema_parity.py https://example.com/page
python3 scripts/schema_parity.py saved-page.html --base-url https://example.com/page
python3 scripts/schema_parity.py URL --check-links     # also request each sameAs and logo URL
python3 scripts/schema_parity.py URL --json            # for further processing
```

Standard library only (tested on Python 3.13). The script fetches raw HTML with `urllib`, parses it with `html.parser`, reads every JSON-LD block (including `@graph` and nested items), and builds three text layers: visible text (script, style and other non-text elements removed), navigation/header/footer text, and text inside hidden elements (`hidden`, `aria-hidden="true"`, `display:none`, `visibility:hidden`). It also reports whether the page has microdata or RDFa, but only JSON-LD is compared in this version.

If the script cannot run in the user's environment, follow the same comparisons by hand from the raw HTML.

## Step 3: Check the rendered view if needed

```
python3 scripts/schema_parity.py URL --render
```

`--render` uses Playwright if it is installed (`pip install playwright` then `playwright install chromium`). If it is not installed, the script says so and carries on with raw HTML. When rendering works, the report shows JSON-LD types in the raw and rendered views and warns about any type that only exists after JavaScript runs. Without Playwright, Google's Rich Results Test is an alternative; Google recommends its URL input over code input ([Google, JavaScript structured data](https://developers.google.com/search/docs/appearance/structured-data/generate-structured-data-with-javascript)).

## What is compared

| Schema type | Fields checked against the page |
|---|---|
| FAQPage | Each Question `name` and its `acceptedAnswer` text. Reports missing, changed (with similarity) and hidden answers, plus question-style headings on the page that are not in the schema |
| Product / Offer | `name`, `offers.price` (and `lowPrice`/`highPrice`), `priceCurrency` marker next to the price, `availability` wording (for example InStock vs "Sold out"), `aggregateRating` `ratingValue`, `reviewCount`, `ratingCount` |
| Organization, LocalBusiness and subtypes | `name`, `telephone` (digit comparison, so formatting does not matter), `address` parts, `aggregateRating`; with `--check-links`, every `sameAs` URL and the `logo` URL |
| Article, BlogPosting, NewsArticle | `headline` vs h1 and title, `datePublished` and `dateModified` vs dates shown on the page (`<time>` tags and written dates), `author` names |
| Review, AggregateRating | `reviewRating.ratingValue`, `author`, `reviewBody`; aggregate counts must appear as numbers on the page |

Text matching: both sides are normalized (case, curly quotes, punctuation, whitespace, HTML tags in schema text). A match after normalizing counts as found. Otherwise the script finds the closest stretch of page text with Python's `difflib` and reports the similarity: 0.90 or higher counts as the same text, 0.60 to 0.90 is "wording differs", below 0.60 is "not found". These thresholds are tool defaults, not a standard. Changed wording is raised to high severity when the schema contains numbers the page does not show (a stale price, time or count).

## Step 4: Read the results

| Severity | Meaning |
|---|---|
| high | The schema states something the visible page does not: a value missing from the page, a number that differs, text that only sits in a hidden element, wording that contradicts the page (for example InStock when the page says sold out), or JSON-LD that does not parse |
| medium | Present but different: reworded text, a phone number only in a `tel:` link, a date not shown, a sameAs or logo URL that errors |
| low | Worth a look but often fine: a question-style heading not in the FAQ schema, no availability wording to confirm, no currency marker next to the price |

The "Confirmed" list shows what matched and where, so the user can see the check actually ran on each field.

## Step 5: Report and recommend

Report the mismatches first, grouped by schema type, each with the schema string and the page string side by side. Then the fixes. The fix is almost always one of two things: change the schema to match the page, or show the information on the page. Which one is the user's call: the page is the source of truth for visitors.

Recommendations and their evidence (Evidence grades: see ../tactics/EVIDENCE.md):

- Make structured data match the visible text, and do not mark up hidden content. **[P]** ([Google, structured data policies](https://developers.google.com/search/docs/appearance/structured-data/sd-policies); [Google, AI features](https://developers.google.com/search/docs/appearance/ai-features))
- If you use AggregateRating, show that rating on the page; marked-up review content should be "readily available to users from the marked-up page". Self-serving reviews on Organization and LocalBusiness are not eligible for star review features. **[P]** ([Google, review snippet](https://developers.google.com/search/docs/appearance/structured-data/review-snippet))
- FAQPage markup: Google stopped showing FAQ rich results from May 7, 2026 and removed the documentation in June 2026 ([Google, Search Central changelog](https://developers.google.com/search/updates)). There is no Google display benefit left. Whether FAQ markup helps AI answers: **[U]**. If the user keeps it, it should still match the page.
- JSON-LD that only appears after JavaScript runs: Google can process it when rendering **[P]** (source above). Crawlers that do not render JavaScript will miss it; the repo grades "server-render important content" as **[S]** in ../tactics/EVIDENCE.md. Putting the JSON-LD in the server HTML removes the question.
- JSON-LD, Microdata and RDFa are all supported by Google; JSON-LD is recommended. **[P]** ([Google, intro to structured data](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data))

Do not tell the user a mismatch causes a penalty or a ranking or citation loss. The documentation says what Google asks for, not what happens to a given page.

## What this skill does not do

- It does not validate schema against schema.org or Google's required properties. Use Google's Rich Results Test or the Schema Markup Validator for that.
- It does not compare microdata or RDFa values, only reports that they exist.
- Dates are matched in ISO, "March 4, 2026" and "4 March 2026" forms. Other formats and other languages will show as "not shown".
- Prices and ratings are matched as numbers anywhere on the page, not tied to the product block. A matching number elsewhere on the page can hide a mismatch, so review the evidence string for high-value fields.
- Hidden text is detected from HTML attributes and inline styles only. Content hidden by a CSS class looks visible to the script. Collapsed `<details>` content counts as visible, because a visitor can open it.
- It checks one page at a time and does not crawl.
- It cannot tell whether a search engine or AI assistant uses the markup.

## Sources

Every platform claim above was checked on 29 October 2026 against the pages linked in [references/sources.md](references/sources.md).

## Credit

Method from the AI Visibility Census, aivisibilitycensus.com, licensed under CC BY 4.0. This credit is for the person installing the skill. Do not add it to the reports or other output the skill produces.

# Tactic evidence grades

Most AI search advice is repeated, not tested. Every skill in this repo that recommends a tactic tags it with one of these grades, so you can see how much weight it carries.

| Grade | Meaning |
|---|---|
| **[T]** | Tested by the AI Visibility Census, with the result published |
| **[S]** | Published study with a stated method (peer-reviewed or preprint, or a dataset whose method is described) |
| **[P]** | Platform documentation: the search engine or AI company says so in its own docs |
| **[V]** | Vendor or practitioner claim, not independently checked |
| **[U]** | Untested, or no evidence found either way |

A higher grade is not a promise. [P] tells you what a platform says it does, not what happens on your site. [S] results come from the study's setup, which may not match yours.

Last checked: 29 October 2026. Census test status comes from the [experiments page](https://aivisibilitycensus.com/experiments/). Two experiments are running: CT-001 (how fast a new page is crawled, indexed and cited) and CS-001 (Content Signals). Neither has reported a result yet, so nothing below is graded [T].

## The tactics

| Tactic | The usual claim | Grade | What the evidence says | Census test |
|---|---|---|---|---|
| Be indexed and eligible for a snippet in Google | Required to appear in AI Overviews and AI Mode | **[P]** | Google: pages need to be indexed and eligible to be shown with a snippet; there are "no additional requirements" ([Google, AI features](https://developers.google.com/search/docs/appearance/ai-features)) | Not tested |
| Special AI files or markup for Google | You need llms.txt or special schema for AI Overviews | **[P] against** | Google: "You don't need to create new machine readable files, AI text files, or markup to appear in these features" ([Google, AI features](https://developers.google.com/search/docs/appearance/ai-features)) | Not tested |
| llms.txt | AI crawlers read it and use it to find your best pages | **[U]** | A proposal by Jeremy Howard, first published September 2024, "open for community input" ([llmstxt.org](https://llmstxt.org/)). Google says AI text files are not needed for its AI features (row above). Whether AI crawlers fetch it is what the Census is logging | Logged within CT-001 |
| Markdown versions of pages | AI tools prefer Markdown to HTML | **[U]** | No platform documentation or study found | Logged within CT-001 |
| Allow OAI-SearchBot in robots.txt | Needed to appear in ChatGPT search answers | **[P]** | OpenAI: sites opted out of OAI-SearchBot "will not be shown in ChatGPT search answers"; GPTBot is the separate training crawler ([OpenAI, bots](https://developers.openai.com/api/docs/bots)) | Not tested |
| IndexNow | Gets pages into Bing (and so Copilot) faster | **[P] partial** | IndexNow: participating engines include Bing; "Submitting a URL does not guarantee immediate indexing" ([IndexNow FAQ](https://www.indexnow.org/faq)). The speed claim is not documented | Used within CT-001 |
| Server-render important content | AI crawlers don't run JavaScript, so they miss it | **[S]** | Vercel and MERJ (December 2024): "none of the major AI crawlers currently render JavaScript"; exceptions were Gemini (via Googlebot) and Applebot ([Vercel](https://vercel.com/blog/the-rise-of-the-ai-crawler)). Single-network data, 2024 | Not tested |
| Structured data matches visible text | Mismatched markup is a problem | **[P]** | Google lists making sure structured data matches the visible text among practices for AI features ([Google, AI features](https://developers.google.com/search/docs/appearance/ai-features)) | Not tested |
| FAQ structured data | Helps AI tools lift your answers | **[U]** | Google stopped showing FAQ rich results from 7 May 2026 ([Google Search Central updates](https://developers.google.com/search/updates)), so there is no Google display benefit. No evidence found that it helps AI answers | In place within CT-001; not isolated |
| Content Signals in robots.txt | AI crawlers change behavior when ai-train or ai-input is set to no | **[U]** | A robots.txt extension introduced by Cloudflare in September 2025 ([Cloudflare](https://blog.cloudflare.com/content-signals-policy/)). No AI company found committing to honor it | CS-001, running |
| Add statistics, quotations and citations to content | Raises visibility in AI answers | **[S]** | Aggarwal et al.: "GEO can boost visibility by up to 40% in generative engine responses", in a benchmark setting (arXiv 2311.09735, v3 June 2024) ([arXiv](https://arxiv.org/abs/2311.09735)). Lab results, not a live-engine guarantee | Not tested |
| Rank in Google's top 10 | Required to be cited in AI Overviews | **[U]** | Claims vary between vendor studies; not checked here | Not tested |
| Backlinks | A page with no backlinks won't be cited | **[U]** | Not checked here | Not tested |
| Question-style headings | Get quoted word for word | **[U]** | Not checked here | Not tested |
| LinkedIn sharing | Speeds up the first Bing and Copilot crawl | **[U]** | Not checked here | Not tested |
| Hidden instructions aimed at AI assistants | Gets your brand remembered or recommended | **Do not use** | Microsoft describes companies hiding instructions that tell an assistant to remember and favor their brand, and calls it "AI Recommendation Poisoning" ([Microsoft Security, 10 February 2026](https://www.microsoft.com/en-us/security/blog/2026/02/10/ai-recommendation-poisoning/)). This repo never recommends it | Never |

## Corrections

If a grade is wrong or a source has changed, open an issue with the link. Grades move up only when the evidence does.

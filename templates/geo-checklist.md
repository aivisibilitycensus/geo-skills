# GEO checklist, graded by evidence

A generative engine optimization (GEO) checklist where every item says how strong the evidence behind it is. Measure first, then do the documented and studied items, skip what platforms say is not needed, and treat untested items as experiments.

Excel version with a status column and a progress tab: [aivisibilitycensus.com/templates/geo-checklist/](https://aivisibilitycensus.com/templates/geo-checklist/). Grades come from [tactics/EVIDENCE.md](../tactics/EVIDENCE.md) (last checked 29 October 2026) and change only when the evidence does.

| Grade | Meaning |
|---|---|
| **[T]** | Tested by the AI Visibility Census, with the result published |
| **[S]** | Published study with a stated method |
| **[P]** | Platform documentation: the search engine or AI company says so in its own docs |
| **[V]** | Vendor or practitioner claim, not independently checked |
| **[U]** | Untested, or no evidence found either way |
| **Method** | How to measure, not a ranking tactic |
| **Do not use** | Harmful or deceptive |

A higher grade is not a promise. [P] tells you what a platform says it does, not what happens on your site. No item is graded [T] yet: the Census experiments in the last column have not reported results.

## 1. Measure first

| Check | How to check | Grade | What the evidence says | Census test |
|---|---|---|---|---|
| Write a fixed set of buyer questions before you change anything | List the questions buyers ask, spread across vendor selection, comparison, specific need and educational intents. Keep the wording fixed so months compare. | **Method** | This is how you measure, not a ranking tactic. Without a fixed question set, a change in results cannot be told apart from a change in the questions. ([Question set builder (free skill)](https://github.com/aivisibilitycensus/geo-skills/tree/main/question-set-builder)) | Used for Census Edition 1 and the Census100 |
| Ask each question at least 3 times per engine per check date | Log every answer with the date, engine, run number, answer text and cited links. | **Method** | AI answers change from run to run. With 1 or 2 runs the only possible rates are 0%, 50% or 100%. ([Answer log analyzer methods](https://github.com/aivisibilitycensus/geo-skills/blob/main/answer-log-analyzer/references/methods.md)) | Edition 1 plan: 3 runs per date on ChatGPT, Gemini and AI Mode |
| Change one thing at a time, with a control page and a written prediction | Note the date of each change and what you expect before results come in. | **Method** | Engine updates land between check dates too, so a change you cannot isolate tells you little. ([GEO experiment kit (free skill)](https://github.com/aivisibilitycensus/geo-skills/tree/main/geo-experiment-kit)) | Every test on our experiments page |

## 2. Do next: documented or studied

| Check | How to check | Grade | What the evidence says | Census test |
|---|---|---|---|---|
| Pages you want in Google's AI features are indexed and eligible for a snippet | URL Inspection in Search Console shows the page is on Google. No nosnippet on the page. | **[P]** | Google: pages need to be indexed and eligible to be shown with a snippet; there are "no additional requirements". ([Google, AI features and your website](https://developers.google.com/search/docs/appearance/ai-features)) | Not tested |
| OAI-SearchBot is allowed in robots.txt | Open yoursite.com/robots.txt and check nothing disallows OAI-SearchBot (or every bot with *). | **[P]** | OpenAI: sites opted out of OAI-SearchBot "will not be shown in ChatGPT search answers". GPTBot is the separate training crawler. ([OpenAI, bots](https://developers.openai.com/api/docs/bots)) | Not tested |
| Important content is in the HTML the server sends, not only added by JavaScript | View the page source (not the inspector) and search for a key sentence. | **[S]** | Vercel and MERJ (December 2024): "none of the major AI crawlers currently render JavaScript"; exceptions were Gemini (via Googlebot) and Applebot. Data from Vercel's network, checked on two other sites, 2024. ([Vercel, The rise of the AI crawler](https://vercel.com/blog/the-rise-of-the-ai-crawler)) | Not tested |
| IndexNow sends new and changed URLs to Bing | Check your CMS or plugin sends IndexNow pings and gets a 200 or 202 back. | **[P] partial** | IndexNow lists Bing among participating engines and says "Submitting a URL does not guarantee immediate indexing". The speed claim is not documented. ([IndexNow FAQ](https://www.indexnow.org/faq)) | Used within CT-001 |
| Structured data says only what the visible page says | Compare schema FAQ text, prices, ratings, phone numbers and dates against the visible page. | **[P]** | Google lists making sure structured data matches the visible text among practices for AI features. ([Google, AI features and your website](https://developers.google.com/search/docs/appearance/ai-features)) | Not tested |
| Add statistics, quotations and citations to key pages | Each key page carries at least one number with its source, and names its sources. | **[S]** | Aggarwal et al.: "GEO can boost visibility by up to 40% in generative engine responses", in a benchmark setting. Lab results, not a live-engine guarantee. ([arXiv 2311.09735](https://arxiv.org/abs/2311.09735)) | Not tested |

## 3. Skip

| Check | How to check | Grade | What the evidence says | Census test |
|---|---|---|---|---|
| Do not add special AI files or markup expecting it to get you into Google's AI features | Nothing to add. If a vendor sells you an AI file for Google, ask for the source. | **[P] against** | Google: "You don't need to create new machine readable files, AI text files, or markup to appear in these features". ([Google, AI features and your website](https://developers.google.com/search/docs/appearance/ai-features)) | Not tested |

## 4. Optional: untested, so test before you rely on it

| Check | How to check | Grade | What the evidence says | Census test |
|---|---|---|---|---|
| FAQ structured data | Optional. Keep it only if it matches visible text. | **[U]** | Google stopped showing FAQ rich results from 7 May 2026, so there is no Google display benefit. No evidence found that it helps AI answers. ([Google Search Central updates](https://developers.google.com/search/updates)) | In place within CT-001; not isolated |
| llms.txt | Optional. Cheap to add, but do not expect results from it alone. | **[U]** | A proposal by Jeremy Howard, first published September 2024. Google says AI text files are not needed for its AI features. Whether AI crawlers fetch it is what the Census is logging. ([llmstxt.org](https://llmstxt.org/)) | LL-001 running; RT-001 from 1 Dec 2026 |
| Markdown versions of pages | Optional. | **[U]** | No platform documentation or study found. | Logged within CT-001 |
| Content Signals line in robots.txt | Optional. Know that no AI company has been found committing to honor it. | **[U]** | A robots.txt extension introduced by Cloudflare in September 2025. No AI company found committing to honor it. ([Cloudflare, Content Signals Policy](https://blog.cloudflare.com/content-signals-policy/)) | CS-001 running |
| Question-style headings | Optional. | **[U]** | Claimed to get quoted word for word. Not checked here. | Not tested |
| Rank in Google's top 10 for the question | Check your ranking for the main query behind each question. | **[U]** | Claimed to be required for AI Overview citations. Claims vary between vendor studies; not checked here. | Not tested |
| Earn backlinks to the pages you want cited | Referring domains to each key page, from Ahrefs, Semrush or Bing Webmaster Tools. | **[U]** | Claimed that a page with no backlinks will not be cited. Not checked here. | Not tested (BL-001 measures links, not citations) |
| Share new pages on LinkedIn to speed up the first Bing crawl | Optional. | **[U]** | Claimed to speed up the first Bing and Copilot crawl. Not checked here. | Not tested |

## 5. Never

| Check | How to check | Grade | What the evidence says | Census test |
|---|---|---|---|---|
| Hidden instructions aimed at AI assistants | Check "Summarize with AI" buttons and share links on your site: none should carry a prompt telling the assistant to remember or favor your brand. | **Do not use** | Microsoft describes companies hiding instructions that tell an assistant to remember and favor their brand, and calls it "AI Recommendation Poisoning". ([Microsoft Security, 10 February 2026](https://www.microsoft.com/en-us/security/blog/2026/02/10/ai-recommendation-poisoning/)) | Never |

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credit: AI Visibility Census, aivisibilitycensus.com/templates/geo-checklist/

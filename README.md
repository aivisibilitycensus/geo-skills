# GEO skills

[![tests](https://github.com/aivisibilitycensus/geo-skills/actions/workflows/tests.yml/badge.svg)](https://github.com/aivisibilitycensus/geo-skills/actions/workflows/tests.yml) [![Code: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE) [![Docs and data: CC BY 4.0](https://img.shields.io/badge/docs%20%26%20data-CC%20BY%204.0-lightgrey.svg)](LICENSE-docs)

**Your GEO audit says 87 out of 100. Can ChatGPT's crawler even reach the page?**

A score cannot tell you. These nine free skills can: they list what blocks a page from AI search, count how often AI engines actually name you, and say when the numbers are too thin to mean anything. For Claude and other AI assistants, and every script also runs on its own from the command line.

Built on the published method of the [AI Visibility Census](https://aivisibilitycensus.com/methodology/).

## Why use this instead of a GEO score

| What a score gives you | What these skills give you |
|---|---|
| One number out of 100 | Findings in order of what blocks you, each with what to do |
| A number nobody has tested against AI answers. We searched nine open-source GEO audit repositories on 10 November 2026 and [found no published test](validation/SV-001-protocol.md) | No score. And we are [testing in public](validation/SV-001-protocol.md) whether scores go with being named at all, with the result published either way |
| "Up 17 points this month", with no way to tell a real change from chance | "Up 17 points, and that is inside the noise": every rate comes with a 95% range and the number of answers behind it |

Also here, and not common:

- **Every tactic is graded by its evidence** ([tactics/EVIDENCE.md](tactics/EVIDENCE.md)): the platform documents it, a study found it, or nobody has tested it. llms.txt is graded untested, and we say so.
- **Crawler visits are verified** against the IP ranges the companies publish, so a fake "GPTBot" is not counted.
- **Experiments are registered before the data exists**, and null results get published.
- **Nothing to install beyond Python 3.** No account for the checks, and your data stays on your machine. Only the answer collector needs a key, and it is your own.
- **Tests run on every change.**

What you get is less flattering than a score and more useful: the three things to fix, the count you can defend to a client, and a plain "we can't tell yet" when that is the truth.

**When another tool is the better choice:** if you want a full SEO suite, client-ready PDF reports or content generation, the larger repositories do far more than this one, and several are very good at it. This repo does one job: honest measurement.

## Start here

Check one page, no account and nothing to install beyond Python 3:

```
git clone https://github.com/aivisibilitycensus/geo-skills
python3 geo-skills/geo-check/scripts/geo_check.py https://example.com/your-page
```

You get a short list of what stops AI search engines from reading that page, each item with the evidence behind it. [Example output](geo-check/examples/output-report.md). There is no score out of 100, on purpose: whether audit scores go with being named by AI is an open question, and we are [testing it in public](validation/SV-001-protocol.md).

### Run it on every deploy

As a GitHub Action, with the findings in the job summary:

```yaml
- uses: aivisibilitycensus/geo-skills@main
  with:
    urls: |
      https://example.com/
      https://example.com/pricing
```

The job fails if a page has a blocking finding, such as a `noindex` that shipped from staging or a robots.txt rule against a search crawler. When nothing blocks, `--badge` prints a README badge that states the count and the date, not a score:

[![AI search check: 0 blocking findings](https://img.shields.io/badge/AI%20search%20check-0%20blocking-2ea44f)](geo-check/)

## See it work

The answer log analyzer on its worked example (a fictional Dublin accounting firm, 108 logged answers a month on three engines):

![Share of answers naming the brand by engine, September and October, with 95% ranges that overlap on every engine](assets/analyzer-example.svg)

| Engine | Named, September | Named, October |
|---|---|---|
| chatgpt | 28% (16-44%), n=36 | 33% (20-50%), n=36 |
| copilot | 14% (6-29%), n=36 | 19% (10-35%), n=36 |
| perplexity | 31% (18-47%), n=36 | 47% (32-63%), n=36 |

A nearly 17-point jump on one engine, and the report says it is not outside the noise. That is the point of these skills: counts with ranges, not a score. Full output: [answer-log-analyzer/examples/example-report.md](answer-log-analyzer/examples/example-report.md).

## Skills

| Skill | What it does | Needs |
|---|---|---|
| [geo-check](geo-check/) | One command: can AI search reach and read this page? Page response, noindex, robots.txt for 11 crawler tokens, text without JavaScript, structured data, firewall hints. Findings in four tiers with evidence grades | A URL |
| [question-set-builder](question-set-builder/) | Builds a fixed set of buyer questions with stable IDs, spread across buying intents, for tracking AI visibility | Nothing |
| [answer-collector](answer-collector/) | Runs the question set on ChatGPT, Gemini, Google AI Overviews, AI Mode and Copilot with repeats, and logs every answer and cited URL | Your own DataForSEO or SerpApi key |
| [answer-log-analyzer](answer-log-analyzer/) | Reads logged AI answers from repeated runs and reports named, cited, cited-but-someone-else-named and absent, with run-to-run variance and an honest month-on-month comparison | A CSV of answers (from answer-collector, a tracker export or a manual log) |
| [schema-parity-checker](schema-parity-checker/) | Checks that a page's structured data says only what the visible page says: FAQ text, prices, ratings, contact details, dates | A URL or saved HTML |
| [geo-migration-guard](geo-migration-guard/) | Protects AI search visibility through a site migration: baseline, redirect map check, post-launch parity, robots.txt changes for AI crawlers | URL lists and a redirect map |
| [ai-crawler-log-check](ai-crawler-log-check/) | Analyzes server logs for AI and search crawlers and verifies them against published IP ranges and reverse DNS, so spoofed bots are not counted | Access logs |
| [content-shape-checker](content-shape-checker/) | Checks whether a draft is built like human writing or generated text (over-explanation, named specifics, scaffold variance, profundity inflation) and quotes every sentence to fix. Also available as a [free web tool](https://aivisibilitycensus.com/content-shape-checker/) | A draft with headings |
| [geo-experiment-kit](geo-experiment-kit/) | Templates and a readout script for running one-change-at-a-time SEO and GEO experiments with control pages and recorded predictions | Nothing |

## Templates

Free spreadsheets in [templates/](templates/): an [SEO report template with AI visibility](https://aivisibilitycensus.com/templates/seo-report-template/) (95% ranges on every AI rate), a [GEO checklist graded by evidence](templates/geo-checklist.md), and an [AI Overview CTR loss finder](https://aivisibilitycensus.com/templates/ai-overview-ctr-loss/) for Search Console data.

Every recommendation carries an evidence grade from [tactics/EVIDENCE.md](tactics/EVIDENCE.md): tested by the Census, published study, platform documentation, vendor claim, or untested.

The scripts are Python 3 and use the standard library only (schema-parity-checker can optionally render pages with Playwright). Each skill with a script has a worked example built from synthetic data, with the real script output, and tests that run on every push.

## Install

**Claude (claude.ai or the desktop app):** zip a skill folder, then in Settings > Capabilities turn on code execution, scroll to Skills, click "Upload skill" and choose the zip. [Anthropic's guide](https://support.claude.com/en/articles/12512180-using-skills-in-claude) has the details.

**Claude Code (plugin, all nine skills):**

```
/plugin marketplace add aivisibilitycensus/geo-skills
/plugin install geo-skills@geo-skills
```

On Claude Code 2.1.275 or later, one step: `/plugin install geo-skills --marketplace aivisibilitycensus/geo-skills`.

**Claude Code (one skill):** copy the skill folder into `~/.claude/skills/` (personal) or `.claude/skills/` in a project. Copy `tactics/` alongside the skills so the evidence links resolve.

**Other assistants:** each `SKILL.md` is plain markdown. Paste it into a custom GPT, a Gem or a project's instructions. The scripts run on their own from the command line.

## A typical workflow

1. Run **geo-check** on the pages you want named, and fix anything that blocks.
2. Build the questions with **question-set-builder**.
3. Collect answers with **answer-collector**: at least three per question, per engine, per check date.
4. Analyze the log with **answer-log-analyzer**.
5. Fix what the data points to, one change at a time, using **geo-experiment-kit**.
6. Check drafts with **content-shape-checker** before they ship.
7. Use **schema-parity-checker**, **ai-crawler-log-check** and **geo-migration-guard** for the deeper technical checks.

## Open studies

Run in this repository, registered before the data exists, published whichever way they come out:

- [SV-001](validation/SV-001-protocol.md): do GEO audit scores go with being named by AI? Two open-source scoring scripts against Census100 answer data for 20 project management brands. Registered 10 November 2026.
- [VS-001](validation/VS-001-protocol.md): how often does the Content Shape Checker flag articles written by people?

## If it helped, pass it on

This repo grows by people showing other people what it found. Three ways, each under a minute:

- **Star it.** Stars are how the next person finds it.
- **Show your result.** Run `geo_check.py --badge` and paste the badge line in your README or site footer when nothing blocks. It states a count and a date, and links back here.
- **Tell one person who reports GEO numbers to a client.** The line that usually lands: "it tells you when a change is inside the noise."

Found a wrong grade, a false finding or a missing check? [Open an issue](https://github.com/aivisibilitycensus/geo-skills/issues/new). See [CONTRIBUTING.md](CONTRIBUTING.md) for the five-minute ways to help.

## License

Code is [MIT](LICENSE). Skill text, evidence grades, templates, examples and data are [CC BY 4.0](LICENSE-docs): reuse them, including commercially, with credit to the AI Visibility Census. [LICENSING.md](LICENSING.md) says which files are which.

## Feedback

Open an issue, or email hello@aivisibilitycensus.com. If a grade in the evidence file is wrong, send the source.

# GEO skills

Open skills for Claude and other AI assistants that help you measure and check how a business appears in AI search. Built on the published method of the [AI Visibility Census](https://aivisibilitycensus.com/methodology/).

Most GEO tools give you a score. These skills give you counts you can trace back to data, say how sure the data lets you be, and grade every tactic by the evidence behind it. None of them promise that a business will be named, and none of them use hidden instructions or tricks aimed at AI systems.

## See it work

The answer log analyzer on its worked example (a fictional Dublin accounting firm, 108 logged answers a month on three engines):

![Share of answers naming the brand by engine, September and October, with 95% ranges that overlap on every engine](assets/analyzer-example.svg)

| Engine | Named, September | Named, October |
|---|---|---|
| chatgpt | 28% (16-44%), n=36 | 33% (20-50%), n=36 |
| copilot | 14% (6-29%), n=36 | 19% (10-35%), n=36 |
| perplexity | 31% (18-47%), n=36 | 47% (32-63%), n=36 |

A nearly 17-point jump on one engine, and the report says it is not outside the noise. That is the point of these skills: counts with ranges, not a score. Full output: [answer-log-analyzer/examples/example-report.md](answer-log-analyzer/examples/example-report.md).

If a skill saves you time, star the repo. Stars are how other people find it.

## Skills

| Skill | What it does | Needs |
|---|---|---|
| [question-set-builder](question-set-builder/) | Builds a fixed set of buyer questions with stable IDs, spread across buying intents, for tracking AI visibility | Nothing |
| [answer-log-analyzer](answer-log-analyzer/) | Reads logged AI answers from repeated runs and reports named, cited, cited-but-someone-else-named and absent, with run-to-run variance and an honest month-on-month comparison | A CSV of answers (tracker export or manual) |
| [schema-parity-checker](schema-parity-checker/) | Checks that a page's structured data says only what the visible page says: FAQ text, prices, ratings, contact details, dates | A URL or saved HTML |
| [geo-migration-guard](geo-migration-guard/) | Protects AI search visibility through a site migration: baseline, redirect map check, post-launch parity, robots.txt changes for AI crawlers | URL lists and a redirect map |
| [ai-crawler-log-check](ai-crawler-log-check/) | Analyzes server logs for AI and search crawlers and verifies them against published IP ranges and reverse DNS, so spoofed bots are not counted | Access logs |
| [content-shape-checker](content-shape-checker/) | Checks whether a draft is built like human writing or generated text (over-explanation, named specifics, scaffold variance, profundity inflation) and quotes every sentence to fix. Also available as a [free web tool](https://aivisibilitycensus.com/content-shape-checker/) | A draft with headings |
| [geo-experiment-kit](geo-experiment-kit/) | Templates and a readout script for running one-change-at-a-time SEO and GEO experiments with control pages and recorded predictions | Nothing |

## Templates

Free spreadsheets in [templates/](templates/): an [SEO report template with AI visibility](https://aivisibilitycensus.com/templates/seo-report-template/) (95% ranges on every AI rate), a [GEO checklist graded by evidence](templates/geo-checklist.md), and an [AI Overview CTR loss finder](https://aivisibilitycensus.com/templates/ai-overview-ctr-loss/) for Search Console data.

Every recommendation carries an evidence grade from [tactics/EVIDENCE.md](tactics/EVIDENCE.md): tested by the Census, published study, platform documentation, vendor claim, or untested.

The scripts are Python 3 and use the standard library only (schema-parity-checker can optionally render pages with Playwright). Each skill with a script has a worked example built from synthetic data, with the real script output.

## Install

**Claude (claude.ai or the desktop app):** zip a skill folder, then in Settings > Capabilities turn on code execution, scroll to Skills, click "Upload skill" and choose the zip. [Anthropic's guide](https://support.claude.com/en/articles/12512180-using-skills-in-claude) has the details.

**Claude Code (plugin, all seven skills):**

```
/plugin marketplace add aivisibilitycensus/geo-skills
/plugin install geo-skills@geo-skills
```

On Claude Code 2.1.275 or later, one step: `/plugin install geo-skills --marketplace aivisibilitycensus/geo-skills`.

**Claude Code (one skill):** copy the skill folder into `~/.claude/skills/` (personal) or `.claude/skills/` in a project. Copy `tactics/` alongside the skills so the evidence links resolve.

**Other assistants:** each `SKILL.md` is plain markdown. Paste it into a custom GPT, a Gem or a project's instructions. The scripts run on their own from the command line.

## A typical workflow

1. Build the questions with **question-set-builder**.
2. Run them on each engine, at least three times per check date, and log the answers.
3. Analyze the log with **answer-log-analyzer**.
4. Fix what the data points to, one change at a time, using **geo-experiment-kit**.
5. Check drafts with **content-shape-checker** before they ship.
6. Use **schema-parity-checker**, **ai-crawler-log-check** and **geo-migration-guard** to check the technical side.

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Use, adapt and share, including commercially, with credit to the AI Visibility Census.

## Feedback

Open an issue, or email hello@aivisibilitycensus.com. If a grade in the evidence file is wrong, send the source.

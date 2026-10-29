# GEO skills

Open skills for Claude and other AI assistants that help you measure and check how a business appears in AI search. Built on the published method of the [AI Visibility Census](https://aivisibilitycensus.com/methodology/).

Most GEO tools give you a score. These skills give you counts you can trace back to data, say how sure the data lets you be, and grade every tactic by the evidence behind it. None of them promise that a business will be named, and none of them use hidden instructions or tricks aimed at AI systems.

## Skills

| Skill | What it does | Needs |
|---|---|---|
| [question-set-builder](question-set-builder/) | Builds a fixed set of buyer questions with stable IDs, spread across buying intents, for tracking AI visibility | Nothing |
| [answer-log-analyzer](answer-log-analyzer/) | Reads logged AI answers from repeated runs and reports named, cited, cited-but-someone-else-named and absent, with run-to-run variance and an honest month-on-month comparison | A CSV of answers (tracker export or manual) |
| [schema-parity-checker](schema-parity-checker/) | Checks that a page's structured data says only what the visible page says: FAQ text, prices, ratings, contact details, dates | A URL or saved HTML |
| [geo-migration-guard](geo-migration-guard/) | Protects AI search visibility through a site migration: baseline, redirect map check, post-launch parity, robots.txt changes for AI crawlers | URL lists and a redirect map |
| [ai-crawler-log-check](ai-crawler-log-check/) | Analyzes server logs for AI and search crawlers and verifies them against published IP ranges and reverse DNS, so spoofed bots are not counted | Access logs |
| [geo-experiment-kit](geo-experiment-kit/) | Templates and a readout script for running one-change-at-a-time SEO and GEO experiments with control pages and recorded predictions | Nothing |

Every recommendation carries an evidence grade from [tactics/EVIDENCE.md](tactics/EVIDENCE.md): tested by the Census, published study, platform documentation, vendor claim, or untested.

The scripts are Python 3 and use the standard library only (schema-parity-checker can optionally render pages with Playwright). Each skill has a worked example built from synthetic data, with the real script output.

## Install

**Claude (claude.ai or the desktop app):** zip a skill folder, then in Settings > Capabilities turn on code execution, scroll to Skills, click "Upload skill" and choose the zip. [Anthropic's guide](https://support.claude.com/en/articles/12512180-using-skills-in-claude) has the details.

**Claude Code:** copy the skill folder into `~/.claude/skills/` (personal) or `.claude/skills/` in a project. Copy `tactics/` alongside the skills so the evidence links resolve.

**Other assistants:** each `SKILL.md` is plain markdown. Paste it into a custom GPT, a Gem or a project's instructions. The scripts run on their own from the command line.

## A typical workflow

1. Build the questions with **question-set-builder**.
2. Run them on each engine, at least three times per check date, and log the answers.
3. Analyze the log with **answer-log-analyzer**.
4. Fix what the data points to, one change at a time, using **geo-experiment-kit**.
5. Use **schema-parity-checker**, **ai-crawler-log-check** and **geo-migration-guard** to check the technical side.

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Use, adapt and share, including commercially, with credit to the AI Visibility Census.

## Feedback

Open an issue, or email hello@aivisibilitycensus.com. If a grade in the evidence file is wrong, send the source.

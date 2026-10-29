# GEO skills

Open skills for Claude and other AI assistants that help you measure and improve how a business appears in AI search. Built on the published method of the [AI Visibility Census](https://aivisibilitycensus.com/methodology/).

The skills are about measuring honestly and writing pages AI tools can use. None of them promise that a business will be named, and none of them use hidden instructions or tricks aimed at AI systems.

## Skills

| Skill | What it does | Status |
|---|---|---|
| [question-set-builder](question-set-builder/) | Builds a fixed set of buyer questions, with stable IDs, for tracking AI visibility across ChatGPT, Perplexity, Copilot, Gemini, Google AI Overviews and Claude | Available |
| geo-page-audit | Checks a page against what AI tools need to cite it | Planned |
| schema-writer | Writes structured data that matches what the page actually says | Planned |

## Install

**Claude (claude.ai or the desktop app):** zip the skill folder, then in Settings > Capabilities turn on code execution, scroll to Skills, click "Upload skill" and choose the zip. [Anthropic's guide](https://support.claude.com/en/articles/12512180-using-skills-in-claude) has the details.

**Claude Code:** copy the skill folder into `~/.claude/skills/` (personal) or `.claude/skills/` in a project.

**Other assistants:** each `SKILL.md` is plain markdown. Paste it into a custom GPT, a Gem or a project's instructions.

## Example

Ask: "Build a question set to track AI visibility for a commercial cleaning company in Manchester." See [the example output](question-set-builder/examples/commercial-cleaning-manchester.md).

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Use, adapt and share, including commercially, with credit to the AI Visibility Census.

## Feedback

Open an issue, or email hello@aivisibilitycensus.com.

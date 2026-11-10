# Contributing

The most useful contributions are small and specific.

## Five-minute ways to help

1. **Run `geo-check` on a real page and tell us what was wrong or missing.** A false "blocks" finding is the most valuable bug report there is. Include the URL (or a saved copy of the HTML) and the output.
2. **Send a source for an evidence grade.** If a tactic in [tactics/EVIDENCE.md](tactics/EVIDENCE.md) is graded untested and you know a study or platform document, open an issue with the link. Grades move only when the evidence does.
3. **Share an anonymized answer log.** A CSV in the [answer-log-analyzer](answer-log-analyzer/) format with brand names replaced helps test the analyzer on shapes we have not seen.
4. **Report a provider change.** If `answer-collector` returns an error for an engine, attach the raw response from the `-raw` folder with keys removed.

## Rules for changes

- **No scores.** A pull request that adds a composite score will be declined. Counts, rates with ranges, and findings are welcome.
- **No promises.** Nothing in a skill may say or imply that a change will get a business named by an AI engine.
- **Every recommendation carries a grade** from `tactics/EVIDENCE.md`, with a primary source for [P] and [S].
- **Standard library only** for scripts, with tests that run without network access. `python3 -m unittest discover -s tests` from the skill folder must pass.
- **Worked examples use fictional businesses** on `.example` domains.
- Do not name or criticize other tools in skill text. Comparisons belong in studies with a registered protocol under `validation/`.

## Licensing of contributions

Code you contribute is licensed MIT and everything else CC BY 4.0, as described in [LICENSING.md](LICENSING.md).

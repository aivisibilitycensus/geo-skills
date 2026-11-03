# VS-001 study code

Code for the pre-registered validation study in [VS-001-protocol.md](../VS-001-protocol.md). Anyone can rerun it.

| Step | Script | What it does | Where it runs |
|---|---|---|---|
| 1 | `sample.mjs` | Lists every archived article-like URL per blog (Appendix A) from the Wayback Machine CDX index, captures 1 Jan 2019 to 31 Oct 2022, and shuffles each blog's list with the fixed seed 20261029. Writes `data/candidates/`. | GitHub Actions (`vs-001.yml`) |
| 2 | `fetch.mjs` | Walks each list in order, fetches the earliest capture on or before 31 Oct 2022, reduces it to the article body with Mozilla Readability, converts to Markdown, applies the inclusion rules (article, English, 500 to 3,000 words, 3 or more subheadings), keeps the first four per blog, and replaces a blog with fewer than four by its group's next reserve blog. Writes `data/human/<id>.md` and `data/human/manifest.csv`, which records every candidate looked at and why it was excluded. | GitHub Actions |
| 3 | `prompts.mjs` | Builds one prompt per accepted human title with the Appendix B wording. Writes `data/prompts.csv`. Model outputs go to `data/ai/<model>/<id>.md`, unedited. | Anywhere |
| 4 | `check.mjs` | Runs one archived copy of the checker (`checkers/hsc-<version>.cjs`, hash recorded in every row) over the human and AI corpora, exactly as the browser tool does: top-level heading removed, then `parseText` and `analyze`. Writes `data/results/<version>.csv`. | GitHub Actions or locally |

The human texts are not republished. The manifest links each one to its archived copy.

## Checker versions on file

- `checkers/hsc-1.5.4.cjs`: the live checker on 3 November 2026 (plugin Content Shape Checker 1.5.4; the file header still reads 1.5.1). SHA-256 `27941ab50c0670bf65f6498526571e2d6465af40ee17f3464b4fc0fb957c49ae`, 106,798 bytes.
- `hsc-1.1.0.cjs` and `hsc-1.5.0.cjs` (SHA-256 `c712c76e...` per the protocol correction of 30 October 2026) are **not yet on file**. The protocol registers 1.1.0 as the version under test; a copy must be recovered from the 29 October 2026 plugin build before the 1.1.0 results can be run. If no copy exists, that is logged as a protocol correction, not papered over.

## Training-set exclusion (protocol correction of 30 October 2026)

The 1.5.0 reading was trained and tested on the documents listed in the published October 2026 test CSV (`content-shape-ai-test-2026-10.csv` on aivisibilitycensus.com): human posts from the PostHog blog, 18F guides, the Basecamp handbook, the Sourcegraph blog and GitHub's Open Source Guides, and AI posts from Claude models. None of those sources is in Appendix A, so no sampled article can overlap; the exclusion rule is satisfied by construction and no URL list is needed.

## Running

```
cd validation/vs-001 && npm ci
node sample.mjs && node fetch.mjs && node prompts.mjs
node check.mjs --checker checkers/hsc-1.5.4.cjs --label 1.5.4 --corpus data/human --corpus data/ai/claude --out data/results/1.5.4.csv
```

The Wayback Machine is not reachable from the Census agent's cloud workspace, so steps 1 and 2 run as the GitHub workflow.

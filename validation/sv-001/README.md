# SV-001 working files

Protocol: [../SV-001-protocol.md](../SV-001-protocol.md). Read that first; nothing here overrides it.

| File | What it is |
|---|---|
| `urls.csv` | The 20 brands and the one page scored for each |
| `smoke-urls.csv` | Two pages outside the study, for testing the pipeline |
| `run_scores.py` | Runs the two third-party scripts on each URL and records the score each reports |
| `analyze.py` | Spearman correlation with permutation p-values and the fixed decision rule |
| `test_analyze.py` | Tests for the statistics |
| `runs/` | Output of each score run: `scores.csv`, raw script output, environment |

## Running it

1. Scores: run the "SV-001 score run" workflow with `urls` set to `validation/sv-001/urls.csv` and `label` set to the date. It commits the results to `runs/<label>/`.
2. Outcomes: after the 17 November collection, export `outcomes.csv` (columns `domain, engine, answers, named, cited`) from the Census100 data in aivisibilitycensus/census-index.
3. Readout: `python3 analyze.py runs/<label>/scores.csv outcomes.csv --covars covars.csv --out-md readout.md`

The scoring job runs code from two outside repositories at pinned commits. It has read-only permissions and no secrets.

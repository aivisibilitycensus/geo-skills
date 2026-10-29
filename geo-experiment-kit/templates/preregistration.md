# Experiment pre-registration

Fill this in and date-stamp it before the change goes live and before any "after" data is looked at. Once dated, do not edit it. If something has to change, add a dated amendment at the bottom saying what changed and why.

- **Experiment ID:**
- **Site:**
- **Date registered (YYYY-MM-DD):**
- **Registered by:**
- **Where this is recorded** (a public page, a commit, a shared doc with version history, an email to someone outside the work): 

## 1. Hypothesis

One sentence: "Changing [X] on [pages] will [increase / decrease] [metric] because [reason]."

Where the idea came from, and its evidence grade (see ../tactics/EVIDENCE.md): [T] / [S] / [P] / [V] / [U]

## 2. The single change

Exactly what will be changed, on which date, by whom. Specific enough that someone else could repeat it. Only one change. If two things change at once, the result cannot be attributed to either.

- Change:
- Go-live date:
- How it can be reversed:

## 3. Pages

| Role | URL | Why chosen |
|---|---|---|
| Test | | |
| Test | | |
| Control | | |
| Control | | |

Controls should be as similar to the test pages as possible (same template, same section, similar traffic and age) and must not receive the change, or any other change, during the experiment. If pages were assigned at random, say how (coin, random number list).

## 4. Metrics

Primary metric (the one the result is judged on, chosen now):

Secondary metrics (reported, but not used to decide the outcome):

| Metric | Source | How measured | Unit (k out of n, count, position) |
|---|---|---|---|
| Crawled | Server or CDN logs (ai-crawler-log-check), verified hits only | | |
| Indexed | Search Console URL inspection or index coverage | | |
| Rank | Rank tracker or Search Console average position, named queries | | |
| AI named | answer-log-analyzer: answers that name the business, out of answers collected | | |
| AI cited | answer-log-analyzer: answers that cite a test page, out of answers collected | | |

Fixed question set for AI measurement (IDs from question-set-builder):

Engines checked:

## 5. Measurement plan

- **Baseline dates** (before the change):
- **Follow-up dates** (after the change):
- **Runs per question per engine per date:**
- **Total observations per cell** (test before, test after, control before, control after):
- **Same conditions each time** (logged out, same location, same time of day where possible):

## 6. Decision rules (set now, not after)

- **Minimum effect worth acting on:** (for example, +10 percentage points in AI named rate on test pages relative to control)
- **What counts as "worked":**
- **What counts as "no detectable effect":** (for example, the whole interval for the difference-in-differences sits inside plus or minus the minimum effect)
- **What counts as "made it worse":**
- **Otherwise:** inconclusive.
- **Analysis method:** (for example, difference-in-differences with Wilson intervals, scripts/readout.py, 95%)

## 7. Known confounders

Things that could move the numbers without the change causing it. List what will be watched and how.

- Search engine or AI model updates announced or observed during the window:
- Seasonality or news in the sector:
- Other edits to the site (check the change log; none allowed on test or control pages):
- Changes to internal links, navigation or sitemaps:
- Outages, migrations, robots.txt or CDN rule changes:
- AI engine product changes (new model, new search feature):

## 8. Commitment

The result will be written up with templates/readout.md whatever it shows, including no effect.

## Amendments

| Date | What changed | Why |
|---|---|---|

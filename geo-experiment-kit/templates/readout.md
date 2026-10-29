# Experiment readout

- **Experiment ID:**
- **Pre-registration:** (link or location, and its date)
- **Change went live (YYYY-MM-DD):**
- **Readout date (YYYY-MM-DD):**
- **Written by:**

## What was tested

One or two sentences, copied from the pre-registration: the hypothesis and the single change.

## Results

Primary metric:

| Cell | Measured on | k | n | Rate | Interval |
|---|---|---|---|---|---|
| Test, before | | | | | |
| Test, after | | | | | |
| Control, before | | | | | |
| Control, after | | | | | |

| | Estimate | Interval |
|---|---|---|
| Change on test pages | | |
| Change on control pages | | |
| Difference-in-differences | | |

Method and confidence level: (for example, scripts/readout.py, Wilson intervals, MOVER for differences, 95%)

Secondary metrics (reported, not used for the decision):

| Metric | Test before | Test after | Control before | Control after | Notes |
|---|---|---|---|---|---|
| | | | | | |

## Deviations from the plan

Anything that did not go as registered: missed measurement dates, fewer runs, a control page that was edited, an engine that changed. Write "none" if none.

## Confounders observed

Algorithm or model updates, seasonality, other site edits from the change log, outages. Write "none observed" if none, and say how it was checked.

## Outcome

Pick one, using the rule written in the pre-registration:

- [ ] **Worked:** the effect meets the pre-registered rule.
- [ ] **No detectable effect:** the data rules out an effect as large as the minimum worth acting on.
- [ ] **Inconclusive:** the data cannot tell. Not the same as "no effect".
- [ ] **Made it worse:** the effect meets the pre-registered rule in the wrong direction.

## What we can conclude

Only what the numbers support, for these pages, on these engines, in this window.

## What we cannot conclude

At minimum: whether this would happen on other pages or sites, whether it lasts, and anything a small sample cannot separate from noise. Name the specific limits of this experiment.

## Next step

One of: roll out to more pages, repeat with more observations, reverse the change, or stop. Say which and why.

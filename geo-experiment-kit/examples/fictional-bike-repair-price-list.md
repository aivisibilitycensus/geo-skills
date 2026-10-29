# Example: price list on service pages (fictional)

An example run of the geo-experiment-kit skill. **The business, the site and every number below are invented.** Brightwater Bikes does not exist, and `brightwater-bikes.example` is a reserved example domain. Nothing here is a real result.

## Pre-registration (excerpt)

- **Experiment ID:** BWB-01
- **Date registered:** 2026-08-25, emailed to the shop's accountant as a dated record
- **Hypothesis:** Adding a plain-language price list to service pages will increase the share of AI answers that name Brightwater Bikes, because the answers to "how much does X cost" questions need a source with prices. Evidence grade: [U] untested.
- **Single change:** a price table (service, price, typical turnaround) above the fold on 4 service pages, live 2026-09-01.
- **Test pages:** wheel truing, brake service, gear tune, puncture repair (chosen by coin flip from 8 service pages).
- **Control pages:** chain replacement, bottom bracket, suspension service, bike fit (the other 4; no edits allowed during the window).
- **Primary metric:** AI named rate: answers that name Brightwater Bikes, out of answers collected, for the questions mapped to each page group.
- **Measurement:** 10 fixed questions per group (5 per page pair), 2 engines, 2 runs each, so 40 answers per cell. Baseline 2026-08-26 and 2026-08-28 pooled; follow-up 2026-09-29 and 2026-10-01 pooled.
- **Minimum effect worth acting on:** +10 percentage points, test change minus control change.
- **Rules:** worked if the difference-in-differences interval excludes zero and the estimate is at least +10 points; no detectable effect if the whole interval sits inside plus or minus 10 points; made it worse if the mirror of "worked"; otherwise inconclusive.
- **Confounders watched:** announced search and AI model updates, the change log, seasonal demand (September is busy for commuter repairs).

## Change log

See `sample-change-log.csv`. One non-test edit (opening hours on the contact page) was logged during the window.

## Readout command and output (verbatim)

```
python3 scripts/readout.py --test-before 3/40 --test-after 11/40 --control-before 4/40 --control-after 5/40 --min-effect 0.10
```

```
Wilson 95% intervals per cell

cell                  k/n     rate            interval
test_before          3/40     7.5%       2.6% to 19.9%
test_after          11/40    27.5%      16.1% to 42.8%
control_before       4/40    10.0%       4.0% to 23.1%
control_after        5/40    12.5%       5.5% to 26.1%

Changes in percentage points, approximate 95% intervals (MOVER)

test change        +20.0 pts   (+3.2 pts to +36.1 pts)
control change      +2.5 pts   (-12.3 pts to +17.4 pts)
diff-in-diff       +17.5 pts   (-5.0 pts to +39.4 pts)

Suggested label: inconclusive (the interval includes both zero and effects at least as large as the minimum)
Check this against the rule written in the pre-registration before using it.
```

## Readout (filled template, abridged)

- **Outcome:** inconclusive.
- **What we can conclude:** on the test pages, the named rate went from 7.5% to 27.5% (3 of 40 to 11 of 40 answers). The control pages went from 10.0% to 12.5%. The estimated effect of the change is +17.5 points, which would clear the +10 point bar if it held.
- **What we cannot conclude:** whether the change caused it. The interval for the difference-in-differences runs from -5.0 to +39.4 points, so it includes zero and it includes effects much larger than the minimum. With 4 pages per group and 40 answers per cell, this is directional at best. The opening-hours edit is on a page outside both groups and is unlikely to explain a difference between them, but it is logged.
- **Deviations from the plan:** none.
- **Next step:** repeat the follow-up measurement with 4 runs per question per engine (80 answers per cell) on two more dates before adding price lists to the control pages.

Note what a before-and-after look at the test pages alone would have said: "+20 points, interval excludes zero, it worked." The control pages are what turn that into an honest "not yet known".

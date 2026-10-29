---
name: geo-experiment-kit
description: Plan, run and write up honest SEO and GEO (AI search) experiments on a website, with a dated pre-registration, one change at a time, control pages, repeated measurement and a readout that reports null results. Use when someone wants to test whether a page change affects crawling, indexing, rankings or being named and cited in AI answers, or asks "did this change work?".
---

# GEO experiment kit

Helps run a website experiment that can actually answer "did this change make a difference?", and write up the answer honestly, including when the answer is "we can't tell". It provides three templates and one small script:

- `templates/preregistration.md`: the plan, written and dated before any results exist.
- `templates/change-log.csv`: every edit to the site during the experiment.
- `templates/readout.md`: the write-up, with fixed outcome labels.
- `scripts/readout.py`: difference-in-differences with Wilson intervals for "k out of n" measures.

Most SEO and GEO advice comes from one before-and-after look at one page. That can't separate the change from everything else that moved at the same time: search updates, AI model changes, seasonality, other edits. The process below is how to do better with the pages a real site has.

## Step 1: Pick one change and write the hypothesis

Ask what the user wants to test and why they think it will work. Write one sentence: "Changing [X] on [pages] will [increase / decrease] [metric] because [reason]."

Tag where the idea came from with an evidence grade (Evidence grades: see ../tactics/EVIDENCE.md): [T] tested by the Census, [S] published study, [P] platform documentation, [V] vendor or practitioner claim, [U] untested. Most ideas worth testing are [V] or [U]; that's why they need a test.

**One change only.** If the user wants to add schema, rewrite the intro and add an FAQ at the same time, that is three experiments. Ask which one matters most, or run them on separate page groups.

## Step 2: Choose test and control pages

- **Test pages** get the change. **Control pages** don't, and get no other edits either.
- Controls should match the test pages as closely as possible: same template, same section, similar age, traffic and current visibility.
- If there are several candidate pages, assign them at random (a coin flip per page is fine) rather than putting the "best" pages in the test group.
- Without controls, any movement could be the whole site, the engine or the season. If the site truly has no comparable pages, say plainly in the plan that the result will be a before-and-after observation, not a controlled test.

## Step 3: Pick metrics and measurement dates

Choose **one primary metric** now. The outcome is judged on it alone. Others are reported as secondary.

Typical metrics, from earliest to latest in the chain:

| Metric | Source |
|---|---|
| Crawled | Server or CDN logs, verified crawler hits only (sibling skill ai-crawler-log-check) |
| Indexed | Search Console URL inspection or page indexing report |
| Rank | Search Console or a rank tracker, for named queries |
| AI named | Answers that name the business, out of answers collected (sibling skill answer-log-analyzer) |
| AI cited | Answers that cite a test page, out of answers collected (answer-log-analyzer) |

For AI metrics, use a fixed question set (sibling skill question-set-builder), the same engines, and the same conditions on every date. AI answers vary from run to run, so ask each question several times per engine per date. Count observations per cell (test before, test after, control before, control after); that number decides how small an effect the experiment can see.

Set dates now: at least two baseline dates before the change, and follow-up dates far enough out for the metric to respond (crawling responds faster than citations).

## Step 4: Set the decision rules, then register the plan

Fill in `templates/preregistration.md`, including:

- **Minimum effect worth acting on.** For example, "+10 percentage points in AI named rate on test pages relative to control." Smaller than this and the change isn't worth rolling out even if it's real.
- **What counts as worked, no detectable effect, made it worse,** and that everything else is inconclusive.
- **Known confounders** and how each will be watched.

Then date-stamp it and put it somewhere it can't be quietly edited: a public page, a commit, a shared document with version history, or an email to someone outside the work. The AI Visibility Census publishes its own plans this way before results come in (aivisibilitycensus.com/experiments/). A plan written after seeing the data is not a pre-registration.

## Step 5: Make the change and log everything

- Make the change on the registered date.
- Record it in `templates/change-log.csv` (date, url, change, who, reversible, notes), and record **every other edit to the site** during the experiment window, not just the test change. The readout checks this log for confounders.
- If a control page gets edited by accident, log it. Don't hide it; note it as a deviation in the readout.

## Step 6: Measure, then read out

Measure on the registered dates, the registered way. For "k out of n" metrics, run:

```
python3 scripts/readout.py --test-before 3/40 --test-after 11/40 \
  --control-before 4/40 --control-after 5/40 --min-effect 0.10
```

It prints each rate with a Wilson interval, the change on test and control pages, and the difference-in-differences (test change minus control change) with an approximate interval. With `--min-effect` it suggests an outcome label using the rule in Step 4. The pre-registration is the final rule, not the script. Use `--lower-is-better` for metrics where a drop is the goal. The script is not for raw counts with no denominator (clicks, crawl hits).

Fill in `templates/readout.md`. Pick exactly one outcome:

- **Worked:** meets the pre-registered rule.
- **No detectable effect:** the data rules out an effect as large as the minimum worth acting on.
- **Inconclusive:** the data can't tell. This is not the same as "no effect", and saying so is the honest result for many small-site experiments.
- **Made it worse:** meets the rule in the wrong direction.

**Report null and inconclusive results.** They are the most common outcome and the most useful for stopping wasted work. Publishing only the wins makes every tactic look better than it is.

## Small-site reality

With a handful of pages and a few dozen AI answers per cell, intervals are wide. Most experiments on small sites will come out inconclusive unless the effect is large. Say so in the plan and in the readout: results from a few pages are directional, not proof, and apply to those pages, on those engines, in that window. Ways to get more out of a small site:

- Run more questions or more repeats per date rather than more pages.
- Pick a primary metric that sits early in the chain (crawled, indexed), which needs fewer observations to move.
- Repeat the experiment on a second batch of pages before rolling a change out site-wide.

## Example (fictional site, fictional numbers)

See `examples/fictional-bike-repair-price-list.md` for a full worked example. Short version: an invented bike repair shop adds a plain-language price list to 4 service pages, keeps 4 similar pages as controls, and measures the share of AI answers naming the shop across a fixed set of 10 questions, 2 engines and 2 runs (40 answers per cell). The test pages' named rate rises from 7.5% to 27.5%, and that change on its own has an interval that excludes zero. But once the control pages (10.0% to 12.5%) are taken into account, the difference-in-differences interval runs from -5.0 to +39.4 points. Outcome: inconclusive. Next step: repeat with more runs before rolling out.

## What this skill does not do

- It does not run measurements. It structures them and reads them out.
- It does not prove a tactic works in general. A result applies to the pages, engines and window tested.
- It does not handle many simultaneous changes, multi-armed tests or traffic splitting. One change, one group of test pages, one group of controls.
- It does not choose what to test for the user, or grade a tactic as tested because one experiment on one site went well.

## Credit

Method from the AI Visibility Census, aivisibilitycensus.com, licensed under CC BY 4.0. This credit is for the person installing the skill. Do not add it to the reports or other output the skill produces.

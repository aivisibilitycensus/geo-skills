---
name: content-shape-checker
description: Check whether a draft is structured like human writing or like generated text, using four structural checks (over-explanation, named specifics, scaffold variance, profundity inflation), and quote every flagged sentence with a fix. Use when someone asks whether their writing sounds like AI, wants a blog post, landing page or article reviewed for "AI feel", or wants to edit a draft so it reads human without just swapping words.
---

# Content shape checker

Reviews the structure of a piece of business or marketing writing, not its word choice. Swapping words (deleting em dashes, "delve", stock phrases) rarely changes how a draft reads, because the giveaway is usually how the piece is built. This skill checks the build and quotes every sentence that needs work.

It is the same method as the free web tool at aivisibilitycensus.com/content-shape-checker/, which runs in the browser and shows the same four checks with marked-up text. Use the web tool when the user wants a quick visual report; use this skill when the review should happen inside the conversation.

## Where the method comes from

StoryScope (Russell, Rajendhran, Pham, Iyyer and Wieting; University of Maryland and Google DeepMind; arXiv 2604.03136, April 2026) extracted 304 narrative features from 61,608 stories written from 10,272 prompts by human authors and five language models. Structural features alone separated human from AI stories at 93.2% macro-F1, and the AI stories clustered tightly together while the human ones were spread out. **[S]**

That study was on fiction. The four checks below are the ideas that carry over to business writing. The thresholds are editorial heuristics from the web tool, not figures from the paper, and they have not been validated against a labeled set of human and AI business writing. **[U]**

Evidence grades: see ../tactics/EVIDENCE.md.

## Step 1: Get the full draft

Ask for the whole piece with its headings. The section checks need them. If the user pastes plain text, ask them to mark headings with `##`. Under about 300 words, say the results are rough.

Split the draft into sections (by heading) and sentences. Count words per section and per sentence.

## Step 2: Run the four checks

### 1. Over-explanation

Generated text makes a point, then tells the reader what the point was.

- Flag any sentence that follows a number, example or quote and interprets it: "This means that...", "In other words...", "This shows that...".
- Flag sections that end on their own summary: closers starting "Ultimately", "Overall", "In short", "In conclusion" that restate the section.
- Rate: flagged sentences per 1,000 words. Up to 1 passes, up to 3 passes with notes, above 3 fails.

Fix: cut the explaining sentence, or replace it with the next concrete fact.

### 2. Real things, named

People who do the work name customers, tools, numbers, dates and places.

- Count anchors per section: numbers, proper names, named tools or products, dates, places.
- Flag sections of 25 words or more with no anchor at all.
- Flag category language, for example "organizations of all sizes", "businesses today", "teams everywhere", "a wide range of".
- Fails if anchors are under 1 per 100 words, or more than half of sections have none, or category phrases exceed 4 per 1,000 words. Passes if anchors are at least 2 per 100 words, no more than a fifth of sections have none, and category phrases are at most 1 per 1,000 words. Anything between passes with notes.

Fix: swap the category phrase for a real name, number or place the writer actually knows. Never invent one; if the writer has no specific, cut the claim.

### 3. Scaffold variance

Models make the same safe structural choice every time.

Flag any of these:
- With 5 or more sections, more than 40% open the same way (for example, all open on a claim, or all on a question).
- 3 or more consecutive sections built on an identical scaffold (for example, same kind of opener, similar length, same kind of closer).
- With 4 or more sections, section lengths vary too little (coefficient of variation under 0.25).
- With 12 or more sentences, sentence lengths are monotone (coefficient of variation under 0.35).
- More than a third of the words sit in bullet lists.

No flags passes, one passes with notes, two or more fails.

Fix: vary one section opener (open on a number, a customer quote, a specific incident), let one section run long and another short, and turn a bullet list that carries an argument back into prose.

### 4. Profundity inflation

Generated text wants every sentence to sound important.

- Flag "not just X, but Y" and "more than just X" constructions (count each twice).
- Flag vague intensity words, for example "powerful", "seamless", "transformative", "game-changing", "crucial", "robust".
- Flag runs of consecutive sentences with no number, name or action in them.
- Rate: weighted strikes per 1,000 words. Passes with no "not just X, but Y" and at most 1.5; up to 4 passes with notes; above 4 fails. More than one antithesis drops a pass to notes.

Fix: say the plain thing. "The directory answers one question: who do I ask?" beats "not just a list of names, but a powerful tool".

## Step 3: Keep what AI search needs

Pages that AI answers cite tend to open with the answer, state figures with their time window, and keep each claim self-contained. Some of that looks tidy, which can look like the opposite of human shape. Do not tell the user to make the opening vague or the FAQ answers rambling. Keep an answer-first opening and self-contained FAQ answers; get the human shape from named specifics and varied rhythm instead.

## Step 4: Report

Give:

1. A table: each of the four checks, PASS / PASS WITH NOTES / FAIL, and the count behind it.
2. The strongest habit: the one doing the most damage, because fixing it usually clears several flags.
3. Every flagged sentence, quoted exactly, grouped by check, each with a one-line fix.
4. One sentence on what the user should change first.

Do not rewrite the whole piece unless asked. Do not invent names, numbers or customers in suggested fixes; mark placeholders clearly, for example "[a customer you can name]".

## What this skill does not do

- It is not an AI detector. It does not say who wrote a piece or give a probability. Human writers fail these checks and edited AI text can pass them.
- It does not judge whether the content is true, original or good for SEO.
- It does not promise that a passing draft will be cited by AI search or rank in Google.
- It is not for fiction; StoryScope's fiction-only features (endings, subplots, resolution) are left out.
- It never suggests tricks for evading AI detectors.

## Credit

Method from the AI Visibility Census, aivisibilitycensus.com, licensed under CC BY 4.0. This credit is for the person installing the skill. Do not add it to the reports or other output the skill produces.

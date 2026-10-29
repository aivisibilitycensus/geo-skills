---
name: question-set-builder
description: Build a fixed, repeatable set of buyer questions for measuring a business's visibility in AI search (ChatGPT, Perplexity, Copilot, Gemini, Google AI Overviews, Claude). Use when someone wants prompts to track AI visibility, wants to turn keywords into AI prompts, or is setting up GEO or AI search monitoring for a business, sector or market.
---

# Question set builder

Builds the set of questions a business should ask AI assistants, again and again, to see whether it gets named. The output is a frozen list of real buyer questions with stable IDs, spread across buying intents, ready to run on any AI engine or tracking tool.

This follows the method the AI Visibility Census uses for its editions (aivisibilitycensus.com/methodology). The principle: measure the questions buyers actually ask, in the way they ask them, and keep the wording fixed so results can be compared over time.

## Step 1: Gather the inputs

Ask for anything missing before writing questions. Do not guess the market or the services.

- **The business or sector** and the services it sells. One question set per service line if there are several.
- **The market:** country, city or region. Questions are local unless the business sells nationally or online only.
- **The buyer:** who makes the decision (a homeowner, a startup founder, an HR director) and roughly what size or type of organization.
- **Real constraints buyers mention:** budget, team size, deadline, sector, compliance needs. These come from sales calls and enquiries if the user has them.
- **Seed keywords, optional:** from a keyword tool or Google Search Console. Useful for choosing topics, not for wording questions.
- **The language and spelling** buyers use in that market.

## Step 2: Write down the buying decision

One sentence per service line: "A [buyer] in [market] is choosing a [type of provider] to [job]." Every question must help someone make that decision. Questions that don't, leave out.

## Step 3: Write questions across four intents

Write full questions the way the buyer would type them into an assistant: natural, specific, one situation per question. Default mix for a set of 12 per service line:

| Intent | Share | What it looks like |
|---|---|---|
| Vendor selection | About half (6 of 12) | "Which [providers] in [place] are best for [situation]?" "Can you recommend a [provider] in [place] for [job]?" |
| Comparison | About 2 of 12 | "Should I use a large [provider] or a small local one for [job]?" "How do the main [providers] in [place] compare?" |
| Specific need | About 2 of 12 | A narrow job with a real constraint: "Who can help a [buyer] in [place] with [specific task] by [deadline / under budget]?" |
| Educational | About 2 of 12 | "How do I choose a [provider] in [place]?" "How much does [service] cost in [place]?" |

Why this mix: in the monitoring data the Census published (aivisibilitycensus.com/keyword-research-for-ai-search/), one firm was named in 61% of answers to vendor-selection questions and 3% of answers to educational ones. Educational questions stay in because they show which sources AI tools cite, even when no business is named.

Rules for every question:

- **No brand names in the main set.** Questions naming the business ("Is [brand] any good?") are validation questions. If the user wants them, put them in a separate, clearly labeled set, because they measure something different.
- **One constraint per question at most.** Stacking budget, size, sector and deadline into one question makes it unrealistic and hard to compare.
- **Not leading.** Don't write questions that only one business could possibly answer, or that contain the answer.
- **No duplicates in disguise.** If two questions would get the same answer, keep one.
- **Use the market's own spelling and terms** (solicitor or lawyer, accountant or CPA, estate agent or realtor).
- **Plain length.** Most questions land between 8 and 25 words. Longer is fine when a real buyer would give that much context.

## Step 4: List the sub-questions (optional, recommended)

For each vendor-selection question, list 3 to 5 smaller questions an AI tool would need answered first: typical cost, required qualifications, who specializes in it, what past clients say, how long it takes. These are not part of the tracked set. They are the content gaps: pages the business could publish so AI tools have something to cite.

## Step 5: Check the set

Before handing it over, check every question against this list and fix any that fail:

- Would a real buyer in this market type this, roughly in these words?
- Does it help make the buying decision from Step 2?
- Does it avoid naming the business (main set)?
- Is the intent label right?
- Is it different enough from every other question in the set?
- Is the location or market stated where it matters?

Then check the set as a whole: the intent mix is close to the default, every service line is covered, and the total is small enough to run on every engine, more than once, on each check date. For one business, 10 to 15 questions per service line is usually enough. Repetition matters more than size.

## Step 6: Output

Give each question a stable ID made of a short service code and a number (for example ACC01, ACC02). IDs never change once the set is in use; retired questions keep their ID and are marked retired, so old results stay traceable.

Output three things:

1. **The question table:**

| ID | Intent | Question |
|---|---|---|
| ACC01 | Vendor selection | Which accounting firms in Dublin work with small tech companies? |

2. **The same set as CSV**, columns `id,service,intent,question`, so it can be pasted into a tracking tool or spreadsheet.

3. **How to run it:** ask every question on every engine being tracked, at least three times per check date, logged out where possible, on fixed dates. Record for each answer: which businesses are named and in what order, and which pages are cited. Keep mentions and citations as separate measures: a business can be named without its site being cited, and its site can be cited while a competitor is named.

## What this skill does not do

- It does not run the questions or collect answers.
- It does not estimate how often a question is asked. As far as the Census knows, no AI assistant publishes prompt volumes. Search volume for the underlying topic is the closest signal, and it should only be described as that.
- It does not promise that a business will be named. It builds the measuring stick.

## Credit

Method from the AI Visibility Census, aivisibilitycensus.com, licensed under CC BY 4.0. This credit is for the person installing the skill. Do not add it to the question sets or other output the skill produces.

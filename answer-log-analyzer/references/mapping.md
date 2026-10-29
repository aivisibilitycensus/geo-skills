# Mapping an export to the canonical schema

Vendor exports change, and this skill has not verified any vendor's column names. Open your file, find the columns that hold each piece of information below, and rename or reshape them. Check the vendor's current documentation for what each column means.

## What to look for

| Canonical column | Look for a column that holds |
|---|---|
| `run_date` | The date (or timestamp) the answer was generated. Trim timestamps to `YYYY-MM-DD` |
| `engine` | The AI platform or model the answer came from |
| `question_id` | The prompt ID. If the export has prompt text only, add an ID column from your question set |
| `question` | The prompt text |
| `intent` | A tag, topic or group, if you labeled prompts by intent. Otherwise join it from your question set |
| `answer_text` | The full response text |
| `brands_named` | A list of brands or entities mentioned, if the tool extracts them |
| `cited_urls` | Source, citation or reference URLs |
| `run_number` | A run, sample or iteration number, if present |

## Common shapes

**One row per answer.** Rename the columns. Join multiple URLs into one `;`-separated cell if they are spread across columns.

**One row per citation** (the same answer repeated once per cited URL). Group rows by answer (date, engine, prompt, run), keep one copy of the answer text, and join the URLs with `;`. If you skip this, the script sees one answer as several, and every rate is wrong.

**One row per brand mention.** Group by answer and join the brand names, in order of position if the export has one, into `brands_named`.

**Wide files** (one column per brand with yes/no or a position). Build `brands_named` by listing the brands marked as mentioned, ordered by position if given.

**Summary exports** (already aggregated rates per prompt or per day). These cannot be analyzed here: the script needs one row per answer to count runs and compute intervals. Ask the vendor for an answer-level export.

## Manual logs

A spreadsheet with the canonical columns is enough. Paste the full answer text and the source links at the time of the run. Use the same question IDs as the question set.

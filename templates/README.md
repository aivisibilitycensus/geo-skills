# Templates

Free spreadsheet templates for SEO and AI search, built on the same method as the skills in this repo. Each one ships with fictional example rows so you can see the output before you add your own data.

| Template | What it does | Page |
|---|---|---|
| [seo-ai-visibility-report-template.xlsx](seo-ai-visibility-report-template.xlsx) | Monthly SEO report that puts Search Console numbers next to AI answer numbers, with a 95% Wilson interval on every AI rate and a verdict on whether a change is outside noise | [SEO report template](https://aivisibilitycensus.com/templates/seo-report-template/) |
| [geo-checklist.xlsx](geo-checklist.xlsx) ([Markdown](geo-checklist.md)) | 19 GEO checks, each graded by the evidence behind it, with a status column and progress by grade | [GEO checklist](https://aivisibilitycensus.com/templates/geo-checklist/) |
| [ai-overview-ctr-loss-finder.xlsx](ai-overview-ctr-loss-finder.xlsx) | Flags Search Console queries where CTR fell at a steady position and separates AI Overview losses from title and snippet problems | [AI Overview CTR loss finder](https://aivisibilitycensus.com/templates/ai-overview-ctr-loss/) |

The report template's example AI numbers are the totals from the [answer log analyzer's worked example](../answer-log-analyzer/examples/example-report.md), so the two can be checked against each other.

## Rebuild

```
python3 build_templates.py   # writes the three .xlsx files
python3 build_markdown.py    # writes geo-checklist.md from the same list
```

The checklist rows live in one list in `build_templates.py`, so the Excel file and the Markdown file cannot drift apart.

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credit: AI Visibility Census, aivisibilitycensus.com/templates/

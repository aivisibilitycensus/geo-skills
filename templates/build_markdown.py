"""Write geo-checklist.md from the same CHECKS list the Excel checklist uses, so the two never drift."""
from pathlib import Path

from build_templates import CHECKS, GRADE_TEXT

HERE = Path(__file__).parent
SECTIONS = [
    ("1. Measure first", lambda g: g == "Method"),
    ("2. Do next: documented or studied", lambda g: g in ("[P]", "[P] partial", "[S]")),
    ("3. Skip", lambda g: g == "[P] against"),
    ("4. Optional: untested, so test before you rely on it", lambda g: g == "[U]"),
    ("5. Never", lambda g: g == "Do not use"),
]


def esc(t):
    return t.replace("|", "\\|")


lines = [
    "# GEO checklist, graded by evidence",
    "",
    "A generative engine optimization (GEO) checklist where every item says how strong the evidence behind it is. "
    "Measure first, then do the documented and studied items, skip what platforms say is not needed, and treat untested items as experiments.",
    "",
    "Excel version with a status column and a progress tab: [aivisibilitycensus.com/templates/geo-checklist/](https://aivisibilitycensus.com/templates/geo-checklist/). "
    "Grades come from [tactics/EVIDENCE.md](../tactics/EVIDENCE.md) (last checked 29 October 2026) and change only when the evidence does.",
    "",
    "| Grade | Meaning |",
    "|---|---|",
]
lines += [f"| **{g}** | {m} |" for g, m in GRADE_TEXT]
lines += ["", "A higher grade is not a promise. [P] tells you what a platform says it does, not what happens on your site. "
          "No item is graded [T] yet: the Census experiments in the last column have not reported results.", ""]
for title, pred in SECTIONS:
    lines += [f"## {title}", "", "| Check | How to check | Grade | What the evidence says | Census test |", "|---|---|---|---|---|"]
    for area, check, how, grade, ev, src, url, test in CHECKS:
        if pred(grade):
            source = f" ([{src}]({url}))" if url else ""
            lines.append(f"| {esc(check)} | {esc(how)} | **{grade}** | {esc(ev)}{source} | {esc(test)} |")
    lines.append("")
lines += ["## License", "", "[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credit: AI Visibility Census, aivisibilitycensus.com/templates/geo-checklist/", ""]
(HERE / "geo-checklist.md").write_text("\n".join(lines))
print("written")

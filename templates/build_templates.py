"""Build the three AI Visibility Census spreadsheet templates.

Run: python3 build_templates.py  (writes the .xlsx files next to this script)
Then recalculate (LibreOffice) so the files carry cached values.

All example rows are fictional. The AI answer counts in the report template are the
aggregates of the answer log analyzer's worked example (answer-log-analyzer/examples),
so the template and the analyzer give the same numbers.
"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

HERE = Path(__file__).parent
INK = "172321"
LIME = "DCFA57"
INPUT = "F3FBD0"
RULE = "D9D6CB"
MUTED = "4A5654"
F = "Arial"

HEAD_FONT = Font(name=F, bold=True, color="FFFFFF", size=10)
HEAD_FILL = PatternFill("solid", fgColor=INK)
IN_FILL = PatternFill("solid", fgColor=INPUT)
BODY = Font(name=F, size=10)
BOLD = Font(name=F, size=10, bold=True)
TITLE = Font(name=F, size=16, bold=True, color=INK)
SUB = Font(name=F, size=10, color=MUTED, italic=True)
LINK = Font(name=F, size=10, color="1155CC", underline="single")
THIN = Border(bottom=Side(style="thin", color=RULE))
WRAP = Alignment(wrap_text=True, vertical="top")

CREDIT = ("Free template from the AI Visibility Census, licensed CC BY 4.0. "
          "Use and adapt it, including for client work, with credit and a link: "
          "aivisibilitycensus.com/templates/")


def header(ws, row, labels, widths=None):
    for i, label in enumerate(labels, 1):
        c = ws.cell(row=row, column=i, value=label)
        c.font = HEAD_FONT
        c.fill = HEAD_FILL
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[row].height = 32
    if widths:
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = ws.cell(row=row + 1, column=1)


def style_body(ws, r1, r2, c1, c2, inputs=()):
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = BODY
            cell.border = THIN
            cell.alignment = WRAP
            if c in inputs:
                cell.fill = IN_FILL


def start_sheet(wb, title, intro, steps, notes):
    ws = wb.active
    ws.title = "Start here"
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 110
    ws.sheet_view.showGridLines = False
    ws["B2"] = title
    ws["B2"].font = TITLE
    ws["B3"] = intro
    ws["B3"].font = BODY
    ws["B3"].alignment = WRAP
    ws.row_dimensions[3].height = 48
    r = 5
    ws.cell(row=r, column=2, value="How to use it").font = BOLD
    for i, s in enumerate(steps, 1):
        r += 1
        c = ws.cell(row=r, column=2, value=f"{i}. {s}")
        c.font = BODY
        c.alignment = WRAP
        ws.row_dimensions[r].height = 30 if len(s) > 110 else 16
    r += 2
    c = ws.cell(row=r, column=2, value="Cells shaded like this are the ones you fill in. Other cells hold formulas or fixed text.")
    c.fill = IN_FILL
    c.font = BODY
    r += 2
    ws.cell(row=r, column=2, value="Good to know").font = BOLD
    for n in notes:
        r += 1
        c = ws.cell(row=r, column=2, value=n)
        c.font = BODY
        c.alignment = WRAP
        ws.row_dimensions[r].height = 30 if len(n) > 110 else 16
    r += 2
    c = ws.cell(row=r, column=2, value=CREDIT)
    c.font = SUB
    c.alignment = WRAP
    ws.row_dimensions[r].height = 30
    return ws


def wilson(k, n, side):
    """Excel formula for one end of a 95% Wilson interval. k and n are cell refs."""
    p = f"({k}/{n})"
    center = f"(({p}+1.96^2/(2*{n}))/(1+1.96^2/{n}))"
    half = f"(1.96*SQRT({p}*(1-{p})/{n}+1.96^2/(4*{n}^2))/(1+1.96^2/{n}))"
    if side == "low":
        return f'=IF(N({n})=0,"",MAX(0,{center}-{half}))'
    return f'=IF(N({n})=0,"",MIN(1,{center}+{half}))'


# ---------------------------------------------------------------- 1. report
def build_report():
    wb = Workbook()
    start_sheet(
        wb,
        "SEO and AI visibility report template",
        "A monthly report that puts Google Search Console numbers and AI answer numbers side by side, "
        "and says whether a change in how often AI answers name your brand is a real change or normal "
        "run-to-run noise. Every rate comes with the range the data supports.",
        [
            "Google tab: paste one row per month from Search Console's Performance report (clicks, impressions, average position). CTR and changes calculate themselves.",
            "Pages tab: paste your top pages for this month and last month. The change columns calculate themselves.",
            "AI answers tab: one row per period and engine: how many answers you logged, how many named your brand, how many cited your site. "
            "If you use our free answer log analyzer, its cells CSV gives you these counts.",
            "Report tab: type the two periods you want to compare in the shaded cells. Every rate gets a 95% interval and a verdict.",
            "Delete the example rows (they are fictional) before you add your own.",
        ],
        [
            "The verdict says \"Change outside noise\" only when the two-proportion test gives p < 0.05 AND the two 95% intervals do not overlap. "
            "That is a strict bar on purpose: repeated answers to the same question are not independent, so the test alone overstates certainty.",
            "Under 30 answers in either period, the row says \"Too few answers to compare\". At 30 answers a 50% rate still runs from about 33% to 67%.",
            "Ask each question at least 3 times per engine per check date. With 1 or 2 runs, the only possible rates are 0%, 50% or 100%.",
            "Google says AI Overviews and AI Mode traffic is included in the Web search type of the Performance report, and does not split it out. "
            "So the Google tab cannot show AI Overview clicks on their own.",
            "The example AI numbers are the aggregates of the answer log analyzer's worked example (fictional brand Liffey Ledger Accountants), "
            "so you can check this sheet against the analyzer's published report.",
            "Method: Wilson score interval; pooled two-proportion z-test. Full method: github.com/aivisibilitycensus/geo-skills/blob/main/answer-log-analyzer/references/methods.md",
        ],
    )

    # Google monthly
    g = wb.create_sheet("Google")
    header(g, 1, ["Month", "Clicks", "Impressions", "Average position", "CTR",
                  "Clicks vs previous month", "Impressions vs previous month"],
           [12, 12, 14, 16, 10, 22, 26])
    months = [("2026-05", 1840, 61200, 14.2), ("2026-06", 1795, 64800, 13.9),
              ("2026-07", 1702, 66900, 13.6), ("2026-08", 1655, 71300, 13.1),
              ("2026-09", 1610, 74100, 12.8), ("2026-10", 1588, 77800, 12.5)]
    for i, (m, cl, im, pos) in enumerate(months, 2):
        g.cell(row=i, column=1, value=m)
        g.cell(row=i, column=2, value=cl)
        g.cell(row=i, column=3, value=im)
        g.cell(row=i, column=4, value=pos)
        g.cell(row=i, column=5, value=f'=IF(N(C{i})=0,"",B{i}/C{i})')
        if i == 2:
            g.cell(row=i, column=6, value="")
            g.cell(row=i, column=7, value="")
        else:
            g.cell(row=i, column=6, value=f'=IF(OR(N(B{i})=0,N(B{i-1})=0),"",B{i}/B{i-1}-1)')
            g.cell(row=i, column=7, value=f'=IF(OR(N(C{i})=0,N(C{i-1})=0),"",C{i}/C{i-1}-1)')
    # extra empty formula rows for users
    for i in range(8, 26):
        g.cell(row=i, column=5, value=f'=IF(N(C{i})=0,"",B{i}/C{i})')
        g.cell(row=i, column=6, value=f'=IF(OR(N(B{i})=0,N(B{i-1})=0),"",B{i}/B{i-1}-1)')
        g.cell(row=i, column=7, value=f'=IF(OR(N(C{i})=0,N(C{i-1})=0),"",C{i}/C{i-1}-1)')
    style_body(g, 2, 25, 1, 7, inputs=(1, 2, 3, 4))
    for i in range(2, 26):
        g.cell(row=i, column=1).number_format = "@"
        g.cell(row=i, column=2).number_format = "#,##0"
        g.cell(row=i, column=3).number_format = "#,##0"
        g.cell(row=i, column=4).number_format = "0.0"
        for c in (5, 6, 7):
            g.cell(row=i, column=c).number_format = "0.0%"
    g["A1"].comment = Comment("Month as YYYY-MM text, oldest first. Example rows are fictional.", "Census")

    # Pages
    p = wb.create_sheet("Pages")
    header(p, 1, ["Page", "Clicks this month", "Clicks last month", "Click change",
                  "Impressions this month", "Impressions last month", "CTR this month", "CTR last month"],
           [44, 12, 12, 12, 14, 14, 12, 12])
    pages = [("/pricing/", 412, 455, 9800, 9400), ("/blog/fixed-fee-accounts/", 288, 301, 21400, 18900),
             ("/services/tech-startups/", 197, 186, 7300, 7100), ("/", 165, 170, 4100, 4000),
             ("/blog/vat-registration-ireland/", 121, 168, 16800, 14200)]
    for i, (u, c1, c0, i1, i0) in enumerate(pages, 2):
        p.cell(row=i, column=1, value=u)
        p.cell(row=i, column=2, value=c1)
        p.cell(row=i, column=3, value=c0)
        p.cell(row=i, column=5, value=i1)
        p.cell(row=i, column=6, value=i0)
    for i in range(2, 32):
        p.cell(row=i, column=4, value=f'=IF(OR(B{i}="",C{i}=""),"",B{i}-C{i})')
        p.cell(row=i, column=7, value=f'=IF(N(E{i})=0,"",B{i}/E{i})')
        p.cell(row=i, column=8, value=f'=IF(N(F{i})=0,"",C{i}/F{i})')
        for c in (2, 3, 4, 5, 6):
            p.cell(row=i, column=c).number_format = "#,##0;-#,##0;0"
        p.cell(row=i, column=7).number_format = "0.0%"
        p.cell(row=i, column=8).number_format = "0.0%"
    style_body(p, 2, 31, 1, 8, inputs=(1, 2, 3, 5, 6))

    # AI answers
    a = wb.create_sheet("AI answers")
    header(a, 1, ["Period", "Engine", "Answers logged", "Answers naming you", "Answers citing your site",
                  "Named rate", "Named low (95%)", "Named high (95%)",
                  "Cited rate", "Cited low (95%)", "Cited high (95%)", "Note"],
           [10, 14, 12, 14, 14, 11, 12, 12, 11, 12, 12, 30])
    rows = [("2026-09", "chatgpt", 36, 10, 14), ("2026-09", "copilot", 36, 5, 12),
            ("2026-09", "perplexity", 36, 11, 10), ("2026-10", "chatgpt", 36, 12, 14),
            ("2026-10", "copilot", 36, 7, 9), ("2026-10", "perplexity", 36, 17, 13)]
    for i, (per, eng, n, k, c) in enumerate(rows, 2):
        a.cell(row=i, column=1, value=per)
        a.cell(row=i, column=2, value=eng)
        a.cell(row=i, column=3, value=n)
        a.cell(row=i, column=4, value=k)
        a.cell(row=i, column=5, value=c)
    last = 61
    for i in range(2, last + 1):
        a.cell(row=i, column=6, value=f'=IF(N(C{i})=0,"",D{i}/C{i})')
        a.cell(row=i, column=7, value=wilson(f"D{i}", f"C{i}", "low"))
        a.cell(row=i, column=8, value=wilson(f"D{i}", f"C{i}", "high"))
        a.cell(row=i, column=9, value=f'=IF(N(C{i})=0,"",E{i}/C{i})')
        a.cell(row=i, column=10, value=wilson(f"E{i}", f"C{i}", "low"))
        a.cell(row=i, column=11, value=wilson(f"E{i}", f"C{i}", "high"))
        a.cell(row=i, column=12, value=f'=IF(N(C{i})=0,"",IF(C{i}<30,"Under 30 answers: wide range",""))')
        a.cell(row=i, column=1).number_format = "@"
        for c in (6, 7, 8, 9, 10, 11):
            a.cell(row=i, column=c).number_format = "0%"
    style_body(a, 2, last, 1, 12, inputs=(1, 2, 3, 4, 5))
    a["A1"].comment = Comment("Period label, e.g. 2026-10. It must match the period you type on the Report tab.", "Census")
    a["B1"].comment = Comment("Engine name, written the same way every period (e.g. chatgpt, gemini, ai_mode, copilot).", "Census")
    dv = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="0", allow_blank=True)
    a.add_data_validation(dv)
    dv.add(f"C2:E{last}")

    # Report
    r = wb.create_sheet("Report")
    r.sheet_view.showGridLines = False
    r.column_dimensions["A"].width = 16
    for col in "BCDEFGHIJ":
        r.column_dimensions[col].width = 15
    r.column_dimensions["K"].width = 30
    r["A1"] = "SEO and AI visibility report"
    r["A1"].font = TITLE
    r["A3"] = "Compare period A"
    r["B3"] = "2026-09"
    r["A4"] = "with period B"
    r["B4"] = "2026-10"
    for ref in ("A3", "A4"):
        r[ref].font = BOLD
    for ref in ("B3", "B4"):
        r[ref].fill = IN_FILL
        r[ref].font = BOLD
        r[ref].number_format = "@"
    r["C3"] = "Type periods exactly as on the AI answers tab."
    r["C3"].font = SUB

    r["A6"] = "Google Search Console, latest month"
    r["A6"].font = BOLD
    kpis = [("Month", "=INDEX(Google!A2:A25,COUNTA(Google!A2:A25))", "@"),
            ("Clicks", "=INDEX(Google!B2:B25,COUNTA(Google!A2:A25))", "#,##0"),
            ("Clicks vs previous month", "=INDEX(Google!F2:F25,COUNTA(Google!A2:A25))", "0.0%"),
            ("Impressions", "=INDEX(Google!C2:C25,COUNTA(Google!A2:A25))", "#,##0"),
            ("Impressions vs previous month", "=INDEX(Google!G2:G25,COUNTA(Google!A2:A25))", "0.0%"),
            ("CTR", "=INDEX(Google!E2:E25,COUNTA(Google!A2:A25))", "0.0%"),
            ("Average position", "=INDEX(Google!D2:D25,COUNTA(Google!A2:A25))", "0.0")]
    for j, (lab, f, fmt) in enumerate(kpis, 7):
        r.cell(row=j, column=1, value=lab).font = BODY
        c = r.cell(row=j, column=3, value=f)
        c.font = BOLD
        c.number_format = fmt
        r.merge_cells(start_row=j, start_column=1, end_row=j, end_column=2)

    def table_header(row):
        for i, lab in enumerate(cols, 1):
            c = r.cell(row=row, column=i, value=lab)
            c.font = HEAD_FONT
            c.fill = HEAD_FILL
            c.alignment = Alignment(wrap_text=True, vertical="center")
        r.row_dimensions[row].height = 30

    cols = ["Engine", "Answers A", "Named A", "Range A", "Answers B", "Named B", "Range B",
            "Change", "p-value", "Ranges overlap?", "Verdict"]
    engines = ["All engines", "chatgpt", "copilot", "perplexity", "", "", ""]

    def block(start, metric_col):
        """metric_col: D for named, E for cited on the AI answers tab."""
        for j, eng in enumerate(engines):
            row = start + j
            r.cell(row=row, column=1, value=eng if eng else None)
            cond = "" if eng == "All engines" else f",'AI answers'!$B$2:$B${last},$A{row}"
            for per, nc, kc in (("$B$3", "B", "C"), ("$B$4", "E", "F")):
                r[f"{nc}{row}"] = (f'=IF($A{row}="","",SUMIFS(\'AI answers\'!$C$2:$C${last},'
                                   f"'AI answers'!$A$2:$A${last},{per}{cond}))")
                r[f"{kc}{row}"] = (f'=IF($A{row}="","",SUMIFS(\'AI answers\'!${metric_col}$2:${metric_col}${last},'
                                   f"'AI answers'!$A$2:$A${last},{per}{cond}))")
            n1, k1, n2, k2 = f"B{row}", f"C{row}", f"E{row}", f"F{row}"
            lo1, hi1 = wilson(k1, n1, "low")[1:], wilson(k1, n1, "high")[1:]
            lo2, hi2 = wilson(k2, n2, "low")[1:], wilson(k2, n2, "high")[1:]
            r[f"D{row}"] = (f'=IF(N({n1})=0,"",TEXT({k1}/{n1},"0%")&" ("&TEXT({lo1},"0%")&"-"&TEXT({hi1},"0%")&")")')
            r[f"G{row}"] = (f'=IF(N({n2})=0,"",TEXT({k2}/{n2},"0%")&" ("&TEXT({lo2},"0%")&"-"&TEXT({hi2},"0%")&")")')
            r[f"H{row}"] = f'=IF(OR(N({n1})=0,N({n2})=0),"",ROUND(({k2}/{n2}-{k1}/{n1})*100,1))'
            r[f"H{row}"].number_format = '+0.0" pts";-0.0" pts";0.0" pts"'
            pooled = f"(({k1}+{k2})/({n1}+{n2}))"
            se = f"SQRT({pooled}*(1-{pooled})*(1/{n1}+1/{n2}))"
            r[f"I{row}"] = (f'=IF(OR(N({n1})=0,N({n2})=0),"",IF({se}=0,1,'
                            f"2*(1-NORMSDIST(ABS(({k2}/{n2}-{k1}/{n1})/{se})))))")
            r[f"I{row}"].number_format = "0.000"
            r[f"J{row}"] = (f'=IF(OR(N({n1})=0,N({n2})=0),"",IF(OR({lo2}>{hi1},{hi2}<{lo1}),"No","Yes"))')
            r[f"K{row}"] = (f'=IF(OR(N({n1})=0,N({n2})=0),"",IF(OR({n1}<30,{n2}<30),"Too few answers to compare",'
                            f'IF(AND(I{row}<0.05,J{row}="No"),"Change outside noise","Within noise")))')
            for c in range(1, 12):
                cell = r.cell(row=row, column=c)
                cell.font = BOLD if (c == 1 and eng == "All engines") else BODY
                cell.border = THIN
            if eng != "All engines":
                r.cell(row=row, column=1).fill = IN_FILL
        rng = f"K{start}:K{start + len(engines) - 1}"
        r.conditional_formatting.add(rng, FormulaRule(formula=[f'K{start}="Change outside noise"'],
                                                      fill=PatternFill("solid", fgColor=LIME), font=Font(name=F, bold=True)))
        return start + len(engines)

    r.cell(row=15, column=1, value="AI answers that name your brand: real change or noise?").font = BOLD
    table_header(16)
    end1 = block(17, "D")
    t2 = end1 + 2
    r.cell(row=t2 - 1, column=1, value="AI answers that cite your site: real change or noise?").font = BOLD
    table_header(t2)
    block(t2 + 1, "E")
    for row in (16, t2):
        r.cell(row=row, column=3).value = "Count A"
        r.cell(row=row, column=6).value = "Count B"
    note_row = t2 + 9
    r.cell(row=note_row, column=1, value=(
        "Engine names in the shaded cells must match the AI answers tab. \"Change outside noise\" needs p < 0.05 "
        "and ranges that do not overlap. Ranges are 95% Wilson intervals. Rates on the same engine are not combined "
        "across naming and citing: they measure different things.")).font = SUB
    r.merge_cells(start_row=note_row, start_column=1, end_row=note_row + 1, end_column=11)
    r.cell(row=note_row, column=1).alignment = WRAP
    r.cell(row=note_row + 3, column=1, value=CREDIT).font = SUB
    r.merge_cells(start_row=note_row + 3, start_column=1, end_row=note_row + 3, end_column=11)

    wb.move_sheet("Report", offset=-3)
    wb.save(HERE / "seo-ai-visibility-report-template.xlsx")


# ---------------------------------------------------------------- 2. checklist
CHECKS = [
    # area, check, how to check, grade, evidence, source label, source url, census test
    ("Method", "Write a fixed set of buyer questions before you change anything",
     "List the questions buyers ask, spread across vendor selection, comparison, specific need and educational intents. Keep the wording fixed so months compare.",
     "Method", "This is how you measure, not a ranking tactic. Without a fixed question set, a change in results cannot be told apart from a change in the questions.",
     "Question set builder (free skill)", "https://github.com/aivisibilitycensus/geo-skills/tree/main/question-set-builder", "Used for Census Edition 1 and the Census100"),
    ("Method", "Ask each question at least 3 times per engine per check date",
     "Log every answer with the date, engine, run number, answer text and cited links.",
     "Method", "AI answers change from run to run. With 1 or 2 runs the only possible rates are 0%, 50% or 100%.",
     "Answer log analyzer methods", "https://github.com/aivisibilitycensus/geo-skills/blob/main/answer-log-analyzer/references/methods.md", "Edition 1 plan: 3 runs per date on ChatGPT, Gemini and AI Mode"),
    ("Method", "Change one thing at a time, with a control page and a written prediction",
     "Note the date of each change and what you expect before results come in.",
     "Method", "Engine updates land between check dates too, so a change you cannot isolate tells you little.",
     "GEO experiment kit (free skill)", "https://github.com/aivisibilitycensus/geo-skills/tree/main/geo-experiment-kit", "Every test on our experiments page"),
    ("Crawl and index", "Pages you want in Google's AI features are indexed and eligible for a snippet",
     "URL Inspection in Search Console shows the page is on Google. No nosnippet on the page.",
     "[P]", "Google: pages need to be indexed and eligible to be shown with a snippet; there are \"no additional requirements\".",
     "Google, AI features and your website", "https://developers.google.com/search/docs/appearance/ai-features", "Not tested"),
    ("Crawl and index", "OAI-SearchBot is allowed in robots.txt",
     "Open yoursite.com/robots.txt and check nothing disallows OAI-SearchBot (or every bot with *).",
     "[P]", "OpenAI: sites opted out of OAI-SearchBot \"will not be shown in ChatGPT search answers\". GPTBot is the separate training crawler.",
     "OpenAI, bots", "https://developers.openai.com/api/docs/bots", "Not tested"),
    ("Crawl and index", "Important content is in the HTML the server sends, not only added by JavaScript",
     "View the page source (not the inspector) and search for a key sentence.",
     "[S]", "Vercel and MERJ (December 2024): \"none of the major AI crawlers currently render JavaScript\"; exceptions were Gemini (via Googlebot) and Applebot. Data from Vercel's network, checked on two other sites, 2024.",
     "Vercel, The rise of the AI crawler", "https://vercel.com/blog/the-rise-of-the-ai-crawler", "Not tested"),
    ("Crawl and index", "IndexNow sends new and changed URLs to Bing",
     "Check your CMS or plugin sends IndexNow pings and gets a 200 or 202 back.",
     "[P] partial", "IndexNow lists Bing among participating engines and says \"Submitting a URL does not guarantee immediate indexing\". The speed claim is not documented.",
     "IndexNow FAQ", "https://www.indexnow.org/faq", "Used within CT-001"),
    ("Markup", "Structured data says only what the visible page says",
     "Compare schema FAQ text, prices, ratings, phone numbers and dates against the visible page.",
     "[P]", "Google lists making sure structured data matches the visible text among practices for AI features.",
     "Google, AI features and your website", "https://developers.google.com/search/docs/appearance/ai-features", "Not tested"),
    ("Markup", "Do not add special AI files or markup expecting it to get you into Google's AI features",
     "Nothing to add. If a vendor sells you an AI file for Google, ask for the source.",
     "[P] against", "Google: \"You don't need to create new machine readable files, AI text files, or markup to appear in these features\".",
     "Google, AI features and your website", "https://developers.google.com/search/docs/appearance/ai-features", "Not tested"),
    ("Markup", "FAQ structured data",
     "Optional. Keep it only if it matches visible text.",
     "[U]", "Google stopped showing FAQ rich results from 7 May 2026, so there is no Google display benefit. No evidence found that it helps AI answers.",
     "Google Search Central updates", "https://developers.google.com/search/updates", "In place within CT-001; not isolated"),
    ("AI files", "llms.txt",
     "Optional. Cheap to add, but do not expect results from it alone.",
     "[U]", "A proposal by Jeremy Howard, first published September 2024. Google says AI text files are not needed for its AI features. Whether AI crawlers fetch it is what the Census is logging.",
     "llmstxt.org", "https://llmstxt.org/", "LL-001 running; RT-001 from 1 Dec 2026"),
    ("AI files", "Markdown versions of pages",
     "Optional.",
     "[U]", "No platform documentation or study found.",
     "", "", "Logged within CT-001"),
    ("AI files", "Content Signals line in robots.txt",
     "Optional. Know that no AI company has been found committing to honor it.",
     "[U]", "A robots.txt extension introduced by Cloudflare in September 2025. No AI company found committing to honor it.",
     "Cloudflare, Content Signals Policy", "https://blog.cloudflare.com/content-signals-policy/", "CS-001 running"),
    ("Content", "Add statistics, quotations and citations to key pages",
     "Each key page carries at least one number with its source, and names its sources.",
     "[S]", "Aggarwal et al.: \"GEO can boost visibility by up to 40% in generative engine responses\", in a benchmark setting. Lab results, not a live-engine guarantee.",
     "arXiv 2311.09735", "https://arxiv.org/abs/2311.09735", "Not tested"),
    ("Content", "Question-style headings",
     "Optional.",
     "[U]", "Claimed to get quoted word for word. Not checked here.",
     "", "", "Not tested"),
    ("Authority", "Rank in Google's top 10 for the question",
     "Check your ranking for the main query behind each question.",
     "[U]", "Claimed to be required for AI Overview citations. Claims vary between vendor studies; not checked here.",
     "", "", "Not tested"),
    ("Authority", "Earn backlinks to the pages you want cited",
     "Referring domains to each key page, from Ahrefs, Semrush or Bing Webmaster Tools.",
     "[U]", "Claimed that a page with no backlinks will not be cited. Not checked here.",
     "", "", "Not tested (BL-001 measures links, not citations)"),
    ("Distribution", "Share new pages on LinkedIn to speed up the first Bing crawl",
     "Optional.",
     "[U]", "Claimed to speed up the first Bing and Copilot crawl. Not checked here.",
     "", "", "Not tested"),
    ("Never", "Hidden instructions aimed at AI assistants",
     "Check \"Summarize with AI\" buttons and share links on your site: none should carry a prompt telling the assistant to remember or favor your brand.",
     "Do not use", "Microsoft describes companies hiding instructions that tell an assistant to remember and favor their brand, and calls it \"AI Recommendation Poisoning\".",
     "Microsoft Security, 10 February 2026", "https://www.microsoft.com/en-us/security/blog/2026/02/10/ai-recommendation-poisoning/", "Never"),
]

GRADE_TEXT = [
    ("[T]", "Tested by the AI Visibility Census, with the result published"),
    ("[S]", "Published study with a stated method"),
    ("[P]", "Platform documentation: the search engine or AI company says so in its own docs"),
    ("[V]", "Vendor or practitioner claim, not independently checked"),
    ("[U]", "Untested, or no evidence found either way"),
    ("Method", "How to measure, not a ranking tactic"),
    ("Do not use", "Harmful or deceptive"),
]


def build_checklist():
    wb = Workbook()
    start_sheet(
        wb,
        "GEO checklist, graded by evidence",
        "A generative engine optimization checklist where every item says how strong the evidence behind it is: "
        "platform documentation, a published study, a vendor claim, or nothing yet. Work through the method items "
        "first, then the items marked Do next. Treat [U] items as optional experiments, not requirements.",
        [
            "Checklist tab: set Status for each row (Done, Not done, Not applicable). The Priority column fills itself from the grade.",
            "Progress tab: shows how many items are done, by grade.",
            "Before you change anything, write your question set and log a baseline (the three Method rows). Otherwise you cannot tell what worked.",
        ],
        [
            "Grades come from the geo-skills evidence file, last checked 29 October 2026. They move only when the evidence does. "
            "Latest version: github.com/aivisibilitycensus/geo-skills/blob/main/tactics/EVIDENCE.md",
            "A higher grade is not a promise. [P] tells you what a platform says it does, not what happens on your site. "
            "[S] results come from the study's setup, which may not match yours.",
            "No item is graded [T] yet: the Census experiments listed in the last column have not reported results. "
            "Results go on aivisibilitycensus.com/experiments/ whatever they show.",
        ],
    )
    ws = wb.create_sheet("Checklist")
    cols = ["#", "Area", "Check", "How to check", "Grade", "What the evidence says", "Source", "Census test",
            "Status", "Priority", "Your notes"]
    header(ws, 1, cols, [5, 14, 36, 40, 11, 52, 30, 20, 13, 18, 30])
    for i, (area, check, how, grade, ev, src, url, test) in enumerate(CHECKS, 2):
        ws.cell(row=i, column=1, value=i - 1)
        ws.cell(row=i, column=2, value=area)
        ws.cell(row=i, column=3, value=check)
        ws.cell(row=i, column=4, value=how)
        ws.cell(row=i, column=5, value=grade)
        ws.cell(row=i, column=6, value=ev)
        c = ws.cell(row=i, column=7, value=src or "None found")
        if url:
            c.hyperlink = url
        ws.cell(row=i, column=8, value=test)
        ws.cell(row=i, column=9, value="Not done")
        ws.cell(row=i, column=10, value=(
            f'=IF(I{i}="Not applicable","",IF(E{i}="Do not use",IF(I{i}="Done","Checked","Remove if found"),IF(I{i}="Done","Done",'
            f'IF(E{i}="Method","Do first",IF(E{i}="[P] against","Skip",'
            f'IF(OR(LEFT(E{i},3)="[P]",LEFT(E{i},3)="[S]",LEFT(E{i},3)="[T]"),"Do next","Optional: test it"))))))'))
    n = len(CHECKS) + 1
    style_body(ws, 2, n, 1, 11, inputs=(9, 11))
    for i in range(2, n + 1):
        if ws.cell(row=i, column=7).hyperlink:
            ws.cell(row=i, column=7).font = LINK
        ws.cell(row=i, column=5).font = BOLD
    dv = DataValidation(type="list", formula1='"Done,Not done,Not applicable"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"I2:I{n}")
    ws.conditional_formatting.add(f"J2:J{n}", FormulaRule(formula=['J2="Do first"'],
                                  fill=PatternFill("solid", fgColor=LIME), font=Font(name=F, bold=True)))
    ws.auto_filter.ref = f"A1:K{n}"

    pr = wb.create_sheet("Progress")
    pr.sheet_view.showGridLines = False
    header(pr, 1, ["Grade", "Meaning", "Items", "Done", "Not applicable"], [12, 70, 8, 8, 14])
    for j, (g, meaning) in enumerate(GRADE_TEXT, 2):
        pr.cell(row=j, column=1, value=g)
        pr.cell(row=j, column=2, value=meaning)
        crit = f'"{g}*"' if g.startswith("[") else f'"{g}"'
        pr.cell(row=j, column=3, value=f"=COUNTIF(Checklist!$E$2:$E${n},{crit})")
        pr.cell(row=j, column=4, value=f'=COUNTIFS(Checklist!$E$2:$E${n},{crit},Checklist!$I$2:$I${n},"Done")')
        pr.cell(row=j, column=5, value=f'=COUNTIFS(Checklist!$E$2:$E${n},{crit},Checklist!$I$2:$I${n},"Not applicable")')
    tot = len(GRADE_TEXT) + 2
    pr.cell(row=tot, column=1, value="All")
    pr.cell(row=tot, column=3, value=f"=COUNTA(Checklist!$C$2:$C${n})")
    pr.cell(row=tot, column=4, value=f'=COUNTIF(Checklist!$I$2:$I${n},"Done")')
    pr.cell(row=tot, column=5, value=f'=COUNTIF(Checklist!$I$2:$I${n},"Not applicable")')
    style_body(pr, 2, tot, 1, 5)
    for c in range(1, 6):
        pr.cell(row=tot, column=c).font = BOLD
    pr.cell(row=tot + 2, column=1, value="[P] matches [P], [P] partial and [P] against.").font = SUB
    pr.cell(row=tot + 4, column=1, value=CREDIT).font = SUB
    wb.save(HERE / "geo-checklist.xlsx")


# ---------------------------------------------------------------- 3. CTR loss
QUERIES = [
    # query, clicks before, clicks after, impressions before, impressions after, pos before, pos after, AIO
    ("what is a fixed fee accountant", 310, 142, 8200, 9100, 2.1, 2.0, "Yes"),
    ("vat registration threshold ireland", 260, 118, 9600, 10400, 3.0, 2.8, "Yes"),
    ("accountant for startups dublin", 145, 151, 2100, 2250, 3.4, 3.2, ""),
    ("how to file a ct1 return", 120, 64, 5400, 5900, 4.1, 4.3, "No"),
    ("small business accountant near me", 98, 92, 1900, 1850, 5.2, 5.5, ""),
    ("sole trader vs limited company ireland", 88, 41, 4700, 5300, 4.9, 4.6, "Yes"),
    ("liffey ledger accountants", 210, 214, 640, 655, 1.0, 1.0, ""),
    ("payroll services dublin", 54, 22, 2300, 2400, 7.8, 9.9, ""),
    ("r&d tax credit ireland", 47, 45, 3100, 3300, 8.2, 8.0, ""),
    ("bookkeeping cost per month", 38, 16, 2900, 3400, 6.0, 6.3, "Not checked"),
    ("online accountant ireland", 31, 30, 1200, 1180, 6.9, 7.1, ""),
    ("what does an accountant do", 9, 4, 3800, 4200, 14.0, 13.5, ""),
]


def build_ctr():
    wb = Workbook()
    start_sheet(
        wb,
        "AI Overview CTR loss finder",
        "Finds the queries where your click-through rate fell while your ranking held, then separates the ones "
        "where Google showed an AI answer from the ones where your title or snippet is the more likely problem. "
        "A low CTR is not always a title problem when an AI answer sits above your result.",
        [
            "In Search Console's Performance report, use the Date filter's Compare option to set two periods "
            "(Google's help page \"Advanced filtering and comparison\"). Monthly or longer periods even out day-of-week swings.",
            "Copy the Queries table into the Queries tab: query, clicks, impressions and average position for each period. "
            "If your export does not carry both periods, export each period on its own and paste them side by side.",
            "Check the settings on the Settings tab. The defaults flag a query when CTR fell by 25% or more, position moved by 1 or less, "
            "and the later period had at least 100 impressions.",
            "For each flagged query, search it in Google yourself and record in the shaded column whether an AI Overview showed, and the date you looked.",
            "Read the Diagnosis column. Review titles and snippets for the queries with no AI Overview first: those are the ones a rewrite might fix.",
        ],
        [
            "Google says AI Overviews and AI Mode traffic is included in the Web search type of the Performance report and does not report it separately. "
            "So Search Console cannot tell you which queries showed an AI Overview. That is why the check in step 4 is by hand.",
            "AI Overviews do not show for every search, every user or every location. One check is one sample: write the date, and look again before you act on a big query.",
            "Expected CTR is your own site's CTR at that position in the earlier period (clicks divided by impressions, for all queries at that rounded position). "
            "It is not an industry benchmark.",
            "A fall in CTR at a steady position has other causes too: new ads, a featured snippet or video block, a change in searcher intent, or seasonality. "
            "The diagnosis says \"may\" for that reason.",
            "Example rows are fictional.",
        ],
    )
    st = wb.create_sheet("Settings")
    st.sheet_view.showGridLines = False
    st.column_dimensions["A"].width = 52
    st.column_dimensions["B"].width = 12
    settings = [("Flag when CTR fell by at least (relative)", 0.25, "0%"),
                ("Treat position as steady if it moved by no more than", 1.0, "0.0"),
                ("Minimum impressions in the later period", 100, "#,##0")]
    st["A1"] = "Settings"
    st["A1"].font = TITLE
    for j, (lab, v, fmt) in enumerate(settings, 3):
        st.cell(row=j, column=1, value=lab).font = BODY
        c = st.cell(row=j, column=2, value=v)
        c.fill = IN_FILL
        c.font = BOLD
        c.number_format = fmt

    q = wb.create_sheet("Queries")
    cols = ["Query", "Clicks (earlier)", "Clicks (later)", "Impressions (earlier)", "Impressions (later)",
            "Position (earlier)", "Position (later)", "CTR (earlier)", "CTR (later)", "CTR change",
            "Position change", "Expected CTR at this position", "Flag",
            "AI Overview shown? (you check)", "Date checked", "Diagnosis"]
    header(q, 1, cols, [34, 10, 10, 12, 12, 10, 10, 10, 10, 10, 10, 13, 26, 16, 12, 44])
    for i, row in enumerate(QUERIES, 2):
        for c, v in enumerate(row[:7], 1):
            q.cell(row=i, column=c, value=v)
        if row[7]:
            q.cell(row=i, column=14, value=row[7])
            if row[7] in ("Yes", "No"):
                q.cell(row=i, column=15, value="2026-11-02")
    last = 501
    for i in range(2, last + 1):
        q[f"H{i}"] = f'=IF(N(D{i})=0,"",B{i}/D{i})'
        q[f"I{i}"] = f'=IF(N(E{i})=0,"",C{i}/E{i})'
        q[f"J{i}"] = f'=IF(OR(H{i}="",I{i}="",N(H{i})=0),"",I{i}/H{i}-1)'
        q[f"K{i}"] = f'=IF(OR(F{i}="",G{i}=""),"",G{i}-F{i})'
        q[f"L{i}"] = (f'=IF(F{i}="","",IFERROR(SUMIFS($B$2:$B${last},$F$2:$F${last},">="&(ROUND(F{i},0)-0.5),$F$2:$F${last},"<"&(ROUND(F{i},0)+0.5))'
                      f'/SUMIFS($D$2:$D${last},$F$2:$F${last},">="&(ROUND(F{i},0)-0.5),$F$2:$F${last},"<"&(ROUND(F{i},0)+0.5)),""))')
        q[f"M{i}"] = (f'=IF(OR(J{i}="",K{i}=""),"",IF(N(E{i})<Settings!$B$5,"Too few impressions",'
                      f'IF(AND(J{i}<=-Settings!$B$3,ABS(K{i})<=Settings!$B$4),"CTR fell at a steady position",'
                      f'IF(J{i}<=-Settings!$B$3,"CTR fell, position moved",""))))')
        q[f"P{i}"] = (f'=IF(M{i}="CTR fell at a steady position",IF(N{i}="Yes","AI Overview shown: the AI answer may be taking the click. Check whether it cites you.",'
                      f'IF(N{i}="No","No AI Overview: check the title, snippet, ads and other results blocks","Search this query and record whether an AI Overview shows")),'
                      f'IF(M{i}="CTR fell, position moved","Ranking changed: look at the position before the CTR",""))')
        q[f"O{i}"].number_format = "@"
        for c in ("H", "I", "L"):
            q[f"{c}{i}"].number_format = "0.0%"
        q[f"J{i}"].number_format = "+0%;-0%;0%"
        q[f"K{i}"].number_format = "+0.0;-0.0;0.0"
        for c in ("B", "C", "D", "E"):
            q[f"{c}{i}"].number_format = "#,##0"
        for c in ("F", "G"):
            q[f"{c}{i}"].number_format = "0.0"
    style_body(q, 2, 60, 1, 16, inputs=(1, 2, 3, 4, 5, 6, 7, 14, 15))
    for i in range(61, last + 1):
        for c in (1, 2, 3, 4, 5, 6, 7, 14, 15):
            q.cell(row=i, column=c).fill = IN_FILL
    dv = DataValidation(type="list", formula1='"Yes,No,Not checked"', allow_blank=True)
    q.add_data_validation(dv)
    dv.add(f"N2:N{last}")
    q.conditional_formatting.add(f"M2:M{last}", FormulaRule(formula=['M2="CTR fell at a steady position"'],
                                 fill=PatternFill("solid", fgColor=LIME), font=Font(name=F, bold=True)))
    q.auto_filter.ref = f"A1:P{last}"

    # summary
    s = wb.create_sheet("Summary")
    s.sheet_view.showGridLines = False
    s.column_dimensions["A"].width = 52
    s.column_dimensions["B"].width = 14
    s.column_dimensions["C"].width = 18
    s["A1"] = "What the sheet found"
    s["A1"].font = TITLE
    header_row = 3
    for i, lab in enumerate(["Group", "Queries", "Clicks lost"], 1):
        c = s.cell(row=header_row, column=i, value=lab)
        c.font = HEAD_FONT
        c.fill = HEAD_FILL
    groups = [
        ("CTR fell at a steady position, AI Overview shown", '"CTR fell at a steady position"', '"Yes"'),
        ("CTR fell at a steady position, no AI Overview", '"CTR fell at a steady position"', '"No"'),
        ("CTR fell at a steady position, not checked yet", '"CTR fell at a steady position"', None),
        ("CTR fell and position moved", '"CTR fell, position moved"', "ANY"),
    ]
    rng = f"Queries!$M$2:$M${last}"
    nrng = f"Queries!$N$2:$N${last}"
    lost = f"(Queries!$B$2:$B${last}-Queries!$C$2:$C${last})"
    for j, (lab, flag, aio) in enumerate(groups, header_row + 1):
        s.cell(row=j, column=1, value=lab)
        if aio == "ANY":
            s.cell(row=j, column=2, value=f"=COUNTIF({rng},{flag})")
            s.cell(row=j, column=3, value=f"=SUMPRODUCT(({rng}={flag})*{lost})")
        elif aio is None:
            s.cell(row=j, column=2, value=f'=COUNTIF({rng},{flag})-COUNTIFS({rng},{flag},{nrng},"Yes")-COUNTIFS({rng},{flag},{nrng},"No")')
            s.cell(row=j, column=3, value=f'=SUMPRODUCT(({rng}={flag})*({nrng}<>"Yes")*({nrng}<>"No")*{lost})')
        else:
            s.cell(row=j, column=2, value=f"=COUNTIFS({rng},{flag},{nrng},{aio})")
            s.cell(row=j, column=3, value=f"=SUMPRODUCT(({rng}={flag})*({nrng}={aio})*{lost})")
        s.cell(row=j, column=3).number_format = "#,##0"
    style_body(s, header_row + 1, header_row + len(groups), 1, 3)
    s.cell(row=header_row + 6, column=1, value=(
        "Clicks lost = earlier clicks minus later clicks for the queries in each group. Periods of different lengths are not adjusted.")).font = SUB
    s.cell(row=header_row + 8, column=1, value=CREDIT).font = SUB
    wb.move_sheet("Summary", offset=-2)
    wb.save(HERE / "ai-overview-ctr-loss-finder.xlsx")


if __name__ == "__main__":
    build_report()
    build_checklist()
    build_ctr()
    print("built")

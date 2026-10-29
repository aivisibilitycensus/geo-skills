import csv, random, sys

rng = random.Random(7)
Q = [
 ("ACC01", "vendor selection", "Which accounting firms in Dublin work with small tech companies?"),
 ("ACC02", "vendor selection", "Can you recommend an accountant in Dublin for a sole trader?"),
 ("ACC03", "vendor selection", "Who are the best small business accountants in south Dublin?"),
 ("ACC04", "vendor selection", "Which Dublin accountants are good with R&D tax credit claims?"),
 ("ACC05", "vendor selection", "I run a cafe in Dublin 8. Which accountants should I talk to?"),
 ("ACC06", "vendor selection", "What are the best accounting firms in Dublin for a startup raising its first round?"),
 ("ACC07", "comparison", "Should I use a big accounting firm or a small local one in Dublin?"),
 ("ACC08", "comparison", "How do the main small business accountants in Dublin compare?"),
 ("ACC09", "specific need", "Who can file my Irish company accounts before the CRO deadline next month?"),
 ("ACC10", "specific need", "Which Dublin accountants do fixed-fee monthly bookkeeping under 300 euro?"),
 ("ACC11", "educational", "How much does an accountant cost for a small company in Ireland?"),
 ("ACC12", "educational", "What should I look for when choosing an accountant in Dublin?"),
]
ENGINES = ["chatgpt", "copilot", "perplexity"]
DATES = ["2026-09-14", "2026-10-12"]
LIFFEY_NAMES = ["Liffey Ledger Accountants", "Liffey Ledger", "liffey ledger"]
COMP = {
 "H": (["Harbour & Quay Accounting", "Harbour and Quay"], ["https://harbourquay.example/services/", "https://www.harbourquay.example"]),
 "G": (["Grangegorman Tax Partners", "Grangegorman Tax"], ["https://grangegormantax.example/r-and-d"]),
 "N": (["Northside Numbers"], ["https://northsidenumbers.example/pricing/"]),
}
LIFFEY_URLS = ["https://www.liffeyledger.example/", "https://liffeyledger.example/tech-startups",
               "http://blog.liffeyledger.example/choosing-an-accountant/", "liffeyledger.example/fees"]
NEUTRAL = ["https://dublinbusinessguide.example/accountants", "https://irishsmeforum.example/thread/221",
           "https://startupireland.example/guides/accounts"]

def p_named(qid, intent, engine, period):
    if qid in ("ACC10", "ACC12"):
        return 0.0
    base = {"vendor selection": 0.45, "comparison": 0.3, "specific need": 0.3, "educational": 0.08}[intent]
    if engine == "copilot":
        base -= 0.15
    if engine == "perplexity" and period == 1 and intent == "vendor selection":
        base += 0.35
    return max(0.0, min(1.0, base))

rows = []
for pi, date in enumerate(DATES):
    for qid, intent, text in Q:
        for eng in ENGINES:
            for run in (1, 2, 3):
                named_l = rng.random() < p_named(qid, intent, eng, pi)
                comps = [c for c in "HGN" if rng.random() < (0.55 if intent != "educational" else 0.25)]
                if qid == "ACC12" and rng.random() < 0.5 and not comps:
                    comps = ["H"]
                order = comps[:]
                if named_l:
                    order.insert(rng.randint(0, len(order)), "L")
                names, urls = [], []
                for c in order:
                    if c == "L":
                        names.append(rng.choice(LIFFEY_NAMES))
                    else:
                        names.append(rng.choice(COMP[c][0]))
                        if rng.random() < 0.6:
                            urls.append(rng.choice(COMP[c][1]))
                cite_l = (named_l and rng.random() < 0.55) or (not named_l and rng.random() < (0.45 if qid in ("ACC12", "ACC11", "ACC04") else 0.12))
                if cite_l:
                    urls.append(rng.choice(LIFFEY_URLS))
                urls.append(rng.choice(NEUTRAL))
                rng.shuffle(urls)
                if names:
                    if len(names) == 1:
                        lst = names[0]
                    else:
                        lst = ", ".join(names[:-1]) + " and " + names[-1]
                    ans = ("Here are some options in Dublin. %s are often recommended. %s is a good starting point "
                           "for a first call, and it is worth asking each firm about fixed fees." % (lst, names[0]))
                else:
                    ans = ("Costs and fit vary. Ask about fixed fees, sector experience, and whether the firm is a "
                           "member of a recognized accountancy body. Get two or three quotes before deciding.")
                rows.append({"run_date": date, "engine": eng, "question_id": qid, "intent": intent,
                             "run_number": run, "question": text, "answer_text": ans,
                             "cited_urls": "; ".join(urls), "data_note": "synthetic example, fictional businesses"})
rows.insert(40, dict(rows[39]))  # one exact duplicate, to show it is dropped
w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()))
w.writeheader(); w.writerows(rows)

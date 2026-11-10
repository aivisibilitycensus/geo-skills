#!/usr/bin/env python3
"""collect.py: run a fixed question set on AI engines and log every answer.

Writes the canonical CSV that answer-log-analyzer reads (one row per answer) and keeps
the raw provider response for every call. Standard library only. You bring the API
keys; nothing is sent anywhere except the provider you choose.

Engines and the provider each one goes through:

  chatgpt              DataForSEO  (ai_optimization/chat_gpt/llm_scraper)
  gemini               DataForSEO  (ai_optimization/gemini/llm_scraper)
  google_ai_overview   SerpApi     (engine=google, the ai_overview block)
  google_ai_mode       SerpApi     (engine=google_ai_mode)
  copilot              SerpApi     (engine=bing_copilot)
  mock                 no network  (deterministic fake answers, for dry runs and tests)

Keys are read from the environment, never from arguments or files:

  DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD
  SERPAPI_KEY

Typical use:

  python3 collect.py plan    questions.csv --engines chatgpt,gemini --repeats 3
  python3 collect.py run     questions.csv --engines chatgpt,gemini --repeats 3 \
                             --out answers.csv --yes
  python3 collect.py resume  --out answers.csv        # fetch DataForSEO tasks still pending

Every call costs money on the provider's side. "plan" prints the number of calls and
makes none. "run" refuses to start without --yes.
"""
import argparse
import base64
import csv
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

FIELDS = ["run_date", "engine", "question_id", "intent", "run_number", "question",
          "answer_text", "cited_urls", "data_note"]

DFS_BASE = "https://api.dataforseo.com/v3/"
SERP_BASE = "https://serpapi.com/search.json"

# engine label -> (provider, provider engine name)
ENGINES = {
    "chatgpt": ("dataforseo", "chat_gpt"),
    "gemini": ("dataforseo", "gemini"),
    "google_ai_overview": ("serpapi", "google"),
    "google_ai_mode": ("serpapi", "google_ai_mode"),
    "copilot": ("serpapi", "bing_copilot"),
    "mock": ("mock", "mock"),
}
# SerpApi calls made per answer, worst case. An AI Overview that loads late needs a second call.
MAX_CALLS = {"chatgpt": 1, "gemini": 1, "google_ai_overview": 2, "google_ai_mode": 1,
             "copilot": 1, "mock": 0}

DFS_PENDING = (40601, 40602)   # task handed to the engine, task in queue


class CollectError(Exception):
    pass


# --------------------------------------------------------------------------- question set

def read_questions(path):
    """Read a question set CSV. Accepts question-set-builder's columns (id, service,
    intent, question) or the analyzer's names (question_id, intent, question)."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise CollectError(f"{path}: no rows")
    out, seen = [], set()
    for i, raw in enumerate(rows, start=2):
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        qid = r.get("question_id") or r.get("id")
        text = r.get("question") or r.get("prompt") or r.get("text")
        if not qid or not text:
            raise CollectError(f"{path} line {i}: needs an id (id or question_id) and a question")
        if qid in seen:
            raise CollectError(f"{path} line {i}: duplicate question id {qid}")
        seen.add(qid)
        out.append({"question_id": qid, "intent": r.get("intent", ""), "question": text})
    return out


def parse_engines(value):
    names = [e.strip().lower() for e in value.split(",") if e.strip()]
    if not names:
        raise CollectError("no engines given")
    bad = [e for e in names if e not in ENGINES]
    if bad:
        raise CollectError(f"unknown engine(s): {', '.join(bad)}. Known: {', '.join(ENGINES)}")
    if len(set(names)) != len(names):
        raise CollectError("an engine is listed twice")
    return names


def plan(questions, engines, repeats):
    cells = [(q, e, n) for e in engines for q in questions for n in range(1, repeats + 1)]
    per_engine = {e: len(questions) * repeats for e in engines}
    calls = {}
    for e in engines:
        prov = ENGINES[e][0]
        calls[prov] = calls.get(prov, 0) + per_engine[e] * MAX_CALLS[e]
    return cells, per_engine, calls


def plan_text(questions, engines, repeats):
    _, per_engine, calls = plan(questions, engines, repeats)
    lines = [f"{len(questions)} questions x {len(engines)} engine(s) x {repeats} repeat(s) "
             f"= {sum(per_engine.values())} answers"]
    for e in engines:
        lines.append(f"  {e}: {per_engine[e]} answers via {ENGINES[e][0]}")
    for prov, n in calls.items():
        if prov == "mock":
            continue
        lines.append(f"  {prov}: up to {n} billable call(s). Check the provider's current price "
                     f"per call before running.")
    if repeats < 3:
        lines.append("  Note: fewer than 3 repeats. One answer shows what one answer said, not "
                     "what the engine usually says.")
    return "\n".join(lines)


# --------------------------------------------------------------------------- output files

def load_done(out_path):
    """Cells already in the output CSV: (run_date, engine, question_id, run_number)."""
    done = set()
    if os.path.exists(out_path):
        with open(out_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                done.add((r["run_date"], r["engine"], r["question_id"], str(r["run_number"])))
    return done


def append_row(out_path, row):
    new = not os.path.exists(out_path) or os.path.getsize(out_path) == 0
    with open(out_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})


def raw_dir_for(out_path):
    d = os.path.splitext(out_path)[0] + "-raw"
    os.makedirs(d, exist_ok=True)
    return d


def save_raw(out_path, name, data):
    path = os.path.join(raw_dir_for(out_path), name + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return path


def pending_path(out_path):
    return os.path.splitext(out_path)[0] + "-pending.json"


def load_pending(out_path):
    p = pending_path(out_path)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_pending(out_path, items):
    p = pending_path(out_path)
    if not items:
        if os.path.exists(p):
            os.remove(p)
        return
    with open(p, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=1)


def cell_name(cell):
    return "{run_date}_{engine}_{question_id}_run{run_number}".format(**cell)


# --------------------------------------------------------------------------- HTTP

def http_json(url, method="GET", headers=None, body=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            raise CollectError(f"HTTP {e.code} from {urllib.parse.urlsplit(url).netloc}")
    except (urllib.error.URLError, OSError) as e:
        raise CollectError(f"{urllib.parse.urlsplit(url).netloc}: {e}")
    try:
        return json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        raise CollectError(f"{urllib.parse.urlsplit(url).netloc}: response was not JSON")


def env(name):
    v = os.environ.get(name, "").strip()
    if not v:
        raise CollectError(f"environment variable {name} is not set")
    return v


# --------------------------------------------------------------------------- DataForSEO

def dfs_headers():
    token = base64.b64encode(f"{env('DATAFORSEO_LOGIN')}:{env('DATAFORSEO_PASSWORD')}".encode()).decode()
    return {"Authorization": "Basic " + token, "Content-Type": "application/json"}


def dfs_call(method, path, body=None, fetch=http_json):
    d = fetch(DFS_BASE + path, method=method, headers=dfs_headers(), body=body)
    if int(d.get("status_code") or 0) != 20000:
        raise CollectError(f"DataForSEO {d.get('status_code')}: {d.get('status_message')}")
    return d


def dfs_post(cell, opts, fetch=http_json):
    """Create one task. Returns the task id."""
    task = {"keyword": cell["question"].replace("%", "%25").replace("+", "%2B"),
            "location_code": opts["location_code"], "language_code": opts["language_code"],
            "tag": cell_name(cell)[:255]}
    if cell["provider_engine"] == "chat_gpt" and opts.get("force_web_search"):
        task["force_web_search"] = True
    d = dfs_call("POST", f"ai_optimization/{cell['provider_engine']}/llm_scraper/task_post", [task], fetch)
    tk = (d.get("tasks") or [{}])[0]
    if int(tk.get("status_code") or 0) != 20100 or not tk.get("id"):
        raise CollectError(f"DataForSEO task not created: {tk.get('status_code')} {tk.get('status_message')}")
    return tk["id"]


def dfs_get(cell, fetch=http_json):
    """Return ('pending', None) | ('done', result dict) | ('error', message)."""
    path = f"ai_optimization/{cell['provider_engine']}/llm_scraper/task_get/advanced/{urllib.parse.quote(cell['task_id'])}"
    d = dfs_call("GET", path, None, fetch)
    tk = (d.get("tasks") or [{}])[0]
    sc = int(tk.get("status_code") or 0)
    if sc == 20000:
        return "done", ((tk.get("result") or [{}])[0] or {})
    if sc in DFS_PENDING:
        return "pending", None
    return "error", f"{sc} {tk.get('status_message')}"


def dfs_parse(result):
    answer = str(result.get("markdown") or "")
    urls = []
    for src in result.get("sources") or []:
        u = str((src or {}).get("url") or "")
        if u and u not in urls:
            urls.append(u)
    notes = []
    if result.get("model"):
        notes.append(f"model={result['model']}")
    if "search_results" in result:
        notes.append(f"web_search_results={len(result.get('search_results') or [])}")
    return answer, urls, notes


# --------------------------------------------------------------------------- SerpApi

def flatten_blocks(blocks):
    """Turn SerpApi text_blocks into plain lines, keeping list item titles (often the brand)."""
    out = []
    for b in blocks or []:
        if not isinstance(b, dict):
            continue
        if b.get("snippet"):
            out.append(str(b["snippet"]))
        for key in ("list", "items"):
            for it in b.get(key) or []:
                if not isinstance(it, dict):
                    out.append("- " + str(it))
                    continue
                title = str(it.get("title") or "").strip()
                snip = str(it.get("snippet") or "").strip()
                links = it.get("snippet_links") or []
                if not title and links and (not snip or snip.startswith(":")):
                    host = urllib.parse.urlsplit(str(links[0].get("link") or "")).netloc
                    if host:
                        title = "[" + (host[4:] if host.startswith("www.") else host) + "]"
                joiner = " " if title and snip and not title.endswith(":") and not snip.startswith(":") else ""
                line = (title + joiner + snip).strip()
                if line:
                    out.append("- " + line)
                nested = []
                for nk in ("list", "items", "text_blocks"):
                    v = it.get(nk)
                    if isinstance(v, list) and v:
                        nested += v if nk == "text_blocks" else [{"list": v}]
                out += flatten_blocks(nested)
        if isinstance(b.get("text_blocks"), list):
            out += flatten_blocks(b["text_blocks"])
    return out


def serp_get(params, fetch=http_json):
    q = dict(params)
    q["api_key"] = env("SERPAPI_KEY")
    d = fetch(SERP_BASE + "?" + urllib.parse.urlencode(q))
    if d.get("error"):
        raise CollectError(f"SerpApi: {d['error']}")
    return d


def serp_parse(block):
    block = block or {}
    answer = str(block.get("reconstructed_markdown") or "")
    if not answer:
        answer = (str(block.get("header") or "") + "\n\n" + "\n".join(flatten_blocks(block.get("text_blocks")))).strip()
    urls = []
    for r in block.get("references") or []:
        u = str((r or {}).get("link") or "")
        if u and u not in urls:
            urls.append(u)
    return answer, urls


def serp_run(cell, opts, fetch=http_json):
    """Return (answer, urls, notes, raw)."""
    geo = {k: opts[k] for k in ("gl", "hl", "location") if opts.get(k)}
    pe = cell["provider_engine"]
    notes = []
    if pe == "google":
        data = serp_get({"engine": "google", "q": cell["question"], "no_cache": "true", **geo}, fetch)
        aio = data.get("ai_overview")
        if isinstance(aio, dict) and not aio.get("text_blocks") and aio.get("page_token"):
            more = serp_get({"engine": "google_ai_overview", "page_token": aio["page_token"]}, fetch)
            aio = more.get("ai_overview") or aio
            data = {"first": data.get("search_metadata"), "ai_overview": aio}
        shown = isinstance(aio, dict) and bool(aio.get("text_blocks"))
        if not shown:
            return "", [], ["no AI Overview shown"], data
        answer, urls = serp_parse(aio)
        return answer, urls, notes, data
    params = {"engine": pe, "q": cell["question"], "no_cache": "true"}
    if pe == "google_ai_mode":
        params.update(geo)
    data = serp_get(params, fetch)
    answer, urls = serp_parse(data)
    return answer, urls, notes, data


# --------------------------------------------------------------------------- mock

MOCK_BRANDS = ["Harbour & Quay Accounting", "Northside Numbers", "Liffey Ledger",
               "Grangegorman Tax Partners"]
MOCK_HOSTS = ["harbourquay.example", "northsidenumbers.example", "liffeyledger.example",
              "grangegormantax.example"]


def mock_run(cell):
    """Deterministic fake answer. Different repeats name different brands, like real engines do."""
    h = hashlib.sha256(cell_name(cell).encode()).digest()
    picks = [i for i in range(len(MOCK_BRANDS)) if h[i] % 3 != 0] or [h[0] % len(MOCK_BRANDS)]
    names = [MOCK_BRANDS[i] for i in picks]
    answer = f"For \"{cell['question']}\", options often mentioned are {', '.join(names)}."
    urls = [f"https://{MOCK_HOSTS[i]}/" for i in picks if h[i + 8] % 2 == 0]
    return answer, urls, ["mock answer, fictional businesses"], {"mock": True, "picks": picks}


# --------------------------------------------------------------------------- running

def make_row(cell, answer, urls, notes, opts):
    base = [f"provider={cell['provider']}"]
    if cell["provider"] == "dataforseo":
        base.append(f"location_code={opts['location_code']}")
    elif cell["provider"] == "serpapi":
        base += [f"{k}={opts[k]}" for k in ("gl", "hl", "location") if opts.get(k)]
    if opts.get("note"):
        base.append(opts["note"])
    return {"run_date": cell["run_date"], "engine": cell["engine"], "question_id": cell["question_id"],
            "intent": cell["intent"], "run_number": cell["run_number"], "question": cell["question"],
            "answer_text": answer, "cited_urls": "; ".join(urls), "data_note": "; ".join(base + notes)}


def build_cells(questions, engines, repeats, run_date):
    cells = []
    for e in engines:
        prov, pe = ENGINES[e]
        for n in range(1, repeats + 1):
            for q in questions:
                cells.append({"run_date": run_date, "engine": e, "provider": prov, "provider_engine": pe,
                              "question_id": q["question_id"], "intent": q["intent"],
                              "question": q["question"], "run_number": n})
    return cells


def collect(cells, out_path, opts, fetch=http_json, log=print, sleep=time.sleep):
    """Run every cell not already in the output. Returns counts."""
    done = load_done(out_path)
    pending = load_pending(out_path)
    pend_keys = {(p["run_date"], p["engine"], p["question_id"], str(p["run_number"])) for p in pending}
    counts = {"written": 0, "skipped": 0, "posted": 0, "errors": 0}
    for cell in cells:
        key = (cell["run_date"], cell["engine"], cell["question_id"], str(cell["run_number"]))
        if key in done or key in pend_keys:
            counts["skipped"] += 1
            continue
        try:
            if cell["provider"] == "mock":
                answer, urls, notes, raw = mock_run(cell)
            elif cell["provider"] == "serpapi":
                answer, urls, notes, raw = serp_run(cell, opts, fetch)
            else:
                task_id = dfs_post(cell, opts, fetch)
                pending.append(dict(cell, task_id=task_id, posted_at=int(time.time())))
                save_pending(out_path, pending)
                counts["posted"] += 1
                continue
        except CollectError as e:
            counts["errors"] += 1
            log(f"  error {cell_name(cell)}: {e}")
            continue
        save_raw(out_path, cell_name(cell), raw)
        append_row(out_path, make_row(cell, answer, urls, notes, opts))
        counts["written"] += 1
        if opts.get("delay"):
            sleep(opts["delay"])
    if pending:
        got = poll(out_path, opts, fetch=fetch, log=log, sleep=sleep)
        counts["written"] += got["written"]
        counts["errors"] += got["errors"]
        counts["still_pending"] = got["still_pending"]
    return counts


def poll(out_path, opts, fetch=http_json, log=print, sleep=time.sleep):
    """Fetch DataForSEO tasks until done or until the wait runs out."""
    deadline = time.time() + opts.get("wait", 600)
    counts = {"written": 0, "errors": 0, "still_pending": 0}
    pending = load_pending(out_path)
    while pending:
        rest = []
        for cell in pending:
            try:
                state, result = dfs_get(cell, fetch)
            except CollectError as e:
                state, result = "pending", None
                log(f"  retry later {cell_name(cell)}: {e}")
            if state == "pending":
                rest.append(cell)
                continue
            if state == "error":
                counts["errors"] += 1
                log(f"  error {cell_name(cell)}: DataForSEO {result}")
                continue
            answer, urls, notes = dfs_parse(result)
            save_raw(out_path, cell_name(cell), result)
            append_row(out_path, make_row(cell, answer, urls, notes, opts))
            counts["written"] += 1
        pending = rest
        save_pending(out_path, pending)
        if not pending or time.time() >= deadline:
            break
        sleep(opts.get("poll_every", 20))
    counts["still_pending"] = len(pending)
    return counts


# --------------------------------------------------------------------------- CLI

def add_common(p):
    p.add_argument("questions", help="question set CSV (id, intent, question)")
    p.add_argument("--engines", required=True, help="comma-separated: " + ", ".join(ENGINES))
    p.add_argument("--repeats", type=int, default=3, help="answers per question per engine (default 3)")


def opts_from(a):
    return {"location_code": a.location_code, "language_code": a.language_code,
            "force_web_search": a.force_web_search, "gl": a.gl, "hl": a.hl, "location": a.location,
            "delay": a.delay, "wait": a.wait, "poll_every": a.poll_every, "note": a.note}


def add_run_opts(p):
    p.add_argument("--out", required=True, help="answers CSV to write or append to")
    p.add_argument("--location-code", type=int, default=2840,
                   help="DataForSEO location code (default 2840, United States)")
    p.add_argument("--language-code", default="en", help="DataForSEO language code")
    p.add_argument("--force-web-search", action="store_true",
                   help="ChatGPT only: force a web search. Off by default, so ChatGPT decides as it does for a user")
    p.add_argument("--gl", default="", help="SerpApi country, for example us or ie")
    p.add_argument("--hl", default="", help="SerpApi language, for example en")
    p.add_argument("--location", default="", help="SerpApi location, for example Dublin, Ireland")
    p.add_argument("--delay", type=float, default=0.0, help="seconds between SerpApi calls")
    p.add_argument("--wait", type=int, default=600, help="seconds to wait for DataForSEO tasks (default 600)")
    p.add_argument("--poll-every", type=int, default=20)
    p.add_argument("--note", default="", help="text added to data_note on every row")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="count the calls; makes none")
    add_common(p)
    r = sub.add_parser("run", help="collect answers")
    add_common(r)
    add_run_opts(r)
    r.add_argument("--run-date", default="", help="YYYY-MM-DD (default: today, UTC)")
    r.add_argument("--yes", action="store_true", help="confirm that the calls shown by plan may be made")
    s = sub.add_parser("resume", help="fetch DataForSEO tasks still pending for an output file")
    s.add_argument("--out", required=True)
    s.add_argument("--wait", type=int, default=600)
    s.add_argument("--poll-every", type=int, default=20)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "resume":
            if not load_pending(a.out):
                print("Nothing pending.")
                return 0
            c = poll(a.out, {"wait": a.wait, "poll_every": a.poll_every, "location_code": "", "note": "resumed"})
            print(f"Written {c['written']}, errors {c['errors']}, still pending {c['still_pending']}")
            return 0 if not c["still_pending"] else 2
        questions = read_questions(a.questions)
        engines = parse_engines(a.engines)
        if a.repeats < 1:
            raise CollectError("--repeats must be at least 1")
        print(plan_text(questions, engines, a.repeats))
        if a.cmd == "plan":
            return 0
        if not a.yes and engines != ["mock"]:
            print("\nNot started. Add --yes to make these calls.")
            return 1
        run_date = a.run_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        datetime.strptime(run_date, "%Y-%m-%d")
        cells = build_cells(questions, engines, a.repeats, run_date)
        c = collect(cells, a.out, opts_from(a))
        print(f"\nWritten {c['written']}, already there {c['skipped']}, errors {c['errors']}"
              + (f", still pending {c['still_pending']} (run: collect.py resume --out {a.out})"
                 if c.get("still_pending") else ""))
        print(f"Answers: {a.out}\nRaw responses: {raw_dir_for(a.out)}/")
        return 0 if not c["errors"] and not c.get("still_pending") else 2
    except CollectError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

// VS-001 step 1: list archived article URLs per blog from the Wayback Machine CDX index and shuffle them
// with the fixed seed. Writes data/candidates/<blog>.json. Deterministic given the same CDX result.
//
//   node sample.mjs [--blogs blogs.json] [--out data/candidates]
//
// The CDX index itself can change over time (new captures are added), so the exact candidate list is
// committed with the results. The shuffle is seeded per blog, so one blog's order never affects another's.

import fs from 'node:fs';
import path from 'node:path';
import { shuffle, looksLikeArticle, fetchText, sleep } from './lib.mjs';

const args = Object.fromEntries(process.argv.slice(2).map((a, i, all) => a.startsWith('--') ? [a.slice(2), all[i + 1]] : []).filter(x => x.length));
const cfg = JSON.parse(fs.readFileSync(args.blogs || 'blogs.json', 'utf8'));
const outDir = args.out || 'data/candidates';
let anyFailed = false;
fs.mkdirSync(outDir, { recursive: true });

const allBlogs = cfg.groups.flatMap(g => g.blogs.map(b => ({ blog: b, group: g.name, reserve: false }))
  .concat(g.reserve.map(b => ({ blog: b, group: g.name, reserve: true }))));

for (const { blog, group, reserve } of allBlogs) {
  const file = path.join(outDir, blog.replace(/[\/]/g, '_') + '.json');
  if (fs.existsSync(file)) { console.log('have', blog); continue; }
  if (fs.existsSync(file + '.failed')) fs.unlinkSync(file + '.failed');
  // The CDX API: every 200 text/html capture under the blog root in the window, one row per URL (earliest
  // capture). The index times out on large hosts, so the window is queried in half-year slices and merged,
  // and a slice that still fails after six tries marks the blog as failed instead of pretending it has no
  // articles (an index outage is not "fewer than four eligible articles").
  // Strategy: one query for the whole window first (cheapest when it works); if that fails, fall back to one
  // query per year. Each query gets 4 tries with a 20 s gap. The index is often overloaded, so progress is
  // committed per blog (VS001_COMMIT=1) and a rerun skips blogs already done.
  const years = [];
  for (let y = Number(cfg.from.slice(0, 4)); y <= Number(cfg.to.slice(0, 4)); y++) {
    const from = Math.max(Number(cfg.from), Number(y + '0101')), to = Math.min(Number(cfg.to), Number(y + '1231'));
    years.push([String(from), String(to)]);
  }
  const byUrl = new Map();
  let rowsTotal = 0;
  async function querySlice(from, to) {
    const q = 'https://web.archive.org/cdx/search/cdx?url=' + encodeURIComponent(blog + '/*') +
      '&from=' + from + '&to=' + to +
      '&filter=statuscode:200&filter=mimetype:text/html&collapse=urlkey&fl=timestamp,original&output=json&limit=20000';
    for (let attempt = 1; attempt <= 4; attempt++) {
      try {
        const txt = await fetchText(q);
        const rows = txt.trim() ? JSON.parse(txt).slice(1) : [];
        rowsTotal += rows.length;
        for (const [ts, original] of rows) {
          const prev = byUrl.get(original);
          if (!prev || ts < prev) byUrl.set(original, ts);
        }
        return true;
      } catch (e) {
        console.error('CDX', blog, from + '-' + to, 'attempt', attempt, e.message.slice(0, 80));
        await sleep(20000);
      }
    }
    return false;
  }
  let failed = null;
  if (!(await querySlice(cfg.from, cfg.to))) {
    for (const [from, to] of years) {
      if (await querySlice(from, to)) { await sleep(1000); continue; }
      // A year that still times out (whole-domain blogs such as copyblogger.com) is tried in quarters.
      const y = from.slice(0, 4);
      for (const [a, b] of [['0101', '0331'], ['0401', '0630'], ['0701', '0930'], ['1001', '1231']]) {
        const qf = String(Math.max(Number(from), Number(y + a))), qt = String(Math.min(Number(to), Number(y + b)));
        if (qf > qt) continue;
        if (!(await querySlice(qf, qt))) { failed = qf + '-' + qt; break; }
        await sleep(1000);
      }
      if (failed) break;
    }
  }
  if (failed) {
    fs.writeFileSync(file + '.failed', JSON.stringify({ blog, group, reserve, failedSlice: failed, at: new Date().toISOString() }));
    console.error(blog, 'CDX FAILED on slice', failed, '(blog marked failed; rerun the sample step)');
    anyFailed = true;
    continue;
  }
  const rows = Array.from(byUrl, ([original, ts]) => [ts, original]).sort((a, b) => a[0] < b[0] ? -1 : 1);
  const seen = new Set();
  const urls = [];
  for (const [ts, original] of rows) {
    const clean = original.replace(/^https?:\/\/(www\.)?/, '').replace(/:80\//, '/').replace(/\/+$/, '');
    if (seen.has(clean)) continue;
    seen.add(clean);
    if (looksLikeArticle(clean, blog)) urls.push({ url: original, earliest: ts });
  }
  const ordered = shuffle(urls, cfg.seed, blog);
  fs.writeFileSync(file, JSON.stringify({ blog, group, reserve, cdxRows: rows.length, articleLike: urls.length, queriedAt: new Date().toISOString(), seed: cfg.seed, candidates: ordered }, null, 1));
  console.log(blog, 'cdx rows', rows.length, 'article-like', urls.length);
  if (process.env.VS001_COMMIT === '1') {
    const { execSync } = await import('node:child_process');
    try {
      execSync('git add "' + file + '" && git commit -q -m "VS-001 sample: ' + blog + '" && git pull -q --rebase origin main && git push -q origin HEAD:main', { stdio: 'inherit' });
    } catch (e) { console.error('commit failed for', blog, e.message.slice(0, 100)); }
  }
  await sleep(1500);
}
if (anyFailed) { console.error('one or more blogs failed at the CDX index; fix and rerun before fetching'); process.exit(1); }

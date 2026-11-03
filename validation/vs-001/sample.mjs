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
fs.mkdirSync(outDir, { recursive: true });

const allBlogs = cfg.groups.flatMap(g => g.blogs.map(b => ({ blog: b, group: g.name, reserve: false }))
  .concat(g.reserve.map(b => ({ blog: b, group: g.name, reserve: true }))));

for (const { blog, group, reserve } of allBlogs) {
  const file = path.join(outDir, blog.replace(/[\/]/g, '_') + '.json');
  if (fs.existsSync(file)) { console.log('have', blog); continue; }
  // The CDX API: every 200 text/html capture under the blog root in the window, one row per URL (earliest capture).
  const q = 'https://web.archive.org/cdx/search/cdx?url=' + encodeURIComponent(blog + '/*') +
    '&from=' + cfg.from + '&to=' + cfg.to +
    '&filter=statuscode:200&filter=mimetype:text/html&collapse=urlkey&fl=timestamp,original&output=json&limit=20000';
  let rows = [];
  for (let attempt = 1; attempt <= 4; attempt++) {
    try {
      const txt = await fetchText(q);
      rows = txt.trim() ? JSON.parse(txt).slice(1) : [];
      break;
    } catch (e) {
      console.error('CDX', blog, 'attempt', attempt, e.message);
      await sleep(5000 * attempt);
    }
  }
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
  await sleep(1500);
}

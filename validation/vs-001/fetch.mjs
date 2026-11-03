// VS-001 step 2: walk each blog's shuffled candidates, fetch the earliest archived copy on or before the
// cutoff, reduce it to the article body with Mozilla Readability, convert to Markdown, and keep the first
// four articles per blog that pass the inclusion rules. Writes data/human/<id>.md and data/human/manifest.csv.
// Every candidate looked at is recorded in the manifest with its outcome, accepted or not.
//
//   node fetch.mjs [--blogs blogs.json] [--candidates data/candidates] [--out data/human]

import fs from 'node:fs';
import path from 'node:path';
import { JSDOM } from 'jsdom';
import { Readability } from '@mozilla/readability';
import TurndownService from 'turndown';
import { wordCount, englishShare, fetchText, sleep, toCsv, parseCsv } from './lib.mjs';

const args = Object.fromEntries(process.argv.slice(2).map((a, i, all) => a.startsWith('--') ? [a.slice(2), all[i + 1]] : []).filter(x => x.length));
const cfg = JSON.parse(fs.readFileSync(args.blogs || 'blogs.json', 'utf8'));
const candDir = args.candidates || 'data/candidates';
const outDir = args.out || 'data/human';
const maxLook = Number(args.maxLook || 40);   // candidates examined per blog before giving up on it
fs.mkdirSync(outDir, { recursive: true });

const manifestFile = path.join(outDir, 'manifest.csv');
const COLS = ['id', 'group', 'blog', 'reserve', 'url', 'snapshot', 'archive_url', 'words', 'subheadings', 'english_share', 'outcome', 'reason', 'title', 'sha256'];
const manifest = fs.existsSync(manifestFile) ? parseCsv(fs.readFileSync(manifestFile, 'utf8')) : [];
const save = () => fs.writeFileSync(manifestFile, toCsv(manifest, COLS));

const td = new TurndownService({ headingStyle: 'atx', bulletListMarker: '-', codeBlockStyle: 'fenced' });
td.remove(['script', 'style', 'noscript', 'iframe', 'figure', 'img', 'svg']);

export function htmlToArticle(html, url) {
  const dom = new JSDOM(html, { url });
  const doc = dom.window.document;
  // Wayback's toolbar is injected into the page; id_ copies do not carry it, but strip any remnant.
  for (const el of doc.querySelectorAll('#wm-ipp-base, #wm-ipp, #donato, .wb-autocomplete-suggestions')) el.remove();
  const art = new Readability(doc, { keepClasses: false }).parse();
  if (!art || !art.content) return null;
  const body = new JSDOM(art.content).window.document;
  const headings = body.querySelectorAll('h2, h3, h4').length;
  let md = td.turndown(art.content);
  md = md.replace(/\n{3,}/g, '\n\n').trim();
  return { title: (art.title || '').trim(), markdown: md, subheadings: headings, words: wordCount(md.replace(/^#.*$/gm, '')) };
}

async function earliestSnapshot(url) {
  const q = 'https://web.archive.org/cdx/search/cdx?url=' + encodeURIComponent(url) + '&to=' + cfg.to + '&filter=statuscode:200&fl=timestamp&limit=1&output=json';
  const txt = await fetchText(q);
  const rows = txt.trim() ? JSON.parse(txt) : [];
  return rows[1] ? rows[1][0] : null;
}

function nextId() {
  const n = manifest.reduce((m, r) => Math.max(m, Number((r.id || 'H000').slice(1)) || 0), 0) + 1;
  return 'H' + String(n).padStart(3, '0');
}

async function workBlog(entry, groupName, isReserve) {
  const file = path.join(candDir, entry.replace(/[\/]/g, '_') + '.json');
  if (!fs.existsSync(file)) { throw new Error('no candidates file for ' + entry + ': run sample.mjs first (an index outage is not a reason to replace a blog)'); }
  const cand = JSON.parse(fs.readFileSync(file, 'utf8'));
  let accepted = manifest.filter(r => r.blog === entry && r.outcome === 'accepted').length;
  let looked = manifest.filter(r => r.blog === entry).length;
  for (const c of cand.candidates.slice(looked)) {
    if (accepted >= cfg.perBlog || looked >= maxLook) break;
    looked++;
    const row = { group: groupName, blog: entry, reserve: isReserve ? 'yes' : 'no', url: c.url, outcome: 'excluded' };
    try {
      const ts = await earliestSnapshot(c.url);
      if (!ts) { row.reason = 'no 200 capture on or before cutoff'; manifest.push(row); save(); continue; }
      row.snapshot = ts;
      row.archive_url = 'https://web.archive.org/web/' + ts + 'id_/' + c.url;
      let html = null;
      for (let attempt = 1; attempt <= 3 && html === null; attempt++) {
        try { html = await fetchText(row.archive_url); }
        catch (e) { if (attempt === 3) throw e; await sleep(10000 * attempt); }
      }
      const art = htmlToArticle(html, c.url);
      if (!art) { row.reason = 'readability found no article body'; manifest.push(row); save(); continue; }
      row.title = art.title; row.words = art.words; row.subheadings = art.subheadings;
      row.english_share = englishShare(art.markdown).toFixed(3);
      if (art.words < 500) row.reason = 'under 500 words';
      else if (art.words > 3000) row.reason = 'over 3,000 words';
      else if (art.subheadings < 3) row.reason = 'fewer than 3 subheadings';
      else if (Number(row.english_share) < 0.2) row.reason = 'not English';
      else if (/\b(press release|job description|apply now|glossary)\b/i.test(art.title)) row.reason = 'not an article by title';
      else {
        row.outcome = 'accepted'; row.reason = '';
        row.id = nextId();
        const text = '# ' + art.title + '\n\n' + art.markdown + '\n';
        fs.writeFileSync(path.join(outDir, row.id + '.md'), text);
        row.sha256 = (await import('./lib.mjs')).sha256(text);
        accepted++;
      }
    } catch (e) {
      row.reason = 'fetch error: ' + e.message.slice(0, 120);
    }
    manifest.push(row); save();
    console.log(entry, row.outcome, row.reason || row.id, c.url);
    await sleep(2000);
  }
  return accepted;
}

for (const g of cfg.groups) {
  const reserve = g.reserve.slice();
  for (const b of g.blogs) {
    let blog = b, got = await workBlog(blog, g.name, false);
    while (got < cfg.perBlog && reserve.length) {
      // Protocol: a blog with fewer than four eligible articles is replaced by the next reserve blog.
      // Its accepted rows are kept in the manifest as "replaced" and their texts removed.
      for (const r of manifest) if (r.blog === blog && r.outcome === 'accepted') {
        r.outcome = 'replaced'; r.reason = 'blog had fewer than ' + cfg.perBlog + ' eligible articles';
        try { fs.unlinkSync(path.join(outDir, r.id + '.md')); } catch {}
      }
      save();
      blog = reserve.shift();
      console.log(b, 'had only', got, 'eligible; replaced by reserve', blog);
      got = await workBlog(blog, g.name, true);
    }
  }
}
const total = manifest.filter(r => r.outcome === 'accepted').length;
console.log('accepted', total, 'of target', cfg.groups.length * 5 * cfg.perBlog);

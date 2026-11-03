// Shared helpers for VS-001. Plain Node, no framework.
import { createHash } from 'node:crypto';

// Deterministic PRNG (mulberry32) so the draw can be reproduced from the seed in blogs.json.
export function rng(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Fisher-Yates with a seeded generator. One generator per blog, seeded from the study seed and the blog name,
// so adding or removing a blog does not change another blog's order.
export function shuffle(items, seed, salt) {
  const h = createHash('sha256').update(String(seed) + '|' + salt).digest();
  const r = rng(h.readUInt32BE(0));
  const a = items.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(r() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// Pages that are not articles: tag, category, author, pagination, search, feeds, assets, home.
const NOT_ARTICLE = /(\/(tag|tags|category|categories|author|authors|page|search|topic|topics|archive|feed|rss|amp|wp-content|wp-json|cdn-cgi)\/|\?|#|\.(xml|json|pdf|jpe?g|png|gif|svg|css|js|txt|zip)$|\/(login|signup|sign-up|register|cart|checkout|pricing|contact|about|careers|jobs)\/?$)/i;

export function looksLikeArticle(url, root) {
  const u = url.replace(/^https?:\/\/(www\.)?/, '');
  if (!u.toLowerCase().startsWith(root.toLowerCase())) return false;
  const rest = u.slice(root.length).replace(/^\/+/, '').replace(/\/+$/, '');
  if (!rest) return false;                      // blog home
  if (NOT_ARTICLE.test('/' + rest + '/')) return false;
  const slug = rest.split('/').pop();
  if (!/[a-z]/i.test(slug) || slug.length < 8) return false;   // needs a real slug
  if (!/-/.test(slug) && !/\d{4}/.test(rest)) return false;     // single-word slugs are usually sections
  return true;
}

export function wordCount(text) {
  return (text.match(/[A-Za-z0-9À-ɏ'’]+/g) || []).length;
}

// Cheap English check: share of common English function words among all words.
const EN = new Set(['the','and','to','of','a','in','is','that','for','it','you','with','on','as','are','this','be','or','your','can','at','by','an','from','have','not','will','we','if','but','they','more','their','which','when','what','how','our','all','one','do','so','about','up','out','has','into','than','also','them','these']);
export function englishShare(text) {
  const words = (text.toLowerCase().match(/[a-z']+/g) || []);
  if (!words.length) return 0;
  let n = 0;
  for (const w of words) if (EN.has(w)) n++;
  return n / words.length;
}

export function sha256(buf) {
  return createHash('sha256').update(buf).digest('hex');
}

export function csvCell(v) {
  const s = v == null ? '' : String(v);
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

export function toCsv(rows, cols) {
  return [cols.join(',')].concat(rows.map(r => cols.map(c => csvCell(r[c])).join(','))).join('\n') + '\n';
}

export function parseCsv(text) {
  const lines = text.replace(/\r/g, '').split('\n').filter(Boolean);
  const split = l => {
    const out = []; let cur = ''; let q = false;
    for (let i = 0; i < l.length; i++) {
      const ch = l[i];
      if (q) { if (ch === '"') { if (l[i + 1] === '"') { cur += '"'; i++; } else q = false; } else cur += ch; }
      else if (ch === '"') q = true;
      else if (ch === ',') { out.push(cur); cur = ''; }
      else cur += ch;
    }
    out.push(cur); return out;
  };
  const cols = split(lines[0]);
  return lines.slice(1).map(l => Object.fromEntries(split(l).map((v, i) => [cols[i], v])));
}

export async function fetchText(url, opts = {}) {
  const res = await fetch(url, { headers: { 'user-agent': 'AI Visibility Census VS-001 study (hello@aivisibilitycensus.com)' }, ...opts });
  if (!res.ok) throw new Error('HTTP ' + res.status + ' for ' + url);
  return await res.text();
}

export function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

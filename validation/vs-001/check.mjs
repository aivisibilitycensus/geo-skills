// VS-001 step 4: run one archived copy of the Content Shape Checker (hsc.js) over every article in one or
// more corpus folders and write per-article results. Reproduces exactly what the browser tool does: the
// top-level heading is removed, then parseText and analyze are called with no other preprocessing.
//
//   node check.mjs --checker path/to/hsc.js --label 1.5.4 --corpus data/human --corpus data/ai/claude --out data/results/1.5.4.csv
//
// Output columns: id, corpus, file, checker_label, checker_sha256, words, d1..d4 (0 PASS, 1 PASS WITH NOTES,
// 2 FAIL), fails, flagged (fails >= 2), ai_score, ai_band (if the version has an AI-style reading).

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { sha256, toCsv } from './lib.mjs';

const argv = process.argv.slice(2);
const opt = { corpus: [] };
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--corpus') opt.corpus.push(argv[++i]);
  else if (argv[i].startsWith('--')) opt[argv[i].slice(2)] = argv[++i];
}
if (!opt.checker || !opt.out || !opt.corpus.length) {
  console.error('usage: node check.mjs --checker hsc.js --label VERSION --corpus DIR [--corpus DIR] --out results.csv');
  process.exit(2);
}
const code = fs.readFileSync(opt.checker);
const hash = sha256(code);
const require = createRequire(import.meta.url);
const hsc = require(path.resolve(opt.checker));
if (typeof hsc.parseText !== 'function' || typeof hsc.analyze !== 'function') {
  console.error('checker does not export parseText and analyze'); process.exit(2);
}

const rows = [];
for (const dir of opt.corpus) {
  const corpus = path.basename(dir) === 'human' ? 'human' : path.relative(path.dirname(path.dirname(dir)), dir).replace(/\\/g, '/');
  for (const f of fs.readdirSync(dir).filter(x => x.endsWith('.md') && x.toLowerCase() !== 'readme.md').sort()) {
    const raw = fs.readFileSync(path.join(dir, f), 'utf8');
    const body = raw.replace(/^# .*\n+/, '');            // drop the top-level heading, as Readability does
    const r = hsc.analyze(hsc.parseText(body));
    const lv = d => (d && typeof d.level === 'number') ? d.level : '';
    const fails = [r.d1, r.d2, r.d3, r.d4].filter(d => d && d.level === 2).length;
    rows.push({
      id: f.replace(/\.md$/, ''), corpus, file: path.join(dir, f), checker_label: opt.label || '', checker_sha256: hash,
      words: r.words, d1: lv(r.d1), d2: lv(r.d2), d3: lv(r.d3), d4: lv(r.d4), fails, flagged: fails >= 2 ? 1 : 0,
      ai_score: r.ai && typeof r.ai.score === 'number' ? r.ai.score.toFixed(4) : '',
      ai_band: r.ai && r.ai.band ? r.ai.band : ''
    });
  }
}
fs.mkdirSync(path.dirname(opt.out), { recursive: true });
fs.writeFileSync(opt.out, toCsv(rows, ['id', 'corpus', 'file', 'checker_label', 'checker_sha256', 'words', 'd1', 'd2', 'd3', 'd4', 'fails', 'flagged', 'ai_score', 'ai_band']));
console.log('checker', opt.label || '', hash.slice(0, 12), 'articles', rows.length, '->', opt.out);

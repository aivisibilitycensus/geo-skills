// VS-001 step 3: build the AI-article prompts from the accepted human articles. One prompt per title,
// exactly the Appendix B wording, with the word count rounded to the nearest 100. Writes
// data/prompts.csv (id, title, words, prompt). Whatever model or route generates the articles reads this
// file and writes data/ai/<model>/<id>.md with the unedited output; nothing else is passed to the model.
//
//   node prompts.mjs [--human data/human] [--out data/prompts.csv]

import fs from 'node:fs';
import path from 'node:path';
import { parseCsv, toCsv } from './lib.mjs';

const args = Object.fromEntries(process.argv.slice(2).map((a, i, all) => a.startsWith('--') ? [a.slice(2), all[i + 1]] : []).filter(x => x.length));
const humanDir = args.human || 'data/human';
const out = args.out || 'data/prompts.csv';
const manifest = parseCsv(fs.readFileSync(path.join(humanDir, 'manifest.csv'), 'utf8')).filter(r => r.outcome === 'accepted');

const rows = manifest.map(r => {
  const words = Math.max(100, Math.round(Number(r.words) / 100) * 100);
  return {
    id: r.id, title: r.title, words,
    prompt: `Write a blog article for a business website titled "${r.title}". Write about ${words} words. Use subheadings. Write for the company's prospective customers.`
  };
});
fs.writeFileSync(out, toCsv(rows, ['id', 'title', 'words', 'prompt']));
console.log('prompts', rows.length, '->', out);

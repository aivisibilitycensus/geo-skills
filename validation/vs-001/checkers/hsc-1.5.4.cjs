/*!
 * Content Shape Checker 1.5.1
 * AI Visibility Census, https://aivisibilitycensus.com/
 * Runs entirely in the visitor's browser. No text is sent anywhere.
 * License: GPL-2.0-or-later
 */
(function (root) {
  'use strict';

  /* ------------------------------------------------------------------ */
  /* Word lists                                                          */
  /* ------------------------------------------------------------------ */

  // Dimension 1: phrases that explain what the reader has just seen.
  var OVER_EXPLAIN = [
    'in other words', 'what this means is', 'what this means', 'the point is', 'put simply',
    'simply put', 'essentially', 'this matters because', 'why this matters', 'the key takeaway',
    'key takeaway', 'in short', 'in summary', 'to summarize', 'to sum up', 'in essence',
    'the bottom line', 'this shows that', 'this means that', 'which means that',
    "it's worth noting", 'it is worth noting', 'it is important to note', "it's important to note",
    'needless to say', 'as mentioned', 'as we have seen', "as we've seen", 'to put it another way',
    'the takeaway', 'all in all', 'at the end of the day'
  ];

  // Sentence starts that interpret a statistic, table or example just given.
  var RESTATE_START = /^(?:this|that|these(?: numbers| figures| results)?|the (?:data|numbers|figures|results)|which|it)\s+(?:means|shows|tells us|tells|suggests|proves|demonstrates|highlights|underscores|matters|illustrates|confirms|is why|is because|reveals)\b/i;

  // Section-closing summaries.
  var SUMMARY_START = /^(?:ultimately|overall|in short|in summary|to summarize|to sum up|the bottom line|all in all|in conclusion)\b/i;

  // Dimension 2: placeless category language.
  var VAGUE = [
    'a range of', 'a wide range of', 'a broad range of', 'a variety of', 'a wide variety of', 'various',
    'numerous', 'countless', 'many organizations', 'many organisations', 'many companies', 'many businesses',
    'companies today', 'businesses today', 'organizations today', 'some teams', 'modern teams',
    'organizations of all sizes', 'organisations of all sizes', 'businesses of all sizes', 'teams of all sizes',
    "today's workplace", "today's world", "in today's", 'the modern workplace', 'the modern world',
    'a popular', 'a leading', 'leading provider', 'industry-leading', 'world-class', 'innovative',
    'across industries', 'across various industries', 'across a range of industries', 'key stakeholders',
    'ever-evolving', 'ever-changing', 'fast-paced', 'digital age', 'in an era of', 'next generation of'
  ];

  // Vague-intensity adjectives. Not scored since v1.5 (human writers in our test used them more); kept for reference.
  var INTENSITY = [
    'powerful', 'seamless', 'seamlessly', 'robust', 'comprehensive', 'cutting-edge', 'game-changing',
    'game changer', 'game-changer', 'transformative', 'revolutionary', 'revolutionize', 'revolutionise',
    'effortless', 'effortlessly', 'intuitive', 'unparalleled', 'best-in-class', 'state-of-the-art',
    'next-level', 'unlock', 'unlocks', 'unlocking', 'unleash', 'unleashes', 'elevate', 'elevates',
    'empower', 'empowers', 'empowering', 'supercharge', 'supercharges', 'harness', 'holistic',
    'groundbreaking', 'unprecedented', 'unmatched', 'unrivaled', 'unrivalled', 'world-class',
    'truly', 'incredibly', 'remarkably'
  ];

  var ESCALATOR = /\b(?:not just|not only|isn't just|is not just|aren't just|are not just|wasn't just|more than just|isn't merely|is not merely|not merely|not simply|isn't simply)\b|\b(?:isn't|is not|aren't|are not)\s+(?:a|an|the)?\s*[\w-]+(?:\s[\w-]+)?\s*[,;]\s*(?:it's|it is|they're|they are)\b/gi;

  // v1.5 (tested 2026-10-29 on 170 business documents plus the Ghostbuster news and essay sets; see methodology).
  // Negative parallelism, all three forms: "not just X, but Y", "Y, not X", "Y rather than X".
  var NEG_PARALLEL = /\b(?:not just|not only|not merely|not simply|more than just|isn't just|is not just|aren't just|are not just)\b|\brather than\b|,\s+not\s+(?:a |an |the |just |only |because )?[a-z][\w-]*/gi;
  // Stock vocabulary in two lists (Wikipedia, Signs of AI writing). In our tests the 2023 GPT-3.5 and Claude texts leaned on
  // the first; the 2026 Claude texts had dropped most of it and leaned on the second, which reads as plain English.
  var STOCK_OLD = [
    'landscape', 'highlighting', 'highlights', 'leverage', 'leverages', 'leveraging',
    'streamline', 'streamlines', 'streamlining', 'streamlined', 'innovative', 'sustainable', 'comprehensive', 'crucial',
    'enhance', 'enhances', 'enhancing', 'enhanced', 'foster', 'fosters', 'fostering', 'fostered', 'pivotal', 'testament',
    'underscore', 'underscores', 'underscoring', 'showcase', 'showcases', 'showcasing', 'seamless', 'seamlessly', 'robust',
    'delve', 'delves', 'delving', 'vibrant', 'multifaceted', 'nuanced', 'holistic', 'transformative', 'empowering', 'thrive',
    'resonate', 'resonates', 'resonating', "in today's", 'cutting-edge', 'tapestry', 'intricate', 'meticulous', 'meticulously',
    'realm', 'embark', 'invaluable', 'game-changer', 'ever-evolving', 'plays a crucial role', 'plays a key role',
    'plays a vital role', 'plays a pivotal role', 'plays a significant role', 'serves as', 'stands as', 'a testament to'
  ];
  var STOCK_NEW = [
    'quietly', 'steady', 'dependable', 'clearer', 'matters', 'practical', 'universally', 'echoed', 'challenge',
    'prioritize', 'prioritise'
  ];
  // Sentence starters that bolt sentences together.
  // (Closing words such as "Ultimately" and "Overall" are counted once, under over-explanation.)
  var FORMULA_START = /^(?:additionally|moreover|furthermore|notably|importantly|crucially)\b/i;
  // Sentences that announce the point instead of making it.
  var POINT_START = /^(?:the (?:lesson|takeaway|point|key|difference|result|upshot) (?:is|was|here is)\b|here(?:'s| is) (?:the (?:thing|point|lesson|takeaway)|why|what (?:this|that) means))/i;
  // Participle tack-ons: a trailing clause that announces what something means.
  var TACK_ON = /,\s+(?:highlighting|underscoring|emphasizing|emphasising|ensuring|reflecting|symbolizing|symbolising|contributing to|cultivating|fostering|encompassing|enhancing|aligning with|resonating with|showcasing|solidifying|cementing|signaling|signalling|demonstrating|illustrating|paving the way|setting the stage|marking)\b[^.?!]*/gi;
  // Significance and legacy claims.
  var SIGNIFICANCE = [
    'stands as', 'serves as', 'is a testament to', 'is a reminder of', 'plays a crucial role', 'plays a pivotal role',
    'plays a vital role', 'plays a key role', 'plays a significant role', 'a crucial role', 'a pivotal role', 'a vital role',
    'key moment', 'underscores the importance', 'underscores its importance', 'highlights the importance',
    'highlights its significance', 'reflects broader', 'setting the stage for', 'represents a shift', 'marks a shift',
    'key turning point', 'evolving landscape', 'focal point', 'indelible mark', 'deeply rooted', 'this matters because',
    'why this matters', 'why it matters', 'this distinction matters'
  ];
  // Thresholds, calibrated on the training half of the test set (see CAL notes in the methodology).
  var CAL = {
    d1: { pass: 1, fail: 3 },
    d3: {
      mu: { sentSD: 8.68, longShare: 0.09, paraCV: 0.52, secCV: 0.64, asides: 8.55, triples: 3.17 },
      sd: { sentSD: 2.21, longShare: 0.07, paraCV: 0.13, secCV: 0.30, asides: 7.10, triples: 2.60 },
      flagZ: 1, pass: 0.35, fail: 0.75
    },
    d4: { pass: 3, fail: 6 }
  };

  var ANTI_A = /^(?:it|this|that|they|the \w+)\s+(?:isn't|is not|wasn't|was not|aren't|are not)\b/i;
  var ANTI_B = /^(?:it's|it is|it was|this is|that's|that is|they're|they are)\b/i;

  // Words that tend to carry resonance rather than content.
  var ABSTRACT = /\b(?:future|journey|landscape|potential|possibilit(?:y|ies)|success|growth|value|impact|transform\w*|world|era|power|innovation|excellence|meaningful|ultimately|truly|vision|mission|thrive|thriving|matters|essential|crucial|vital|key|today|tomorrow|game|revolution\w*|competitive edge|ahead of the curve|next level|new heights|endless|limitless|unlock\w*|elevat\w*|empower\w*|strategic|holistic|synerg\w*)\b/i;

  var IMPERATIVE = ('add ask avoid book build call change check choose click compare copy count create cut delete download drop ' +
    'email enter export find fix follow get give go install keep list look make map measure move note open paste pick plan ' +
    'publish pull put read remove replace run save search send set share sign skip start stop swap take tell test track try ' +
    'turn update upload use watch write type press select tap drag connect ship hire fire budget').split(' ');
  var IMPERATIVE_SET = {};
  IMPERATIVE.forEach(function (w) { IMPERATIVE_SET[w] = true; });

  var SPELLED_NUM = /\b(?:two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|hundred|thousand|million|billion|dozen|half|quarter)\b/gi;
  var DIGIT_NUM = /[$€£¥]?\d[\d,.:]*\s?(?:%|k|m|bn|x)?/gi;

  var GENERIC_PLURAL = /\b(organi[sz]ations|businesses|companies|teams|users|employees|customers|brands|marketers|leaders|professionals|enterprises|stakeholders)\b/gi;
  var YOU = /\b(?:you|your|yours|yourself|you're|you've|you'll)\b/gi;

  var SURFACE = [
    'delve', 'delves', 'tapestry', 'testament to', 'realm', 'navigate the', 'navigating the', "here's the thing",
    'in the realm of', 'a myriad of', 'myriad', 'embark', 'it is crucial', "let's dive in", 'dive into', 'deep dive'
  ];

  // AI-style signals: stock vocabulary, framing and sign-posting that generated text over-uses.
  var AI_VOCAB = [
    'delve', 'delves', 'delving', 'tapestry', 'testament to', 'realm', 'in the realm of', 'navigate the', 'navigating the',
    'landscape', 'seamless', 'seamlessly', 'robust', 'leverage', 'leveraging', 'unlock', 'unlocks', 'unlocking', 'elevate',
    'elevates', 'empower', 'empowers', 'empowering', 'crucial', 'pivotal', 'foster', 'fosters', 'fostering', 'harness',
    'harnessing', 'intricate', 'multifaceted', 'ever-evolving', 'ever-changing', 'game-changer', 'game changer', 'cutting-edge',
    'streamline', 'streamlines', 'synergy', 'holistic', 'paradigm', 'bustling', 'vibrant', 'embark', 'underscores',
    'underscore', 'showcase', 'showcases', 'boasts', 'meticulous', 'meticulously', 'nuanced', 'transformative',
    'revolutionize', 'revolutionise', 'unparalleled', 'myriad', 'a myriad of', 'plethora', 'dive into', 'deep dive',
    'at its core', 'in essence', 'treasure trove', 'resonate', 'resonates', 'commendable', 'invaluable', 'paramount'
  ];
  var AI_FRAME = [
    "in today's", 'in the ever', 'in an era', 'in conclusion', 'when it comes to', "whether you're", 'whether you are',
    'look no further', 'the future of', 'stands out as', 'plays a crucial role', 'plays a vital role', 'plays a key role',
    'a key role', 'the world of', 'unlock the full potential', 'to the next level', 'in the digital age',
    'are you looking to', 'have you ever wondered'
  ];
  var AI_SIGNPOST = [
    "it's worth noting", 'it is worth noting', "it's important to note", 'it is important to note', "it's important to",
    'it is important to', "let's dive", "let's explore", "let's take a look", "here's the thing",
    'comes into play', 'without further ado', 'buckle up', 'rest assured', 'needless to say',
    'first and foremost', 'last but not least'
  ];

  // Fitted logistic model (v1, 2026-10-29). Trained on 32 pre-2022 human company blog posts, 32 pre-2022 human
  // handbook and guide pages, and 32 AI posts written on matching titles by Claude Haiku and Claude Sonnet (tested on Claude Opus and Sonnet). Em dashes are
  // excluded because the AI training posts contained none. Held-out results: High caught 18 of 26 AI texts and
  // 2 of 48 human texts. See the methodology section on the page.
  var AI_MODEL = {
    f: ['parens',  'density',  'longSent',  'sentMean',  'secCV',  'paraCV',  'colons',  'contractions'],
    mu: [0.3734,  4.1603,  0.0625,  15.6686,  0.5309,  0.5266,  0.6496,  1.7354],
    sd: [0.5529,  2.8951,  0.0651,  2.5828,  0.265,  0.1842,  0.9462,  1.3057],
    w: [-0.1859,  -0.2373,  -0.203,  -0.2281,  -0.2165,  -0.1961,  -0.1243,  -0.1616],
    b: -0.8375,
    human: [0.5574,  5.4096,  0.0873,  16.6794,  0.6301,  0.5936,  0.8707,  2.0856],
    high: 0.4,
    medium: 0.3
  };
  var AI_FEAT_LABEL = {
    parens: ['Parenthetical asides', 'per 100 words', 2],
    density: ['Names and numbers', 'per 100 words', 1],
    longSent: ['Long sentences (30+ words)', 'share', 'pct'],
    sentMean: ['Average sentence length', 'words', 1],
    secCV: ['Variety in section length', 'variation', 2],
    paraCV: ['Variety in paragraph length', 'variation', 2],
    colons: ['Colons', 'per 100 words', 2],
    contractions: ['Contractions ("it\'s", "don\'t")', 'per 100 words', 1],
    shortSent: ['Short sentences (8 words or fewer)', 'share', 'pct'],
    bullets: ['Words in bullet lists', 'share', 'pct'],
    emPer1k: ['Em dashes', 'per 1,000 words', 1],
    iPer100: ['First person singular ("I", "my")', 'per 100 words', 2]
  };
  function aiModelScore(feats) {
    var z = AI_MODEL.b, contrib = [];
    AI_MODEL.f.forEach(function (k, i) {
      var v = feats[k], zz = Math.max(-4, Math.min(4, (v - AI_MODEL.mu[i]) / AI_MODEL.sd[i]));
      var c = AI_MODEL.w[i] * zz; z += c;
      var hm = AI_MODEL.human[i];
      contrib.push({ k: k, value: v, typical: hm, c: c, higher: v > hm, consistent: (v - hm) * (v - AI_MODEL.mu[i]) > 0 || Math.abs(v - hm) < 1e-9 });
    });
    return { p: 1 / (1 + Math.exp(-z)), contrib: contrib };
  }

  var STOP_CAPS = { 'I': 1, "I'm": 1, "I've": 1, "I'd": 1, "I'll": 1, 'A': 1, 'An': 1, 'The': 1, 'OK': 0 };

  /* ------------------------------------------------------------------ */
  /* Helpers                                                             */
  /* ------------------------------------------------------------------ */

  function escHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function reEsc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
  function listRe(list) {
    var l = list.slice().sort(function (a, b) { return b.length - a.length; });
    var body = l.map(function (p) { return reEsc(p).replace(/'/g, "['\u2019]"); }).join('|');
    return new RegExp('(^|[^A-Za-z0-9\u2019\'-])(' + body + ')(?=$|[^A-Za-z0-9-])', 'gi');
  }
  var OVER_RE = listRe(OVER_EXPLAIN);
  var VAGUE_RE = listRe(VAGUE);
  var INTENSITY_RE = listRe(INTENSITY);
  var SURFACE_RE = listRe(SURFACE);
  var STOCK_OLD_RE = listRe(STOCK_OLD);
  var STOCK_NEW_RE = listRe(STOCK_NEW);
  var SIGNIFICANCE_RE = listRe(SIGNIFICANCE);
  var AI_VOCAB_RE = listRe(AI_VOCAB);
  var AI_FRAME_RE = listRe(AI_FRAME);
  var AI_SIGNPOST_RE = listRe(AI_SIGNPOST);

  function findList(re, text) {
    var out = [], m;
    re.lastIndex = 0;
    while ((m = re.exec(text)) !== null) {
      var s = m.index + m[1].length;
      out.push({ start: s, end: s + m[2].length, match: m[2] });
      if (re.lastIndex === m.index) re.lastIndex++;
    }
    return out;
  }
  function findRe(re, text) {
    var out = [], m;
    re.lastIndex = 0;
    while ((m = re.exec(text)) !== null) {
      out.push({ start: m.index, end: m.index + m[0].length, match: m[0] });
      if (re.lastIndex === m.index) re.lastIndex++;
    }
    return out;
  }
  function quotedRanges(text) {
    var out = [], m, re = /"[^"]{1,240}"/g;
    while ((m = re.exec(text)) !== null) out.push([m.index, m.index + m[0].length]);
    return out;
  }
  function unquoted(hits, text) {
    var q = quotedRanges(text);
    if (!q.length) return hits;
    return hits.filter(function (h) {
      for (var i = 0; i < q.length; i++) if (h.start >= q[i][0] && h.end <= q[i][1]) return false;
      return true;
    });
  }
  function norm(t) { return t.replace(/[\u2018\u2019]/g, "'").replace(/[\u201C\u201D]/g, '"'); }
  function wordCount(t) {
    var w = t.trim().split(/\s+/);
    var n = 0;
    for (var i = 0; i < w.length; i++) if (/[A-Za-z0-9]/.test(w[i])) n++;
    return n;
  }
  function mean(a) { if (!a.length) return 0; var s = 0; for (var i = 0; i < a.length; i++) s += a[i]; return s / a.length; }
  function median(a) {
    if (!a.length) return 0;
    var b = a.slice().sort(function (x, y) { return x - y; });
    var m = Math.floor(b.length / 2);
    return b.length % 2 ? b[m] : (b[m - 1] + b[m]) / 2;
  }
  function sd(a) {
    if (a.length < 2) return 0;
    var m = mean(a), s = 0;
    for (var i = 0; i < a.length; i++) s += (a[i] - m) * (a[i] - m);
    return Math.sqrt(s / (a.length - 1));
  }
  function round(n, d) { var p = Math.pow(10, d || 0); return Math.round(n * p) / p; }
  function per1k(n, words) { return words ? (n * 1000) / words : 0; }
  function stripMd(t) {
    return t.replace(/!\[[^\]]*\]\([^)]*\)/g, '')
      .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1\u2060')
      .replace(/(\*\*|__)(.*?)\1/g, '$2')
      .replace(/(\*|_)(.*?)\1/g, '$2')
      .replace(/`([^`]*)`/g, '$1')
      .replace(/^>\s?/, '')
      .trim();
  }
  function truncate(t, n) { return t.length > n ? t.slice(0, n - 1).replace(/\s+\S*$/, '') + '\u2026' : t; }

  /* ------------------------------------------------------------------ */
  /* Parsing                                                             */
  /* ------------------------------------------------------------------ */

  var ABBR = /\b(?:e\.g|i\.e|etc|vs|approx|Mr|Mrs|Ms|Dr|Prof|Inc|Ltd|Co|St|No|Fig|U\.S|U\.K|a\.m|p\.m|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\./g;

  function splitSentences(t) {
    var p = t.replace(ABBR, function (m) { return m.replace(/\./g, '\u0001'); });
    var parts = p.split(/(?<=[.!?\u2026]["\u201D\u2019)\]]?)\s+(?=["\u201C\u2018(\[]?[A-Z0-9$€£])/);
    var out = [];
    for (var i = 0; i < parts.length; i++) {
      var s = parts[i].replace(/\u0001/g, '.').trim();
      if (s) out.push(s);
    }
    return out;
  }

  function isHeadingLike(t) {
    var w = t.split(/\s+/).length;
    return w <= 12 && t.length < 100 && !/[.!,;:]$/.test(t) && /^["\u201C]?[A-Z0-9]/.test(t);
  }

  function parseText(raw) {
    var lines = String(raw).replace(/\r\n?/g, '\n').split('\n');
    var blocks = [], buf = [], bufLink = false;
    var LINK = /\]\([^)\s]+\)|https?:\/\/|www\./;
    function flush() { if (buf.length) { blocks.push({ type: 'para', text: buf.join(' '), hasLink: bufLink }); buf = []; bufLink = false; } }
    for (var i = 0; i < lines.length; i++) {
      var tr = lines[i].trim();
      if (!tr) { flush(); continue; }
      var h = tr.match(/^(#{1,6})\s+(.*)$/);
      if (h) { flush(); blocks.push({ type: 'heading', level: h[1].length, text: stripMd(h[2]) }); continue; }
      var lineLink = LINK.test(tr);
      var b = tr.match(/^(?:[-*+\u2022\u25CF\u25AA\u2013]|\d{1,3}[.)])\s+(.*)$/);
      if (b) { flush(); blocks.push({ type: 'bullet', text: stripMd(b[1]), hasLink: lineLink }); continue; }
      if (/^\|.*\|$/.test(tr)) {
        flush();
        if (!/^\|[\s:|-]+\|$/.test(tr)) blocks.push({ type: 'table', text: stripMd(tr.replace(/^\||\|$/g, '').split('|').map(function (c) { return c.trim(); }).join(' | ')), hasLink: lineLink });
        continue;
      }
      var prevBlank = i === 0 || !lines[i - 1].trim();
      var nextBlank = i === lines.length - 1 || !lines[i + 1].trim();
      if (prevBlank && nextBlank && isHeadingLike(tr) && buf.length === 0) {
        blocks.push({ type: 'heading', level: 2, text: stripMd(tr) });
        continue;
      }
      buf.push(stripMd(tr)); if (lineLink) bufLink = true;
    }
    flush();
    return blocks;
  }

  function parseHTML(html) {
    var doc = new DOMParser().parseFromString(html, 'text/html');
    Array.prototype.forEach.call(doc.querySelectorAll('script,style,noscript,nav,footer,form,svg,iframe'), function (n) { n.remove(); });
    Array.prototype.forEach.call(doc.querySelectorAll('a[href]'), function (a) { if (/^(?:https?:|www\.)/i.test(a.getAttribute('href') || '') && a.textContent.trim()) a.appendChild(doc.createTextNode('\u2060')); });
    var rootEl = doc.querySelector('article') || doc.querySelector('main') || doc.body;
    var blocks = [];
    function push(type, text, level) {
      text = (text || '').replace(/\s+/g, ' ').trim();
      if (text) blocks.push({ type: type, text: text, level: level || 0 });
    }
    function linked(el) {
      var clone = el.cloneNode(true);
      Array.prototype.forEach.call(clone.querySelectorAll('a[href]'), function (a) {
        var href = a.getAttribute('href') || '';
        if (/^(https?:|www\.|\/)/i.test(href) && a.textContent.trim()) a.replaceWith(doc.createTextNode('[' + a.textContent.trim() + '](' + href.replace(/\s/g, '') + ')'));
      });
      return clone;
    }
    var BLOCKY = 'p,h1,h2,h3,h4,h5,h6,li,div,tr,section,article,blockquote,ul,ol,table,pre';
    function walk(node) {
      for (var c = node.firstElementChild; c; c = c.nextElementSibling) {
        var tag = c.tagName.toLowerCase();
        if (/^h[1-6]$/.test(tag)) push('heading', c.textContent, +tag.charAt(1));
        else if (tag === 'li') {
          var clone = linked(c);
          Array.prototype.forEach.call(clone.querySelectorAll('ul,ol'), function (x) { x.remove(); });
          push('bullet', clone.textContent);
          Array.prototype.forEach.call(c.children, function (k) { if (/^(ul|ol)$/i.test(k.tagName)) walk(k); });
        }
        else if (tag === 'tr') push('table', Array.prototype.map.call(c.children, function (x) { return linked(x).textContent.trim(); }).join(' | '));
        else if (tag === 'p' || tag === 'pre' || (tag === 'blockquote' && !c.querySelector('p'))) push('para', linked(c).textContent);
        else if (c.querySelector(BLOCKY)) walk(c);
        else if (c.textContent.trim()) push('para', c.textContent);
      }
    }
    walk(rootEl);
    if (!blocks.length) return parseText(rootEl.textContent || '');
    return blocks;
  }

  // Minimal .docx reader: finds word/document.xml in the zip and inflates it in the browser.
  function unzipEntry(buf, name) {
    var dv = new DataView(buf), u8 = new Uint8Array(buf), dec = new TextDecoder('utf-8');
    var eocd = -1;
    for (var i = buf.byteLength - 22; i >= Math.max(0, buf.byteLength - 65557); i--) {
      if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
    }
    if (eocd < 0) return Promise.reject(new Error('That file does not look like a valid .docx.'));
    var count = dv.getUint16(eocd + 10, true), p = dv.getUint32(eocd + 16, true);
    for (var n = 0; n < count; n++) {
      if (dv.getUint32(p, true) !== 0x02014b50) break;
      var method = dv.getUint16(p + 10, true), csize = dv.getUint32(p + 20, true);
      var nlen = dv.getUint16(p + 28, true), elen = dv.getUint16(p + 30, true), clen = dv.getUint16(p + 32, true);
      var loff = dv.getUint32(p + 42, true);
      var fname = dec.decode(u8.subarray(p + 46, p + 46 + nlen));
      if (fname === name) {
        var start = loff + 30 + dv.getUint16(loff + 26, true) + dv.getUint16(loff + 28, true);
        var data = u8.subarray(start, start + csize);
        if (method === 0) return Promise.resolve(dec.decode(data));
        if (method === 8) {
          if (typeof DecompressionStream === 'undefined') return Promise.reject(new Error('This browser cannot open .docx files. Paste the text instead.'));
          var stream = new Blob([data]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
          return new Response(stream).text();
        }
        return Promise.reject(new Error('Unsupported compression in this .docx.'));
      }
      p += 46 + nlen + elen + clen;
    }
    return Promise.reject(new Error('No document text found in that file.'));
  }

  function parseDocxXml(xml) {
    var doc = new DOMParser().parseFromString(xml, 'application/xml');
    var ps = doc.getElementsByTagName('w:p');
    var blocks = [];
    for (var i = 0; i < ps.length; i++) {
      var p = ps[i], text = '';
      var all = p.getElementsByTagName('*');
      for (var j = 0; j < all.length; j++) {
        var nn = all[j].nodeName;
        if (nn === 'w:t') { var inLink = false; for (var q = all[j].parentNode; q && q !== p; q = q.parentNode) { if (q.nodeName === 'w:hyperlink') { inLink = true; break; } } text += inLink ? '\u0002' + all[j].textContent + '\u0003' : all[j].textContent; }
        else if (nn === 'w:tab' || nn === 'w:br') text += ' ';
      }
      text = text.replace(/\u0003\u0002/g, '').replace(/\u0002([^\u0003]*)\u0003/g, '[$1](docx-link)').replace(/[\u0002\u0003]/g, '').replace(/\s+/g, ' ').trim();
      if (!text) continue;
      var styleEl = p.getElementsByTagName('w:pStyle')[0];
      var style = styleEl ? (styleEl.getAttribute('w:val') || '') : '';
      var hm = style.match(/heading\s?(\d)/i);
      var inTable = false;
      for (var a = p.parentNode; a; a = a.parentNode) { if (a.nodeName === 'w:tc') { inTable = true; break; } }
      if (hm) blocks.push({ type: 'heading', level: +hm[1], text: text });
      else if (/^title$/i.test(style)) blocks.push({ type: 'heading', level: 1, text: text });
      else if (inTable) blocks.push({ type: 'table', text: text });
      else if (p.getElementsByTagName('w:numPr').length || /list/i.test(style)) blocks.push({ type: 'bullet', text: text });
      else blocks.push({ type: 'para', text: text });
    }
    return blocks;
  }

  /* ------------------------------------------------------------------ */
  /* Sentence features                                                   */
  /* ------------------------------------------------------------------ */

  function properNounCount(s) {
    var toks = s.split(/\s+/), n = 0, names = [];
    for (var i = 0; i < toks.length; i++) {
      var raw = toks[i];
      var t = raw.replace(/^[("\u201C\u2018'[]+|[)"\u201D\u2019'\].,;:!?]+$/g, '');
      if (!t || STOP_CAPS[t]) continue;
      var acronym = /^[A-Z][A-Z0-9&]{1,}s?$/.test(t);
      var camel = /^[A-Za-z]+[A-Z][a-z]/.test(t) || /^[a-z]+[A-Z]/.test(t);
      var cap = /^[A-Z][a-z0-9'\u2019&.-]+$/.test(t);
      var prev = i > 0 ? toks[i - 1] : '';
      var startish = i === 0 || /[:.!?]$/.test(prev) || /^[-\u2013\u2014]$/.test(prev);
      if (acronym || camel || (cap && !startish)) { n++; names.push(t); }
    }
    return { count: n, names: names };
  }

  function numberCount(s) {
    var d = (s.match(DIGIT_NUM) || []).length;
    var w = (s.match(SPELLED_NUM) || []).length;
    return d + w;
  }

  function firstWord(s) {
    var m = s.match(/^["\u201C(]*([A-Za-z']+)/);
    return m ? m[1].toLowerCase() : '';
  }

  /* ------------------------------------------------------------------ */
  /* Analysis                                                            */
  /* ------------------------------------------------------------------ */

  function classifyOpener(s) {
    var t = norm(s);
    if (/\?["')]*$/.test(t)) return 'question';
    var firstSix = t.split(/\s+/).slice(0, 6).join(' ');
    SPELLED_NUM.lastIndex = 0;
    if (/^\W*[$€£]?\d/.test(t) || /\d/.test(firstSix) || SPELLED_NUM.test(firstSix)) { SPELLED_NUM.lastIndex = 0; return 'number'; }
    SPELLED_NUM.lastIndex = 0;
    if (/^(?:for example|for instance|take |consider |imagine |picture |last (?:week|month|year|quarter)|when |in (?:19|20)\d\d|one (?:customer|client|team))/i.test(t) ||
        /\b(?:on (?:a )?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|yesterday|this morning|last (?:week|month|year|quarter)|(?:in|on|at) (?:january|february|march|april|may|june|july|august|september|october|november|december))\b/i.test(t)) return 'scenario';
    if (/^(?:[\w-]+\s){0,5}(?:is|are) (?:a|an|the)\b|\brefers to\b|\bis defined as\b/i.test(t)) return 'definition';
    if (IMPERATIVE_SET[firstWord(t)]) return 'instruction';
    if (/\byou(?:r)?\b/i.test(t)) return 'direct address';
    var first = (t.match(/^["“(]*([^\s,.;:]+)/) || [])[1] || '';
    if (/^[A-Z][A-Z0-9&]{1,}s?$/.test(first) || /^[A-Za-z]+[A-Z][a-z]/.test(first) || properNounCount(s).count > 0) return 'named fact';
    return 'claim';
  }

  function classifyCloser(s) {
    var t = norm(s);
    if (SUMMARY_START.test(t)) return 'summary';
    if (/\?["')]*$/.test(t)) return 'question';
    if (/\b(?:contact us|book a|get started|sign up|start your|try it|learn more|download|request a demo|talk to)\b/i.test(t)) return 'call to action';
    return 'statement';
  }

  function verdict(level) { return ['PASS', 'PASS WITH NOTES', 'FAIL'][level]; }

  function analyze(inputBlocks) {
    var blocks = [];
    inputBlocks.forEach(function (b) {
      var text = (b.text || '').replace(/\s+/g, ' ').trim();
      if (text && /[A-Za-z0-9]/.test(text)) blocks.push({ type: b.type, level: b.level || 0, text: text, hasLink: !!b.hasLink || /\]\([^)\s]+\)|https?:\/\//.test(text) });
    });

    var subHeadings = 0;
    blocks.forEach(function (b, i) { if (b.type === 'heading' && i > 0) subHeadings++; });
    var mode = subHeadings >= 2 ? 'headings' : 'paragraphs';

    // Build sections.
    var sections = [], cur = null;
    function newSection(heading) { cur = { heading: heading || null, blocks: [] }; sections.push(cur); }
    blocks.forEach(function (b) {
      if (b.type === 'heading') { newSection(b.text); return; }
      if (mode === 'paragraphs' && b.type === 'para' && (!cur || cur.blocks.length)) {
        if (!cur || cur.blocks.length) newSection(cur && !cur.blocks.length ? cur.heading : null);
      }
      if (!cur) newSection(null);
      cur.blocks.push(b);
    });
    sections = sections.filter(function (s) { return s.blocks.length; });

    // Sentences.
    var sentences = [], totalWords = 0, bulletWords = 0, tableBlocks = 0;
    sections.forEach(function (sec, si) {
      sec.index = si;
      sec.sentences = [];
      sec.words = 0;
      sec.paras = 0;
      sec.bullets = 0;
      sec.anchors = 0;
      sec.blocks.forEach(function (b, bi) {
        var wc = wordCount(b.text);
        sec.words += wc;
        totalWords += wc;
        if (b.type === 'bullet') { bulletWords += wc; sec.bullets++; }
        if (b.type === 'para') sec.paras++;
        var parts = b.type === 'table' ? [b.text] : splitSentences(b.text);
        if (b.type === 'table') tableBlocks++;
        b.sentences = [];
        parts.forEach(function (st, k) {
          var linkMark = /\u2060/.test(st);
          st = st.replace(/\u2060/g, '');
          var nt = norm(st);
          var pn = properNounCount(st);
          var o = {
            id: sentences.length, text: st, ntext: nt, sec: si, block: bi, blockType: b.type,
            first: k === 0, words: wordCount(st), hasDigit: /\d/.test(st),
            numbers: numberCount(st), proper: pn.count, properNames: pn.names,
            imperative: !!IMPERATIVE_SET[firstWord(nt)], marks: [], flags: [], linkMark: linkMark
          };
          o.anchors = o.numbers + o.proper;
          sec.anchors += o.anchors;
          sentences.push(o);
          sec.sentences.push(o);
          b.sentences.push(o);
        });
      });
    });

    function mark(s, start, end, dim, label) { s.marks.push({ start: start, end: end, dim: dim, label: label }); }
    function flag(s, dim, label) { s.flags.push({ dim: dim, label: label }); }

    /* ---------------- Dimension 1: over-explanation ---------------- */
    // v1.5: what separated AI from human text in testing was narration of meaning (trailing "..., highlighting X"
    // clauses, significance claims, closing summaries), not phrases like "in other words", which human writers use as often.
    var d1 = { phraseHits: [], tackOns: [], significance: [], restatements: [], summaries: [] };
    sentences.forEach(function (s, i) {
      if (s.blockType === 'table') return;
      unquoted(findRe(TACK_ON, s.ntext), s.ntext).forEach(function (h) {
        mark(s, h.start, h.end, 1, 'Narrates what it means');
        d1.tackOns.push({ s: s, match: h.match.replace(/^,\s*/, '').split(/\s+/).slice(0, 2).join(' ').toLowerCase() });
      });
      if (s.blockType === 'para' && POINT_START.test(s.ntext)) {
        var pm = s.ntext.match(POINT_START)[0];
        mark(s, 0, pm.length, 1, 'Announces the point');
        d1.significance.push({ s: s, match: pm.toLowerCase() });
      }
      unquoted(findList(SIGNIFICANCE_RE, s.ntext), s.ntext).forEach(function (h) {
        mark(s, h.start, h.end, 1, 'Significance claim');
        d1.significance.push({ s: s, match: h.match.toLowerCase() });
      });
      var prev = i > 0 ? sentences[i - 1] : null;
      if (prev && prev.sec === s.sec && (prev.hasDigit || prev.blockType === 'table' || prev.blockType === 'bullet') && RESTATE_START.test(s.ntext)) {
        flag(s, 1, 'Interprets the evidence just given');
        d1.restatements.push(s);
      }
    });
    sections.forEach(function (sec) {
      var ss = sec.sentences.filter(function (x) { return x.blockType !== 'table'; });
      if (ss.length >= 3) {
        var last = ss[ss.length - 1];
        if (SUMMARY_START.test(last.ntext)) { flag(last, 1, 'Section-closing summary'); d1.summaries.push(last); }
      }
    });
    var d1Sentences = sentences.filter(function (s) {
      return s.marks.some(function (m) { return m.dim === 1; }) || s.flags.some(function (f) { return f.dim === 1; });
    });
    d1.phraseHits = d1.tackOns.concat(d1.significance);
    d1.strikes = d1Sentences.length;
    d1.rate = per1k(d1.strikes, totalWords);
    d1.level = d1.rate <= CAL.d1.pass ? 0 : d1.rate <= CAL.d1.fail ? 1 : 2;

    /* ---------------- Dimension 2: real things, named ---------------- */
    var d2 = { vagueHits: [], zeroSections: [] };
    var anchorTotal = 0;
    sentences.forEach(function (s) {
      anchorTotal += s.anchors;
      unquoted(findList(VAGUE_RE, s.ntext), s.ntext).forEach(function (h) {
        mark(s, h.start, h.end, 2, 'Category language');
        d2.vagueHits.push({ s: s, match: h.match.toLowerCase() });
      });
    });
    sections.forEach(function (sec) {
      if (sec.words >= 25 && sec.anchors === 0) d2.zeroSections.push(sec);
    });
    var allText = sentences.map(function (s) { return s.ntext; }).join(' ');
    var youCount = (allText.match(YOU) || []).length;
    var genericCount = 0;
    findRe(GENERIC_PLURAL, allText).forEach(function (h) {
      var before = allText.slice(Math.max(0, h.start - 6), h.start).toLowerCase();
      if (!/your\s$/.test(before)) genericCount++;
    });
    var eligibleSections = sections.filter(function (s) { return s.words >= 25; }).length || 1;
    d2.density = totalWords ? (anchorTotal * 100) / totalWords : 0;
    d2.zeroShare = d2.zeroSections.length / eligibleSections;
    d2.vagueRate = per1k(d2.vagueHits.length, totalWords);
    d2.you = youCount;
    d2.generic = genericCount;
    d2.strikes = d2.vagueHits.length + d2.zeroSections.length;
    if (d2.density < 1 || d2.zeroShare > 0.5 || d2.vagueRate > 4) d2.level = 2;
    else if (d2.density >= 2 && d2.zeroShare <= 0.2 && d2.vagueRate <= 1) d2.level = 0;
    else d2.level = 1;

    /* ---------------- Dimension 3: rhythm and variety ---------------- */
    // v1.5: scored on the measures that separated human from AI text in testing: spread of sentence length, share of
    // long sentences, variety in paragraph and section length, asides (parentheses, semicolons, questions) and lists
    // of three. Repeated section openers and heavy bullet use are no longer scored: both were as common in human text.
    var d3 = { flags: [], nested: [], z: {} };
    var openers = {}, sigs = [];
    sections.forEach(function (sec) {
      var ss = sec.sentences.filter(function (x) { return x.blockType !== 'table'; });
      sec.opener = ss.length ? classifyOpener(ss[0].text) : 'none';
      sec.closer = ss.length ? classifyCloser(ss[ss.length - 1].text) : 'none';
      openers[sec.opener] = (openers[sec.opener] || 0) + 1;
      var shape = sec.paras + 'p' + (sec.bullets ? '+list' : '');
      sec.sig = sec.opener + ' / ' + shape + ' / ' + sec.closer;
      sigs.push(sec.sig);
    });
    var nSec = sections.length;
    d3.openers = openers;
    var topOpener = null, topCount = 0;
    Object.keys(openers).forEach(function (k) { if (openers[k] > topCount) { topCount = openers[k]; topOpener = k; } });
    d3.topOpener = topOpener;
    d3.topShare = nSec ? topCount / nSec : 0;
    var runs = [], runStart = 0;
    for (var i = 1; i <= sigs.length; i++) {
      if (i === sigs.length || sigs[i] !== sigs[runStart]) {
        if (i - runStart >= 3) runs.push({ from: runStart, to: i - 1, sig: sigs[runStart] });
        runStart = i;
      }
    }
    d3.runs = runs;

    var secWords = sections.filter(function (s) { return s.words >= 15; }).map(function (s) { return s.words; });
    d3.secCV = secWords.length ? sd(secWords) / (mean(secWords) || 1) : 0;
    var paraSent = sentences.filter(function (s) { return s.blockType === 'para'; });
    var lens = paraSent.map(function (s) { return s.words; });
    d3.sentMean = mean(lens);
    d3.sentMedian = median(lens);
    d3.sentSD = sd(lens);
    d3.sentCV = d3.sentMean ? d3.sentSD / d3.sentMean : 0;
    d3.longShare = lens.length ? lens.filter(function (n) { return n >= 30; }).length / lens.length : 0;
    var paraLens3 = blocks.filter(function (b) { return b.type === 'para'; }).map(function (b) { return wordCount(b.text); }).filter(function (n) { return n >= 5; });
    d3.paraCV = paraLens3.length > 2 ? sd(paraLens3) / (mean(paraLens3) || 1) : null;
    var proseText3 = paraSent.map(function (x) { return x.ntext; }).join(' ');
    var proseWords3 = wordCount(proseText3) || 1;
    d3.asides = ((proseText3.match(/\(/g) || []).length + (proseText3.match(/;/g) || []).length + paraSent.filter(function (x) { return /\?["')]*$/.test(x.ntext); }).length) * 1000 / proseWords3;
    var triadRe3 = /\b[\w'-]+(?: [\w'-]+){0,2}, [\w'-]+(?: [\w'-]+){0,2},? and [\w'-]+\b/g;
    d3.triples = [];
    paraSent.forEach(function (s) { var m = s.ntext.match(triadRe3); if (m) d3.triples.push({ s: s, match: m[0] }); });
    d3.tripleRate = d3.triples.length * 1000 / proseWords3;
    var C3 = CAL.d3;
    function z3(k, v, dir) { if (v === null || v === undefined || !C3.mu[k]) return null; var z = dir * (v - C3.mu[k]) / C3.sd[k]; d3.z[k] = z; return z; }
    var enoughSent = lens.length >= 12;
    var parts3 = [
      enoughSent ? z3('sentSD', d3.sentSD, -1) : null,
      enoughSent ? z3('longShare', d3.longShare, -1) : null,
      z3('paraCV', d3.paraCV, -1),
      secWords.length >= 4 ? z3('secCV', d3.secCV, -1) : null,
      proseWords3 >= 200 ? z3('asides', d3.asides, -1) : null,
      proseWords3 >= 200 ? z3('triples', d3.tripleRate, 1) : null
    ].filter(function (x) { return x !== null; });
    d3.score = parts3.length ? mean(parts3) : 0;
    var T = C3.flagZ || 1;
    if (enoughSent && d3.z.sentSD > T) d3.flags.push({ key: 'rhythm', text: 'Sentence lengths sit in a narrow band (spread ' + round(d3.sentSD, 1) + ' words; human business writing we tested averaged ' + round(C3.mu.sentSD, 1) + ').' });
    if (enoughSent && d3.z.longShare > T) d3.flags.push({ key: 'long', text: round(d3.longShare * 100) + '% of sentences run 30 words or more (human average ' + round(C3.mu.longShare * 100) + '%). Let some sentences breathe.' });
    if (d3.z.paraCV > T) d3.flags.push({ key: 'paralen', text: 'Paragraphs are a similar length (variation ' + round(d3.paraCV, 2) + '; human average ' + round(C3.mu.paraCV, 2) + ').' });
    if (secWords.length >= 4 && d3.z.secCV > T) d3.flags.push({ key: 'seclen', text: 'Section lengths are uniform (variation ' + round(d3.secCV, 2) + '; human average ' + round(C3.mu.secCV, 2) + '). Generated text often lands every section at a similar size.' });
    if (proseWords3 >= 200 && d3.z.asides > T) d3.flags.push({ key: 'asides', text: 'Almost no asides: ' + round(d3.asides, 1) + ' parentheses, semicolons and questions per 1,000 words (human average ' + round(C3.mu.asides, 1) + ').' });
    if (proseWords3 >= 200 && d3.z.triples > T) d3.flags.push({ key: 'triples', text: d3.triples.length + ' lists of three (' + round(d3.tripleRate, 1) + ' per 1,000 words; human average ' + round(C3.mu.triples, 1) + '). Use the number of items the content has.' });
    if (runs.length) d3.flags.push({ key: 'runs', text: runs.length + ' run' + (runs.length > 1 ? 's' : '') + ' of 3+ consecutive sections built on an identical scaffold.', note: true });

    d3.bulletShare = totalWords ? bulletWords / totalWords : 0;
    paraSent.forEach(function (s) {
      var parens = (s.text.match(/\(/g) || []).length;
      var dashes = (s.text.match(/\s[\u2014\u2013-]\s|\u2014/g) || []).length;
      var commas = (s.text.match(/,/g) || []).length;
      var score = parens + Math.floor(dashes / 2 + 0.5) + Math.floor(commas / 3);
      if (s.words > 30 && score >= 3) d3.nested.push(s);
    });
    d3.strikes = d3.flags.filter(function (f) { return !f.note; }).length;
    d3.level = d3.score <= C3.pass ? 0 : d3.score <= C3.fail ? 1 : 2;
    // Rhythm needs enough sentences to judge. Under 20 prose sentences the check can note, but not fail.
    d3.short = lens.length < 20;
    if (d3.short && d3.level === 2) d3.level = 1;

    /* ---------------- Dimension 4: stock AI phrasing ---------------- */
    // v1.5: replaces "profundity inflation". Vague intensity words ("powerful", "incredibly") were more common in the
    // human texts we tested, so they are no longer scored. What separated the groups: stock vocabulary (two eras),
    // negative parallelism ("not just X, but Y", "Y, not X", "rather than") and formula sentence starters.
    var d4 = { escalators: [], vocab: [], starters: [], antitheses: [], intensity: [], runs: [] };
    sentences.forEach(function (s) {
      if (s.blockType === 'table') return;
      unquoted(findRe(NEG_PARALLEL, s.ntext), s.ntext).forEach(function (h) {
        mark(s, h.start, h.end, 4, 'Negative parallelism');
        d4.escalators.push({ s: s, match: h.match.replace(/^,\s*/, '').toLowerCase() });
      });
      unquoted(findList(STOCK_OLD_RE, s.ntext), s.ntext).concat(unquoted(findList(STOCK_NEW_RE, s.ntext), s.ntext)).forEach(function (h) {
        mark(s, h.start, h.end, 4, 'Stock AI vocabulary');
        d4.vocab.push({ s: s, match: h.match.toLowerCase() });
      });
      if (s.blockType === 'para' && FORMULA_START.test(s.ntext)) {
        var fm = s.ntext.match(FORMULA_START)[0];
        mark(s, 0, fm.length, 4, 'Formula starter');
        d4.starters.push({ s: s, match: fm.toLowerCase() });
      }
    });
    for (var j = 0; j < sentences.length - 1; j++) {
      var a = sentences[j], b = sentences[j + 1];
      if (a.sec === b.sec && ANTI_A.test(a.ntext) && ANTI_B.test(b.ntext)) d4.antitheses.push([a, b]);
    }
    d4.intensity = d4.vocab;
    d4.edgeRuns = 0;
    d4.strikes = d4.escalators.length + d4.vocab.length + d4.starters.length;
    d4.rate = per1k(d4.strikes, totalWords);
    // Density, not single words: a fail needs at least 3 hits and a note at least 2, however short the text.
    d4.level = (d4.rate <= CAL.d4.pass || d4.strikes < 2) ? 0 : (d4.rate <= CAL.d4.fail || d4.strikes < 3) ? 1 : 2;

    /* ---------------- Claims to verify (not scored) ---------------- */
    var RE_STAT = /\d[\d,.]*\s?%|\bper ?cent\b|\b\d[\d,.]*\s?(?:x|times)\b|[$€£¥]\s?\d|\b\d[\d,.]*\s?(?:million|billion|thousand|bn|k)\b|\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten) (?:in|out of) (?:\d+|two|three|four|five|six|seven|eight|nine|ten)\b|\b\d[\d,.]*\s+(?:hours?|minutes?|mins?|seconds?|days?|weeks?|months?|years?|people|users|customers|clients|companies|businesses|organi[sz]ations|employees|staff|members|visitors|sessions|downloads|leads|points?|percentage points?)\b|\b(?:half|a third|a quarter|two thirds|three quarters|most|majority|nearly all|almost all) of (?:all )?(?:\w+ )?(?:marketers|companies|businesses|organi[sz]ations|employees|people|buyers|users|customers|teams|leaders|executives)\b/i;
    var RE_RESEARCH = /\b(?:stud(?:y|ies)|research|survey|surveys|report|reports|poll|analysis|data|experts?|scientists?|researchers?|analysts?)\b[^.!?]{0,40}?\b(?:shows?|showed|shown|finds?|found|suggests?|suggested|reveals?|revealed|indicates?|indicated|confirms?|confirmed|says?|said|proves?|proved|estimates?|estimated|predicts?|predicted)\b/i;
    var RE_SUPER = /\b(?:the|our|its|their)\s+(?:largest|biggest|fastest|leading|best|most popular|most trusted|most advanced|number one|top-rated|#1)\b|\b(?:the|our)\s+(?:first|only)\s+(?:[\w-]+\s+){0,3}?(?:to|that|which|company|tool|platform|product|solution|provider|software|app|vendor|firm|agency|directory|service)\b|\bnumber one\b|#1\b|\bworld'?s\s+(?:first|largest|leading|best|fastest|most)\b|\b(?:industry|market)[- ]leading\b|\bunmatched\b|\bguaranteed?\b/i;
    var RE_QUOTE = /"[^"]{20,}"/;
    var RE_QUOTE_ATTR = /\b(?:said|says|told|according to|wrote|writes|explains?|explained|added|notes?|noted)\b/i;
    var RE_DATE = /\b(?:in|since|by|from|until|during|as of|before|after)\s+(?:early |mid-|late )?(?:19|20)\d\d\b|\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+(?:\d{1,2},?\s+)?(?:19|20)\d\d\b/i;
    var RE_SOURCE = /\baccording to\b|\bsource[sd]?\s*:|\bcited (?:by|in)\b|\bpublished (?:by|in)\b|\breported by\b|https?:\/\/|www\.|\[\d+\]|\(\s*(?:19|20)\d\d\s*\)/i;
    var RE_NAMED_SOURCE = /\b[A-Z][\w&.\-']+(?:\s+[A-Z][\w&.\-']+){0,4}(?:'s)?\s+(?:(?:19|20)\d\d\s+)?(?:study|survey|report|research|data|analysis|index|benchmark|census|poll)\b|\b[A-Z][\w&.\-]+(?:\s+[A-Z][\w&.\-]+){0,3}\s+(?:found|reported|estimates|estimated|surveyed|published|measured)\b/;
    var RE_FIRST_PARTY = /\b(?:[Ww]e|[Oo]ur|[Uu]s|[Mm]y|I)\b/;
    var GENERIC_SRC = /^(?:a|an|the|one|this|that|these|those|recent|new|latest|independent|industry|market|global|some|many|most|several|research|researchers|study|studies|data|experts?|analysts?|scientists?|survey|surveys|report|reports|analysis|our|my|their|its|his|her|internal|annual|another|further|more|other|separate|early|current|previous)$/i;
    function namedSource(text) {
      var re = new RegExp(RE_NAMED_SOURCE.source, 'g'), m;
      while ((m = re.exec(text)) !== null) {
        var words = m[0].split(/\s+/).filter(function (w) { return /^[A-Z]/.test(w); });
        var named = words.filter(function (w) { return !GENERIC_SRC.test(w.replace(/'s$/, '').replace(/[^A-Za-z]/g, '')); });
        if (named.length) return true;
      }
      return false;
    }
    var RE_PRICE_ONLY = /[$\u20AC\u00A3\u00A5]\s?\d/;
    var claims = [];
    sentences.forEach(function (s, idx) {
      var t = s.ntext, types = [];
      if (RE_STAT.test(t)) {
        var statOnlyPrice = RE_PRICE_ONLY.test(t) && !RE_STAT.test(t.replace(/[$\u20AC\u00A3\u00A5]\s?\d[\d,.]*(?:\s?(?:k|m|bn|million|billion|thousand))?/gi, ''));
        types.push(statOnlyPrice ? 'price' : 'statistic');
      }
      if (RE_RESEARCH.test(t)) types.push('research claim');
      if (RE_SUPER.test(t)) types.push('superlative');
      if (RE_QUOTE.test(t) && RE_QUOTE_ATTR.test(t)) types.push('quote');
      if (RE_DATE.test(t)) types.push('date');
      if (!types.length) return;
      // A neighbor only counts as the source when it is a pure attribution line, not a claim of its own.
      var neighbors = sentences.filter(function (o) { return o.sec === s.sec && o.block === s.block && o.id === s.id + 1; });
      var sourced = s.linkMark || RE_SOURCE.test(t) || namedSource(s.text) || neighbors.some(function (o) { return RE_SOURCE.test(o.ntext) && !RE_STAT.test(o.ntext) && o.words <= 14; });
      if (!sourced && types.indexOf('quote') >= 0 && /\b(?:said|says|told|wrote|added|explains?|explained|noted)\s+[A-Z][a-z]+|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+(?:said|says|told|wrote|added|explained|noted)\b/.test(s.text)) sourced = true;
      var stripQ = function (x) { return x.replace(/"[^"]*"|\u201C[^\u201D]*\u201D/g, ''); };
      var blockMates = sentences.filter(function (o) { return o.sec === s.sec && o.block === s.block; });
      var firstParty = !sourced && !RE_RESEARCH.test(t) && (RE_FIRST_PARTY.test(stripQ(s.text)) || blockMates.some(function (o) { return RE_FIRST_PARTY.test(stripQ(o.text)); }));
      var needsSource = types.indexOf('statistic') >= 0 || types.indexOf('research claim') >= 0 || types.indexOf('quote') >= 0;
      var status = sourced ? 'source named' : firstParty ? 'your own claim' : needsSource ? 'no source nearby' : 'check';
      var c = { s: s, types: types, sourced: sourced, firstParty: firstParty, status: status, unsourced: needsSource && !sourced && !firstParty };
      claims.push(c);
      flag(s, 5, 'Claim to verify: ' + types.join(', ') + (c.unsourced ? ' (no source nearby)' : ''));
    });
    var claimsSummary = {
      list: claims,
      total: claims.length,
      unsourced: claims.filter(function (c) { return c.unsourced; }).length,
      stats: claims.filter(function (c) { return c.types.indexOf('statistic') >= 0; }).length,
      research: claims.filter(function (c) { return c.types.indexOf('research claim') >= 0; }).length,
      superlatives: claims.filter(function (c) { return c.types.indexOf('superlative') >= 0; }).length
    };

    /* ---------------- GEO check (separate from shape) ---------------- */
    var firstPara = sentences.filter(function (s) { return s.blockType === 'para'; })[0];
    var geo = { firstSentence: firstPara ? firstPara.text : '' };
    if (firstPara) {
      var weakOpen = /^(?:in today'?s|in the (?:modern|ever|fast|world|age|realm|digital)|have you ever|imagine|are you|when it comes to|in an era|as (?:businesses|organizations|companies)|there'?s no denying|it'?s no secret)/i.test(firstPara.ntext);
      var answerish = firstPara.numbers > 0 || firstPara.proper > 0 || /\b(?:is|are|means|costs|takes|works|lets|shows|found)\b/i.test(firstPara.ntext);
      geo.answerFirst = !weakOpen && answerish && !/\?["')]*$/.test(firstPara.ntext);
      geo.weakOpen = weakOpen;
    }

    /* ---------------- Surface tells (not scored) ---------------- */
    var emDashes = (allText.match(/\u2014/g) || []).length;
    var surfaceHits = {};
    findList(SURFACE_RE, allText).forEach(function (h) { var k = h.match.toLowerCase(); surfaceHits[k] = (surfaceHits[k] || 0) + 1; });

    var emDashCount = (allText.match(/\u2014/g) || []).length;
    /* ---------------- AI-style signals (not scored, not proof) ---------------- */
    function clamp01(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
    function phraseHits(re) {
      var hits = [];
      sentences.forEach(function (s) { if (s.blockType === 'table' || (s.blockType === 'bullet' && s.words <= 8)) return; unquoted(findList(re, s.ntext), s.ntext).forEach(function (h) { hits.push({ s: s, match: h.match.toLowerCase() }); }); });
      return hits;
    }
    function topPhrases(hits, n) {
      var c = {}; hits.forEach(function (h) { c[h.match] = (c[h.match] || 0) + 1; });
      return Object.keys(c).sort(function (a, b) { return c[b] - c[a]; }).slice(0, n || 5).map(function (k) { return '"' + k + '"' + (c[k] > 1 ? ' x' + c[k] : ''); });
    }
    var kw = totalWords / 1000 || 1;
    var vocabHits = phraseHits(AI_VOCAB_RE);
    var frameHits = phraseHits(AI_FRAME_RE);
    var signHits = phraseHits(AI_SIGNPOST_RE);
    var summaryStarts = sentences.filter(function (s) { return s.blockType === 'para' && SUMMARY_START.test(s.ntext); });
    var triadRe = /\b[\w'-]+(?: [\w'-]+)?, [\w'-]+(?: [\w'-]+)?,? and [\w'-]+\b/;
    var triads = sentences.filter(function (s) { return s.blockType === 'para' && triadRe.test(s.ntext); });
    var proseCount = paraSent.length || 1;
    var sig = [];
    function addSig(id, label, what, weight, strength, evidence, examples) {
      sig.push({ id: id, label: label, what: what, weight: weight, strength: clamp01(strength), evidence: evidence, examples: examples || [] });
    }
    addSig('vocab', 'Stock AI vocabulary', 'Words generated text over-uses: "delve", "seamless", "robust", "unlock", "pivotal".', 3,
      Math.min((vocabHits.length / kw) / 8, vocabHits.length / 4), vocabHits.length + ' in ' + totalWords + ' words', topPhrases(vocabHits));
    addSig('escalator', 'Negative parallelism', '"Not just X, but Y", "Y, not X" and "rather than": constructions that correct a claim nobody made.', 2,
      Math.min((d4.escalators.length / kw) / 2.5, d4.escalators.length / 3), d4.escalators.length + ' use' + (d4.escalators.length === 1 ? '' : 's'), d4.escalators.slice(0, 3).map(function (e) { return '"' + e.match + '"'; }));
    addSig('frame', 'Formula openings and summaries', 'Warm-up openers ("In today\'s...", "When it comes to...") and paragraphs that close on "Ultimately", "Overall", "In short".', 2,
      Math.min(((frameHits.length + summaryStarts.length) / kw) / 5, (frameHits.length + summaryStarts.length) / 3), (frameHits.length + summaryStarts.length) + ' found', topPhrases(frameHits, 3).concat(summaryStarts.slice(0, 2).map(function (s) { return '"' + truncate(s.text, 40) + '"'; })));
    addSig('signpost', 'Sign-posting and filler', '"It\'s worth noting", "let\'s dive in", "here\'s the thing": lines that announce a point instead of making it.', 1.5,
      Math.min((signHits.length / kw) / 3, signHits.length / 3), signHits.length + ' found', topPhrases(signHits));
    addSig('rhythm', 'Even sentence rhythm', 'Generated text tends to keep sentences a similar length. Human prose swings between short and long.', 1.5,
      lens.length >= 10 ? (0.6 - d3.sentCV) / 0.3 : 0, lens.length >= 10 ? 'length variation ' + round(d3.sentCV, 2) + ' (human prose is usually above 0.6)' : 'too few sentences to judge');
    addSig('specific', 'Few names or numbers', 'Generated text stays general. People who know the subject name customers, tools, places and figures.', 1.5,
      (2.5 - d2.density) / 2.5, round(d2.density, 1) + ' per 100 words');
    addSig('sections', 'Same-shaped sections', 'Every section opens, runs and closes the same way, at a similar length.', 1,
      sections.length >= 4 ? Math.max((0.45 - d3.secCV) / 0.35, d3.runs.length ? 0.7 : 0) : 0, sections.length >= 4 ? 'section length variation ' + round(d3.secCV, 2) + (d3.runs.length ? ', ' + d3.runs.length + ' identical run' + (d3.runs.length > 1 ? 's' : '') : '') : 'too few sections to judge');
    addSig('triads', 'Lists of three', '"Fast, simple, and secure." Generated text reaches for groups of three far more than most writers.', 1,
      ((triads.length / proseCount) - 0.1) / 0.25, triads.length + ' of ' + proseCount + ' sentences', triads.slice(0, 2).map(function (s) { return '"' + truncate(s.text, 70) + '"'; }));
    addSig('emdash', 'Em dashes', 'Common in generated text, but plenty of writers use them too, so this counts for little.', 0.75,
      Math.min((emDashCount / kw) / 6, emDashCount / 5), emDashCount + ' found');
    // Raw structural features (used by the fitted model; see AI_MODEL)
    var paraBlocks = blocks.filter(function (b) { return b.type === 'para'; });
    var paraLens = paraBlocks.map(function (b) { return wordCount(b.text); });
    var proseText = paraSent.map(function (x) { return x.ntext; }).join(' ');
    var proseWords = proseText.split(/\s+/).filter(function (w) { return /[A-Za-z]/.test(w); });
    var lw = proseWords.map(function (w) { return w.toLowerCase().replace(/[^a-z']/g, ''); }).filter(Boolean);
    var uniq = {}; lw.slice(0, 400).forEach(function (w) { uniq[w] = 1; });
    var pw = lw.length || 1;
    var aiFeatures = {
      secCV: sections.length >= 3 ? d3.secCV : 0.6,
      density: d2.density,
      sentMean: d3.sentMean,
      sentCV: d3.sentCV,
      paraMean: mean(paraLens),
      paraCV: paraLens.length > 2 ? sd(paraLens) / (mean(paraLens) || 1) : 0.5,
      bullets: d3.bulletShare,
      headingsPer1k: (sections.length / kw),
      triadRate: triads.length / proseCount,
      escPer1k: d4.escalators.length / kw,
      youRate: (proseText.match(/\b(?:you|your|you're|you've|you'll)\b/gi) || []).length / pw * 100,
      wePer100: (proseText.match(/\b(?:we|our|us|we're|we've|we'll)\b/gi) || []).length / pw * 100,
      iPer100: (proseText.match(/\b(?:I|I'm|I've|I'd|my|me)\b/g) || []).length / pw * 100,
      contractions: (proseText.match(/\b\w+'(?:s|t|re|ve|ll|d|m)\b/gi) || []).length / pw * 100,
      questions: paraSent.filter(function (x) { return /\?["')]*$/.test(x.ntext); }).length / proseCount,
      parens: (proseText.match(/\(/g) || []).length / pw * 100,
      colons: (proseText.match(/:/g) || []).length / pw * 100,
      wordLen: lw.reduce(function (a, w) { return a + w.length; }, 0) / pw,
      ttr: Object.keys(uniq).length / Math.min(400, pw),
      vocabPer1k: vocabHits.length / kw,
      framePer1k: (frameHits.length + summaryStarts.length) / kw,
      emPer1k: emDashCount / kw,
      longSent: lens.filter(function (n) { return n >= 30; }).length / (lens.length || 1),
      shortSent: lens.filter(function (n) { return n <= 8; }).length / (lens.length || 1)
    };
    var wsum = 0, ssum = 0;
    sig.forEach(function (g) { wsum += g.weight; ssum += g.weight * g.strength; });
    var phraseScore = wsum ? ssum / wsum : 0;
    var fitted = aiModelScore(aiFeatures);
    var aiScore = fitted.p;
    var aiBand = totalWords < 300 ? 'Too short' : aiScore >= AI_MODEL.high ? 'High' : aiScore >= AI_MODEL.medium ? 'Medium' : 'Low';
    var aiSignals = { features: aiFeatures, contrib: fitted.contrib, phraseScore: phraseScore, signals: sig, score: aiScore, band: aiBand, strong: sig.filter(function (g) { return g.strength >= 0.6; }).length, reliable: totalWords >= 300 };

    /* ---------------- Strongest habit ---------------- */
    function topMatch(list) {
      var c = {};
      list.forEach(function (h) { c[h.match] = (c[h.match] || 0) + 1; });
      var best = null;
      Object.keys(c).forEach(function (k) { if (!best || c[k] > c[best]) best = k; });
      return best ? { phrase: best, count: c[best] } : null;
    }
    var candidates = [];
    if (d1.strikes) candidates.push({ level: d1.level, weight: d1.rate, text: 'Narrating what things mean: ' + d1.strikes + ' sentence' + (d1.strikes > 1 ? 's' : '') + ' explain the significance instead of showing it.' });
    if (d2.vagueHits.length || d2.zeroSections.length) {
      var tv = topMatch(d2.vagueHits);
      candidates.push({ level: d2.level, weight: d2.vagueRate + d2.zeroShare * 5, text: 'Category language instead of named things' + (tv ? ' ("' + tv.phrase + '" x' + tv.count + ')' : '') + (d2.zeroSections.length ? ', with ' + d2.zeroSections.length + ' section' + (d2.zeroSections.length > 1 ? 's' : '') + ' containing no number or name' : '') + '.' });
    }
    var d3scoredFlags = d3.flags.filter(function (f) { return !f.note; });
    if (d3scoredFlags.length) candidates.push({ level: d3.level, weight: d3.score * 4, text: 'Even rhythm: ' + d3scoredFlags[0].text });
    if (d4.strikes) {
      var tvoc = topMatch(d4.vocab), tneg = topMatch(d4.escalators);
      var d4top = (tvoc && (!tneg || tvoc.count >= tneg.count)) ? 'Stock vocabulary ("' + tvoc.phrase + '" x' + tvoc.count + ')' : tneg ? 'Negative parallelism ("' + tneg.phrase + '" x' + tneg.count + ')' : 'Formula sentence starters';
      candidates.push({ level: d4.level, weight: d4.rate, text: d4top + ', ' + round(d4.rate, 1) + ' stock phrases per 1,000 words.' });
    }
    candidates.sort(function (x, y) { return y.level - x.level || y.weight - x.weight; });
    var habit = candidates.length && candidates[0].level > 0 ? candidates[0].text : null;

    var levels = [d1.level, d2.level, d3.level, d4.level];
    var passes = levels.filter(function (l) { return l === 0; }).length;
    var fails = levels.filter(function (l) { return l === 2; }).length;

    return {
      mode: mode, sections: sections, sentences: sentences, blocks: blocks,
      words: totalWords, sentenceCount: paraSent.length, tableBlocks: tableBlocks,
      d1: d1, d2: d2, d3: d3, d4: d4, geo: geo,
      surface: { emDashes: emDashes, hits: surfaceHits },
      habit: habit, passes: passes, fails: fails, claims: claimsSummary, ai: aiSignals
    };
  }

  /* ------------------------------------------------------------------ */
  /* Rendering                                                           */
  /* ------------------------------------------------------------------ */

  var DIM_NAMES = ['', 'Over-explanation', 'Real things, named', 'Rhythm and variety', 'Stock AI phrasing'];
  var DIM_WHAT = [
    '',
    'Trailing "..., highlighting" clauses, significance claims and closing summaries that narrate what things mean.',
    'Named customers, tools, places, dates and numbers versus category language.',
    'Sentence and section length, asides and lists of three, against human business writing.',
    'Stock AI vocabulary, "not just X, but Y" constructions and formula starters.'
  ];

  function highlightSentence(s) {
    var t = s.ntext;
    var marks = s.marks.slice().sort(function (a, b) { return a.start - b.start || b.end - a.end; });
    var out = '', pos = 0;
    marks.forEach(function (m) {
      if (m.start < pos) return;
      out += escHtml(t.slice(pos, m.start));
      out += '<mark class="hsc-m hsc-d' + m.dim + '" title="' + escHtml(m.label) + '">' + escHtml(t.slice(m.start, m.end)) + '</mark>';
      pos = m.end;
    });
    out += escHtml(t.slice(pos));
    if (s.flags.length) {
      var dims = {}, labels = [];
      s.flags.forEach(function (f) { dims[f.dim] = true; if (labels.indexOf(f.label) < 0) labels.push(f.label); });
      var cls = Object.keys(dims).map(function (d) { return 'hsc-sf' + d; }).join(' ');
      out = '<span class="hsc-sflag ' + cls + '" title="' + escHtml(labels.join('; ')) + '">' + out + '</span>';
    }
    return out;
  }

  function quote(s, extra) {
    return '<li><q>' + highlightSentence(s) + '</q>' + (extra ? ' <span class="hsc-why">' + escHtml(extra) + '</span>' : '') + '</li>';
  }

  function listItems(items, max) {
    max = max || 20;
    var html = items.slice(0, max).join('');
    if (items.length > max) html += '<li class="hsc-more">+' + (items.length - max) + ' more, marked in the full text below.</li>';
    return html;
  }

  function metric(label, value) {
    return '<div class="hsc-metric"><span class="hsc-metric-v">' + escHtml(String(value)) + '</span><span class="hsc-metric-l">' + escHtml(label) + '</span></div>';
  }

  function badge(level) {
    var cls = ['hsc-pass', 'hsc-notes', 'hsc-fail'][level];
    return '<span class="hsc-badge ' + cls + '">' + verdict(level) + '</span>';
  }

  function uniqueSentences(list) {
    var seen = {}, out = [];
    list.forEach(function (h) { var s = h.s || h; if (!seen[s.id]) { seen[s.id] = true; out.push(s); } });
    return out;
  }

  function rhythmChart(r) {
    var ss = r.sentences.filter(function (s) { return s.blockType === 'para'; });
    if (ss.length < 5) return '';
    var W = 640, H = 120, max = 0;
    ss.forEach(function (s) { if (s.words > max) max = s.words; });
    max = Math.max(max, 10);
    var bw = W / ss.length, bars = '';
    ss.forEach(function (s, i) {
      var h = Math.max(1, (s.words / max) * (H - 10));
      var flagged = s.marks.length || s.flags.some(function (f) { return f.dim !== 5; });
      bars += '<rect x="' + round(i * bw, 2) + '" y="' + round(H - h, 2) + '" width="' + Math.max(1, round(bw - 1, 2)) + '" height="' + round(h, 2) + '" class="' + (flagged ? 'hsc-rbar-f' : 'hsc-rbar') + '"><title>' + s.words + ' words</title></rect>';
    });
    var my = H - (r.d3.sentMedian / max) * (H - 10);
    return '<figure class="hsc-rhythm"><svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" role="img" aria-label="Sentence length through the piece">' + bars +
      '<line x1="0" x2="' + W + '" y1="' + round(my, 2) + '" y2="' + round(my, 2) + '" class="hsc-median"/></svg>' +
      '<figcaption>Sentence length through the piece, in order. The line is the median (' + r.d3.sentMedian + ' words). Darker bars contain a flag. Human prose usually looks jagged.</figcaption></figure>';
  }

  function renderFullText(r) {
    var html = '';
    r.sections.forEach(function (sec) {
      html += '<div class="hsc-sec">';
      if (sec.heading) html += '<div class="hsc-sec-h">' + escHtml(sec.heading) + ' <span class="hsc-sig">' + escHtml(sec.sig) + '</span></div>';
      else html += '<div class="hsc-sec-h hsc-sec-h-anon"><span class="hsc-sig">' + escHtml(sec.sig) + '</span></div>';
      if (sec.words >= 25 && sec.anchors === 0) html += '<div class="hsc-zero">No numbers or names in this section.</div>';
      sec.blocks.forEach(function (b) {
        var inner = b.sentences.map(highlightSentence).join(' ');
        if (b.type === 'bullet') html += '<div class="hsc-b-li">' + inner + '</div>';
        else if (b.type === 'table') html += '<div class="hsc-b-tr">' + inner + '</div>';
        else html += '<p>' + inner + '</p>';
      });
      html += '</div>';
    });
    return html;
  }

  function aiMeter(ai, compact) {
    var p = ai.score, m = AI_MODEL, pos;
    if (p < m.medium) pos = (p / m.medium) * 33.3;
    else if (p < m.high) pos = 33.3 + ((p - m.medium) / (m.high - m.medium)) * 33.3;
    else pos = 66.6 + Math.min(1, (p - m.high) / 0.4) * 33.4;
    pos = Math.max(2, Math.min(99, pos));
    var cls = ai.band === 'High' ? 'hsc-ai-high' : ai.band === 'Medium' ? 'hsc-ai-med' : 'hsc-ai-low';
    return '<div class="hsc-aimeter ' + cls + (compact ? ' hsc-aimeter-sm' : '') + '"><div class="hsc-aitrack"><span style="width:' + Math.round(pos) + '%"></span></div><div class="hsc-aiscale"><span>Low</span><span>Medium</span><span>High</span></div></div>';
  }
  function aiSentence(ai) {
    if (ai.band === 'Too short') return 'Needs at least 300 words for a reading.';
    if (ai.band === 'High') return 'The structure looks a lot like AI-written blog posts in our test set.';
    if (ai.band === 'Medium') return 'Mixed: some of the structure looks like AI-written blog posts in our test set. Medium is weak evidence on its own.';
    return 'The structure looks more like the human-written posts in our test set.';
  }
  function fmtFeat(k, v) {
    var L = AI_FEAT_LABEL[k];
    if (L[2] === 'pct') return Math.round(v * 100) + '%';
    return (Math.round(v * Math.pow(10, L[2])) / Math.pow(10, L[2])) + (L[1] === 'words' ? ' words' : L[1] === 'variation' ? '' : ' ' + L[1]);
  }
  function aiDrivers(ai) {
    var c = ai.contrib.slice().sort(function (a, b) { return b.c - a.c; });
    return { toward: c.filter(function (x) { return x.c > 0.08 && x.consistent; }).slice(0, 5), against: c.filter(function (x) { return x.c < -0.08 && x.consistent; }).reverse().slice(0, 3) };
  }
  function driverLine(x) {
    var L = AI_FEAT_LABEL[x.k];
    return '<li><strong>' + escHtml(L[0]) + '</strong>: ' + (x.higher ? 'more' : 'less') + ' than typical human writing <span class="hsc-why">this draft ' + escHtml(fmtFeat(x.k, x.value)) + ', human posts ' + escHtml(fmtFeat(x.k, x.typical)) + '</span></li>';
  }
  var AI_ACCURACY = 'In our held-out test, High caught 18 of 26 AI-written texts and 2 of 48 human-written texts. Medium or High caught 23 of 26 AI texts, but also 9 of 48 human texts, so Medium means little on its own.';

  function renderReport(r) {
    var d1 = r.d1, d2 = r.d2, d3 = r.d3, d4 = r.d4;
    var h = '';

    var summary;
    if (r.fails === 0 && r.passes === 4) summary = 'Passes all four shape checks.';
    else if (r.fails === 0) summary = 'Passes ' + r.passes + ' of 4 checks, with notes on the rest.';
    else summary = 'Fails ' + r.fails + ' of 4 shape checks.';

    h += '<div class="hsc-head">';
    h += '<p class="hsc-summary">' + escHtml(summary) + '</p>';
    h += '<p class="hsc-sub">' + r.words + ' words, ' + r.sentenceCount + ' prose sentences, ' + r.sections.length + ' ' + (r.mode === 'headings' ? 'sections (split by headings)' : 'units (no headings found, so each paragraph is treated as a section)') + '.</p>';
    h += '<p class="hsc-ailine">AI-style signals: <a href="#" class="hsc-jump-ai"><strong class="hsc-aiband hsc-aiband-' + r.ai.band.toLowerCase().replace(/ /g, '-') + '">' + r.ai.band + '</strong></a> <span>' + escHtml(aiSentence(r.ai)) + (r.ai.band === 'Too short' ? '' : ' A signal, not proof of who wrote it.') + '</span></p>';
    if (r.claims.total) h += '<p class="hsc-claimline"><a href="#" class="hsc-jump-claims">' + r.claims.total + ' claim' + (r.claims.total > 1 ? 's' : '') + ' to verify</a>' + (r.claims.unsourced ? ', <strong>' + r.claims.unsourced + ' with no source nearby</strong>' : ', all with a source nearby') + '.</p>';
    if (r.words < 300) h += '<p class="hsc-warn">Under 300 words, these measures are noisy. Treat the results as a rough read.</p>';
    else if (r.words > 1500) h += '<p class="hsc-warn">Over 1,500 words, results average across the whole piece, so a few weak sections can hide behind strong ones. For a sharper read, check one section at a time.</p>';
    if (r.habit) h += '<p class="hsc-habit"><strong>Strongest machine habit:</strong> ' + escHtml(r.habit) + '</p>';
    h += '<div class="hsc-head-actions"><button type="button" class="hsc-btn hsc-pdf">Download PDF report</button><span class="hsc-head-note">Scorecard, every flagged sentence and the marked-up text, ready to share.</span></div>';
    h += '</div>';

    h += '<table class="hsc-score"><thead><tr><th>Dimension</th><th>Result</th><th>Strikes</th><th>What it measures</th></tr></thead><tbody>';
    [d1, d2, d3, d4].forEach(function (d, i) {
      h += '<tr><td>' + (i + 1) + '. ' + DIM_NAMES[i + 1] + '</td><td>' + badge(d.level) + '</td><td>' + d.strikes + '</td><td>' + DIM_WHAT[i + 1] + '</td></tr>';
    });
    h += '</tbody></table>';

    // D1
    h += '<section class="hsc-dim hsc-dim1"><h3>1. Over-explanation ' + badge(d1.level) + '</h3>';
    h += '<p class="hsc-lede">Generated text narrates what things mean instead of trusting the reader: a trailing ", highlighting the importance of..." clause, a claim that something "plays a crucial role", a section that closes on "Ultimately...". In our tests these separated 2023-era GPT text from people; current Claude models rarely do it, so a pass here is weak evidence.</p>';
    h += '<div class="hsc-metrics">' + metric('flagged sentences', d1.strikes) + metric('per 1,000 words', round(d1.rate, 1)) + metric('trailing "..., highlighting" clauses', d1.tackOns.length) + metric('significance claims', d1.significance.length) + metric('interpret a number or list', d1.restatements.length) + metric('section-closing summaries', d1.summaries.length) + '</div>';
    var d1s = uniqueSentences(d1.phraseHits.concat(d1.restatements, d1.summaries));
    if (d1s.length) h += '<p class="hsc-fix"><strong>Fix:</strong> cut the trailing clause or the explaining sentence and re-read. If meaning dies with the cut, the example was underbuilt. Fix the example, not the explanation.</p><ul class="hsc-quotes">' + listItems(d1s.map(function (s) { return quote(s); })) + '</ul>';
    else h += '<p class="hsc-ok">Nothing flagged.</p>';
    h += '<p class="hsc-note">Not a strike: a number with its unit and time window. "82% of searches resolve, median four seconds, across 90 days" is specification.</p></section>';

    // D2
    h += '<section class="hsc-dim hsc-dim2"><h3>2. Real things, named ' + badge(d2.level) + '</h3>';
    h += '<p class="hsc-lede">People with jobs name customers, tools, numbers, dates and places. Generated text stays in category language: "a leading provider", "organizations of all sizes".</p>';
    h += '<div class="hsc-metrics">' + metric('anchors per 100 words', round(d2.density, 1)) + metric('sections with no number or name', d2.zeroSections.length) + metric('category phrases', d2.vagueHits.length) + metric('"you" vs generic plurals', d2.you + ' : ' + d2.generic) + '</div>';
    if (d2.zeroSections.length) {
      h += '<p class="hsc-fix"><strong>Sections with no anchors:</strong></p><ul class="hsc-quotes">' + listItems(d2.zeroSections.map(function (sec) {
        var label = sec.heading ? sec.heading : truncate(sec.sentences[0] ? sec.sentences[0].text : '', 90);
        return '<li>' + escHtml(label) + ' <span class="hsc-why">' + sec.words + ' words</span></li>';
      }), 12) + '</ul>';
    }
    var d2s = uniqueSentences(d2.vagueHits);
    if (d2s.length) h += '<p class="hsc-fix"><strong>Fix:</strong> one proper noun or number per vague slot. "Fast search" becomes "median four seconds". Where you cannot name a client, name its shape: "a credit union with 226 staff".</p><ul class="hsc-quotes">' + listItems(d2s.map(function (s) { return quote(s); })) + '</ul>';
    if (!d2.zeroSections.length && !d2s.length) h += '<p class="hsc-ok">Nothing flagged.</p>';
    h += '<p class="hsc-note">This tool counts anchors. It cannot tell whether they are correct. A wrong price or a competitor that was acquired last year costs more than no specifics at all.</p></section>';

    // D3
    h += '<section class="hsc-dim hsc-dim3"><h3>3. Rhythm and variety ' + badge(d3.level) + '</h3>';
    h += '<p class="hsc-lede">Human writing swings: a six-word sentence next to a 35-word one, a one-line paragraph next to a long one, an aside in parentheses, a question. Generated text holds a narrow band and reaches for lists of three. Each measure below is compared with the human business writing we tested.</p>';
    h += '<div class="hsc-metrics">' + metric('sentence length spread', round(d3.sentSD, 1) + ' words') + metric('sentences of 30+ words', round(d3.longShare * 100) + '%') + metric('paragraph length variation', d3.paraCV === null ? 'n/a' : round(d3.paraCV, 2)) + metric('section length variation', round(d3.secCV, 2)) + metric('asides per 1,000 words', round(d3.asides, 1)) + metric('lists of three', d3.triples.length) + '</div>';
    h += rhythmChart(r);
    var d3scored = d3.flags.filter(function (f) { return !f.note; });
    if (d3scored.length) h += '<ul class="hsc-flags">' + d3scored.map(function (f) { return '<li>' + escHtml(f.text) + '</li>'; }).join('') + '</ul>';
    if (d3.triples.length && d3.z.triples > (CAL.d3.flagZ || 1)) h += '<p class="hsc-fix"><strong>Lists of three:</strong></p><ul class="hsc-quotes">' + listItems(uniqueSentences(d3.triples).map(function (s) { return quote(s); }), 8) + '</ul>';
    if (d3.runs.length) {
      h += '<p class="hsc-fix"><strong>Not scored, worth a look: identical scaffolds</strong></p><ul class="hsc-quotes">' + d3.runs.map(function (run) {
        var names = [];
        for (var k = run.from; k <= run.to; k++) names.push(r.sections[k].heading || ('Unit ' + (k + 1)));
        return '<li>' + escHtml(names.join(' / ')) + ' <span class="hsc-why">' + escHtml(run.sig) + '</span></li>';
      }).join('') + '</ul>';
    }
    if (d3scored.length) h += '<p class="hsc-fix"><strong>Fix:</strong> vary on purpose. Let one sentence run long and follow it with a short one. Merge two same-sized sections or cut one down. Put the qualification you were going to drop in parentheses. Use the number of items the content has, not three.</p>';
    else h += '<p class="hsc-ok">Nothing flagged.</p>';
    if (d3.short) h += '<p class="hsc-note">Fewer than 20 sentences of prose, so this check can note but not fail. Rhythm needs more text to judge.</p>';
    h += '<p class="hsc-note">Repeated section openers and heavy bullet use are not scored: in testing, human writers did both as often as AI.</p></section>';

    // D4
    h += '<section class="hsc-dim hsc-dim4"><h3>4. Stock AI phrasing ' + badge(d4.level) + '</h3>';
    h += '<p class="hsc-lede">The words and constructions models lean on. In our tests, 2023 models leaned on "landscape", "crucial", "leverage", "seamless", "plays a pivotal role", and 2026 Claude models on plain-sounding words like "quietly", "steady", "practical", "matters". Both: negative parallelism ("not just X, but Y", "Y, not X", "rather than") and sentences that start "Additionally" or "Moreover".</p>';
    h += '<div class="hsc-metrics">' + metric('per 1,000 words', round(d4.rate, 1)) + metric('stock words', d4.vocab.length) + metric('negative parallelism', d4.escalators.length) + metric('formula starters', d4.starters.length) + '</div>';
    var d4s = uniqueSentences(d4.escalators.concat(d4.vocab, d4.starters));
    if (d4s.length) h += '<p class="hsc-fix"><strong>Fix:</strong> a synonym will not help. Replace the stock word with the fact it stands in for, state the true half of "not X, but Y" on its own, and delete the starter. If a sentence cannot be made more specific, cut it.</p><ul class="hsc-quotes">' + listItems(d4s.map(function (s) { return quote(s); })) + '</ul>';
    if (d4.antitheses.length) h += '<p class="hsc-fix"><strong>Not scored, check the direction: "It isn\'t X. It\'s Y."</strong> Grounded versions move toward the concrete ("It isn\'t a strategy problem. It\'s a staffing problem."). Inflated versions move toward the abstract.</p><ul class="hsc-quotes">' + d4.antitheses.map(function (p) { return '<li><q>' + highlightSentence(p[0]) + ' ' + highlightSentence(p[1]) + '</q></li>'; }).join('') + '</ul>';
    if (!d4s.length && !d4.antitheses.length) h += '<p class="hsc-ok">Nothing flagged.</p>';
    h += '<p class="hsc-note">One or two of these mean nothing. The check fails on density. Intensity words such as "powerful" are not scored: the human writers we tested used them more than the AI did.</p>';
    h += '</section>';

    // Claims
    var cl = r.claims;
    h += '<section class="hsc-dim hsc-dim5" id="hsc-claims"><h3>Claims to verify <span class="hsc-badge hsc-info">NOT SCORED</span></h3>';
    h += '<p class="hsc-lede">The checker does not know whether a claim is true, and it does not fact-check. It lists every sentence a reader could check (figures, studies, superlatives, quotes and dates) and flags statistics with no source nearby, so you can verify them before you publish.</p>';
    h += '<div class="hsc-metrics">' + metric('claims to verify', cl.total) + metric('no source nearby', cl.unsourced) + metric('statistics', cl.stats) + metric('research claims', cl.research) + metric('superlatives', cl.superlatives) + '</div>';
    if (cl.total) {
      h += '<ul class="hsc-claims">' + cl.list.slice(0, 40).map(function (c) {
        var tags = c.types.map(function (t) { return '<span class="hsc-tag">' + escHtml(t) + '</span>'; }).join('');
        var st = '<span class="hsc-tag ' + (c.unsourced ? 'hsc-tag-warn' : c.sourced ? 'hsc-tag-ok' : 'hsc-tag-own') + '">' + escHtml(c.status) + '</span>';
        return '<li><div class="hsc-ctags">' + tags + st + '</div><q>' + escHtml(c.s.ntext) + '</q></li>';
      }).join('') + (cl.list.length > 40 ? '<li class="hsc-more">+' + (cl.list.length - 40) + ' more, marked in the full text below.</li>' : '') + '</ul>';
      h += '<p class="hsc-fix"><strong>Fix:</strong> name or link the source for every figure, study and quote. Keep the data behind your own figures on file. Cut any number you cannot trace.</p>';
    } else h += '<p class="hsc-ok">No checkable claims found.</p>';
    h += '<p class="hsc-note">Sources are detected from links, "according to", named studies and publication years in or next to the sentence. A source being named does not mean it says what the sentence claims.</p></section>';

    // GEO
    h += '<section class="hsc-dim hsc-geo"><h3>AI citation check (separate from the shape score)</h3>';
    if (r.geo.firstSentence) {
      h += '<p>' + (r.geo.answerFirst ? '<span class="hsc-badge hsc-pass">ANSWER-FIRST</span> ' : '<span class="hsc-badge hsc-notes">' + (r.geo.weakOpen ? 'WARM-UP OPENING' : 'CHECK OPENING') + '</span> ') + 'Opening sentence: <q>' + escHtml(truncate(r.geo.firstSentence, 240)) + '</q></p>';
    }
    h += '<p class="hsc-note">Content written to be cited by AI search wants some things the human-shape advice resists. Keep an answer-first opening, self-contained FAQ answers with figures, a stated method and window, and resolved, extractable claims. Get human shape from specificity and rhythm, not from leaving things messy.</p></section>';

    // AI-style signals
    var ai = r.ai;
    h += '<section class="hsc-dim hsc-dim6" id="hsc-signals"><h3>AI-style signals: ' + ai.band + ' <span class="hsc-badge hsc-info">NOT SCORED</span></h3>';
    h += '<p class="hsc-lede">' + escHtml(aiSentence(ai)) + ' The reading comes from a small model trained on human-written company blog posts from before ChatGPT and AI-written posts on the same titles. It reads structure, not word choice. It cannot prove who wrote a piece: never use it as the only evidence that someone used AI.</p>';
    if (ai.band === 'Too short') {
      h += '<p class="hsc-warn">Add more text. Under 300 words there is not enough structure to read, and the model was never tested on pieces that short.</p>';
    } else {
      h += aiMeter(ai);
      var dr = aiDrivers(ai);
      if (dr.toward.length) h += '<p class="hsc-fix"><strong>What pushed it toward AI-style</strong></p><ul class="hsc-drivers">' + dr.toward.map(driverLine).join('') + '</ul>';
      if (dr.against.length) h += '<p class="hsc-fix"><strong>What pulled it the other way</strong></p><ul class="hsc-drivers hsc-drivers-h">' + dr.against.map(driverLine).join('') + '</ul>';
    }
    var ph = ai.signals.filter(function (g) { return ['vocab', 'escalator', 'frame', 'signpost'].indexOf(g.id) >= 0 && g.examples.length; });
    if (ph.length) h += '<p class="hsc-fix"><strong>Phrases often seen in AI text</strong> <span class="hsc-why">(shown for reference; they do not change the reading, because current AI models rarely use them)</span></p><ul class="hsc-drivers">' + ph.map(function (g) { return '<li><strong>' + escHtml(g.label) + '</strong>: ' + escHtml(g.examples.join(', ')) + '</li>'; }).join('') + '</ul>';
    h += '<div class="hsc-acc"><strong>How accurate is it?</strong> ' + escHtml(AI_ACCURACY) + ' Short, punchy copy with lots of fragments can read as AI-style even when a person wrote it. Tested on business blog posts, handbooks and guides only.</div></section>';

    // Limits
    h += '<details class="hsc-limits"><summary>What this tool cannot check</summary><ul>' +
      '<li>Whether your names, numbers and dates are correct.</li>' +
      '<li>Whether the central claim is repeated more than it needs to be.</li>' +
      '<li>Whether an "It isn\'t X. It\'s Y." line moves toward the concrete or the abstract.</li>' +
      '<li>Who wrote it. The AI-style signals are patterns, not proof: human writers can trip them and edited AI text can avoid them.</li>' +
      '<li>The test that cannot be gamed: give it to a cold reader and ask where they got bored and whether anything rang false.</li>' +
      '</ul></details>';

    // Full text
    h += '<section class="hsc-full"><h3>Your text, marked up</h3>';
    h += '<p class="hsc-legend"><span class="hsc-m hsc-d1">Over-explanation</span> <span class="hsc-m hsc-d2">Category language</span> <span class="hsc-m hsc-d4">Stock phrasing</span> <span class="hsc-sflag hsc-sf5">Claim to verify</span> <span class="hsc-legend-n">Hover a mark for the reason. Grey labels show each section\'s opener / paragraphs / closer.</span></p>';
    h += '<div class="hsc-fulltext">' + renderFullText(r) + '</div></section>';

    return h;
  }

  function renderPrint(r, brand) {
    var d1 = r.d1, d2 = r.d2, d3 = r.d3, d4 = r.d4;
    var utm = function (url, content) {
      var hash = '', i = url.indexOf('#');
      if (i >= 0) { hash = url.slice(i); url = url.slice(0, i); }
      return url + (url.indexOf('?') < 0 ? '?' : '&') + 'utm_source=shape_checker_pdf&utm_medium=referral&utm_campaign=content_shape_checker&utm_content=' + content + hash;
    };
    var toolUrl = brand.toolUrl;
    var date = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    var summary = r.fails === 0 && r.passes === 4 ? 'Passes all four shape checks.' : r.fails === 0 ? 'Passes ' + r.passes + ' of 4 checks, with notes on the rest.' : 'Fails ' + r.fails + ' of 4 shape checks.';
    var h = '<header class="hsc-ph">';
    h += brand.logo ? '<img class="hsc-plogo" src="' + escHtml(brand.logo) + '" alt="' + escHtml(brand.name) + '">' : '<strong class="hsc-pword">' + escHtml(brand.name) + '</strong>';
    h += '<div class="hsc-phmeta"><span class="hsc-ptag">Content Shape Checker report</span><span>' + escHtml(date) + '</span><a href="' + escHtml(utm(toolUrl, 'header')) + '">' + escHtml(toolUrl.replace(/^https?:\/\//, '')) + '</a></div></header>';
    h += '<section class="hsc-pverdict"><p class="hsc-psum">' + escHtml(summary) + '</p>';
    h += '<p class="hsc-pstats">' + r.words + ' words &middot; ' + r.sentenceCount + ' prose sentences &middot; ' + r.sections.length + ' ' + (r.mode === 'headings' ? 'sections' : 'paragraph units') + '</p>';
    h += '<p class="hsc-pstats"><strong>AI-style signals: ' + r.ai.band + '.</strong> ' + escHtml(aiSentence(r.ai)) + (r.ai.band === 'Too short' ? '' : ' A signal, not proof of who wrote it.') + '</p>';
    if (r.claims.total) h += '<p class="hsc-pstats"><strong>' + r.claims.total + (r.claims.total === 1 ? ' claim' : ' claims') + ' to verify</strong>, ' + r.claims.unsourced + ' with no source nearby (see the checklist).</p>';
    if (r.habit) h += '<p class="hsc-phabit"><strong>Strongest machine habit:</strong> ' + escHtml(r.habit) + '</p>';
    if (r.words < 300) h += '<p class="hsc-pnote">Under 300 words, these measures are noisy. Treat the results as a rough read.</p>';
    else if (r.words > 1500) h += '<p class="hsc-pnote">Over 1,500 words, results average across the whole piece.</p>';
    h += '</section>';
    h += '<table class="hsc-score"><thead><tr><th>Check</th><th>Result</th><th>Strikes</th><th>What it measures</th></tr></thead><tbody>';
    [d1, d2, d3, d4].forEach(function (d, i) { h += '<tr><td>' + (i + 1) + '. ' + DIM_NAMES[i + 1] + '</td><td>' + badge(d.level) + '</td><td>' + d.strikes + '</td><td>' + DIM_WHAT[i + 1] + '</td></tr>'; });
    h += '</tbody></table>';

    function block(n, title, level, metricsLine, items, fix, cls) {
      var b = '<section class="hsc-pdim ' + cls + '"><h2>' + n + '. ' + title + ' ' + badge(level) + '</h2><p class="hsc-pmet">' + metricsLine + '</p>';
      if (items.length) b += '<ul class="hsc-quotes">' + items.join('') + '</ul>' + (fix ? '<p class="hsc-pfix"><strong>Fix:</strong> ' + fix + '</p>' : '');
      else b += '<p class="hsc-ok">Nothing flagged.</p>';
      return b + '</section>';
    }
    var d1s = uniqueSentences(d1.phraseHits.concat(d1.restatements, d1.summaries));
    h += block(1, 'Over-explanation', d1.level, d1.strikes + ' flagged sentences, ' + round(d1.rate, 1) + ' per 1,000 words.', d1s.map(function (s) { return quote(s); }), 'cut the explaining sentence and re-read. If meaning dies with the cut, the example was underbuilt. Fix the example, not the explanation.', 'hsc-dim1');
    var d2items = d2.zeroSections.map(function (sec) { return '<li>No numbers or names: ' + escHtml(sec.heading || truncate(sec.sentences[0] ? sec.sentences[0].text : '', 90)) + ' <span class="hsc-why">' + sec.words + ' words</span></li>'; })
      .concat(uniqueSentences(d2.vagueHits).map(function (s) { return quote(s); }));
    h += block(2, 'Real things, named', d2.level, round(d2.density, 1) + ' numbers or names per 100 words. ' + d2.zeroSections.length + ' sections with none. ' + d2.vagueHits.length + ' category phrases.', d2items, 'one proper noun or number per vague slot. Where you cannot name a client, name its shape: "a credit union with 226 staff".', 'hsc-dim2');
    var d3items = d3.flags.filter(function (f) { return !f.note; }).map(function (f) { return '<li>' + escHtml(f.text) + '</li>'; });
    h += block(3, 'Rhythm and variety', d3.level, 'Sentence length spread ' + round(d3.sentSD, 1) + ' words; ' + round(d3.longShare * 100) + '% of sentences 30+ words; section length variation ' + round(d3.secCV, 2) + '; ' + round(d3.asides, 1) + ' asides per 1,000 words; ' + d3.triples.length + ' lists of three.', d3items, 'vary on purpose: one long sentence then a short one, uneven sections, an aside in parentheses, the number of items the content has.', 'hsc-dim3');
    var d4items = uniqueSentences(d4.escalators.concat(d4.vocab, d4.starters)).map(function (s) { return quote(s); });
    h += block(4, 'Stock AI phrasing', d4.level, round(d4.rate, 1) + ' per 1,000 words: ' + d4.vocab.length + ' stock words, ' + d4.escalators.length + ' negative parallelisms, ' + d4.starters.length + ' formula starters.', d4items, 'replace the stock word with the fact it stands in for; state the true half of "not X, but Y"; delete the starter.', 'hsc-dim4');
    (function () {
      var ai = r.ai, x = '<section class="hsc-pdim hsc-dim6"><h2>AI-style signals: ' + ai.band + ' <span class="hsc-badge hsc-info">NOT SCORED</span></h2><p class="hsc-pmet">' + escHtml(aiSentence(ai)) + ' A signal, not proof of who wrote it.</p>';
      if (ai.band !== 'Too short') {
        var dr = aiDrivers(ai);
        x += aiMeter(ai, true);
        if (dr.toward.length) x += '<p class="hsc-pmet"><strong>Toward AI-style:</strong> ' + dr.toward.map(function (d) { return escHtml(AI_FEAT_LABEL[d.k][0].toLowerCase()) + ' (' + (d.higher ? 'more' : 'less') + ' than typical, ' + escHtml(fmtFeat(d.k, d.value)) + ' vs ' + escHtml(fmtFeat(d.k, d.typical)) + ')'; }).join('; ') + '.</p>';
        if (dr.against.length) x += '<p class="hsc-pmet"><strong>The other way:</strong> ' + dr.against.map(function (d) { return escHtml(AI_FEAT_LABEL[d.k][0].toLowerCase()); }).join('; ') + '.</p>';
      }
      x += '<p class="hsc-pmet">' + escHtml(AI_ACCURACY) + '</p></section>';
      h += x;
    })();
    if (r.claims.total) {
      h += '<section class="hsc-pdim hsc-dim5"><h2>Claims to verify <span class="hsc-badge hsc-info">NOT SCORED</span></h2><p class="hsc-pmet">' + r.claims.total + (r.claims.total === 1 ? ' claim, ' : ' claims, ') + r.claims.unsourced + ' with no source nearby. The checker does not judge whether a claim is true. Tick each one off once you have checked it.</p><ul class="hsc-pchecklist">' +
        r.claims.list.map(function (c) { return '<li><span class="hsc-box"></span><div><div class="hsc-ctags">' + c.types.map(function (t) { return '<span class="hsc-tag">' + escHtml(t) + '</span>'; }).join('') + '<span class="hsc-tag ' + (c.unsourced ? 'hsc-tag-warn' : c.sourced ? 'hsc-tag-ok' : 'hsc-tag-own') + '">' + escHtml(c.status) + '</span></div><q>' + escHtml(c.s.ntext) + '</q></div></li>'; }).join('') +
        '</ul></section>';
    }
    if (r.geo.firstSentence) h += '<section class="hsc-pdim hsc-geo"><h2>AI citation check: opening sentence ' + (r.geo.answerFirst ? '<span class="hsc-badge hsc-pass">ANSWER-FIRST</span>' : '<span class="hsc-badge hsc-notes">' + (r.geo.weakOpen ? 'WARM-UP OPENING' : 'CHECK OPENING') + '</span>') + '</h2><p><q>' + escHtml(truncate(r.geo.firstSentence, 260)) + '</q></p></section>';

    h += '<section class="hsc-pappx"><h2>Appendix: your text, marked up</h2><p class="hsc-legend"><span class="hsc-m hsc-d1">Over-explanation</span> <span class="hsc-m hsc-d2">Category language</span> <span class="hsc-m hsc-d4">Stock phrasing</span> <span class="hsc-sflag hsc-sf5">Claim to verify</span></p><div class="hsc-fulltext">' + renderFullText(r) + '</div></section>';
    h += '<section class="hsc-pcta"><h2>Keep going</h2><ul>' +
      '<li><a href="' + escHtml(utm(toolUrl, 'run_again')) + '">Check your next draft free</a><span>' + escHtml(toolUrl.replace(/^https?:\/\//, '')) + '</span></li>' +
      '<li><a href="' + escHtml(utm(toolUrl + '#method', 'method')) + '">How the checker works and the research behind it</a><span>' + escHtml(toolUrl.replace(/^https?:\/\//, '')) + '#method</span></li>' +
      '<li><a href="' + escHtml(utm(brand.site + '/', 'census_home')) + '">' + escHtml(brand.name) + ': which firms AI answers name, and why</a><span>' + escHtml(brand.site.replace(/^https?:\/\//, '')) + '</span></li>' +
      '<li><a href="' + escHtml(utm(brand.site + '/methodology/', 'census_method')) + '">The Census methodology</a><span>' + escHtml(brand.site.replace(/^https?:\/\//, '')) + '/methodology/</span></li>' +
      '</ul><p class="hsc-pdisc">This report audits structure. It is not a fact-checker, and its AI-style signals are not proof of authorship. Human writers can fail these checks and edited AI text can pass them.</p></section>';

    return h;
  }

  function printReport(r, brand) {
    var el = document.createElement('div');
    el.className = 'hsc hsc-print';
    el.innerHTML = renderPrint(r, brand);
    document.body.appendChild(el);
    document.body.classList.add('hsc-printing');
    var oldTitle = document.title;
    document.title = 'content-shape-report-' + new Date().toISOString().slice(0, 10);
    var cleaned = false;
    function cleanup() {
      if (cleaned) return; cleaned = true;
      document.body.classList.remove('hsc-printing');
      if (el.parentNode) el.parentNode.removeChild(el);
      document.title = oldTitle;
      window.removeEventListener('afterprint', cleanup);
    }
    window.addEventListener('afterprint', cleanup);
    var imgs = el.querySelectorAll('img');
    var pending = imgs.length;
    function go() { setTimeout(function () { window.print(); setTimeout(cleanup, 1000); }, 50); }
    if (!pending) go();
    else Array.prototype.forEach.call(imgs, function (im) {
      var done = function () { if (--pending === 0) go(); };
      if (im.complete) done(); else { im.addEventListener('load', done); im.addEventListener('error', function () { im.remove(); done(); }); }
    });
  }

  function reportMarkdown(r) {
    var lines = ['# Content Shape Checker report', '', r.words + ' words, ' + r.sections.length + ' sections.' + (r.claims.total ? ' ' + r.claims.total + (r.claims.total === 1 ? ' claim' : ' claims') + ' to verify, ' + r.claims.unsourced + ' with no source nearby.' : ''), ''];
    lines.push('| Dimension | Result | Strikes |', '|---|---|---|');
    [r.d1, r.d2, r.d3, r.d4].forEach(function (d, i) { lines.push('| ' + (i + 1) + '. ' + DIM_NAMES[i + 1] + ' | ' + verdict(d.level) + ' | ' + d.strikes + ' |'); });
    lines.push('');
    if (r.habit) lines.push('Strongest machine habit: ' + r.habit, '');
    function q(s) { return '- "' + s.text + '"'; }
    var d1s = uniqueSentences(r.d1.phraseHits.concat(r.d1.restatements, r.d1.summaries));
    if (d1s.length) { lines.push('## Over-explanation'); d1s.forEach(function (s) { lines.push(q(s)); }); lines.push(''); }
    var d2s = uniqueSentences(r.d2.vagueHits);
    if (d2s.length || r.d2.zeroSections.length) {
      lines.push('## Real things, named');
      r.d2.zeroSections.forEach(function (sec) { lines.push('- No anchors: ' + (sec.heading || truncate(sec.sentences[0].text, 80))); });
      d2s.forEach(function (s) { lines.push(q(s)); });
      lines.push('');
    }
    var d3f = r.d3.flags.filter(function (f) { return !f.note; });
    if (d3f.length) { lines.push('## Rhythm and variety'); d3f.forEach(function (f) { lines.push('- ' + f.text); }); lines.push(''); }
    var d4s = uniqueSentences(r.d4.escalators.concat(r.d4.vocab, r.d4.starters));
    if (d4s.length) {
      lines.push('## Stock AI phrasing');
      d4s.forEach(function (s) { lines.push(q(s)); });
      lines.push('');
    }
    lines.push('## AI-style signals: ' + r.ai.band + ' (not scored, not proof)', aiSentence(r.ai), '');
    if (r.ai.band !== 'Too short') { var dr = aiDrivers(r.ai); dr.toward.forEach(function (d) { lines.push('- Toward AI-style: ' + AI_FEAT_LABEL[d.k][0] + ', ' + (d.higher ? 'more' : 'less') + ' than typical (' + fmtFeat(d.k, d.value) + ' vs ' + fmtFeat(d.k, d.typical) + ')'); }); dr.against.forEach(function (d) { lines.push('- The other way: ' + AI_FEAT_LABEL[d.k][0]); }); }
    lines.push('', AI_ACCURACY, '');
    if (r.claims.total) {
      lines.push('## Claims to verify (not scored)', r.claims.unsourced + ' of ' + r.claims.total + (r.claims.total === 1 ? ' has' : ' have') + ' no source nearby. The checker does not judge whether a claim is true.', '');
      r.claims.list.forEach(function (c) { lines.push('- [ ] "' + c.s.text + '" (' + c.types.join(', ') + '; ' + c.status + ')'); });
      lines.push('');
    }
    lines.push('Checked with the free Content Shape Checker: https://aivisibilitycensus.com/content-shape-checker/');
    return lines.join('\n');
  }

  /* ------------------------------------------------------------------ */
  /* UI wiring                                                           */
  /* ------------------------------------------------------------------ */

  function init(rootEl) {
    if (rootEl.__hsc) return;
    rootEl.__hsc = true;
    var minWords = parseInt(rootEl.getAttribute('data-min-words') || '80', 10);
    var maxWords = parseInt(rootEl.getAttribute('data-max-words') || '3000', 10);
    var brand = {
      name: rootEl.getAttribute('data-brand') || 'AI Visibility Census',
      site: (rootEl.getAttribute('data-site') || 'https://aivisibilitycensus.com').replace(/\/$/, ''),
      toolUrl: rootEl.getAttribute('data-tool-url') || location.href.split('#')[0].split('?')[0],
      logo: rootEl.getAttribute('data-logo') || ''
    };
    var ta = rootEl.querySelector('.hsc-input');
    var fileIn = rootEl.querySelector('.hsc-file');
    var runBtn = rootEl.querySelector('.hsc-run');
    var clearBtn = rootEl.querySelector('.hsc-clear');
    var out = rootEl.querySelector('.hsc-output');
    var status = rootEl.querySelector('.hsc-status');
    var drop = rootEl.querySelector('.hsc-drop');
    var counter = rootEl.querySelector('.hsc-count');
    var source = null; // { blocks, plain } when the content came from rich paste or a file
    var usageUrl = rootEl.getAttribute('data-usage') || '';
    var inputKind = 'typed';
    // Usage count: event type and coarse buckets only. Never the text, never an identifier, no cookies.
    function wordBand(n) { return n < 300 ? 'under300' : n <= 800 ? '300-800' : n <= 1500 ? '800-1500' : 'over1500'; }
    function track(ev, r) {
      var d = { e: ev, wb: r ? wordBand(r.words) : '', f: r ? r.fails : '', ai: r && r.ai ? r.ai.band : '', src: inputKind };
      if (usageUrl) {
        try {
          var body = JSON.stringify(d);
          if (navigator.sendBeacon) navigator.sendBeacon(usageUrl, new Blob([body], { type: 'application/json' }));
          else fetch(usageUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body, keepalive: true, credentials: 'omit' });
        } catch (e) { /* counting must never break the tool */ }
      }
      try {
        if (typeof window.gtag === 'function') window.gtag('event', 'shape_' + ev, { word_band: d.wb, fails: d.f, ai_band: d.ai, input: d.src });
      } catch (e) { /* ignore */ }
    }

    function setStatus(msg, isErr) {
      status.textContent = msg || '';
      status.className = 'hsc-status' + (isErr ? ' hsc-err' : '');
    }
    function updateCount() {
      var n = wordCount(ta.value);
      counter.textContent = n ? n.toLocaleString('en-US') + ' words' + (n > 1500 ? ' (best under 1,500)' : '') : '';
    }

    ta.addEventListener('paste', function (e) {
      var cd = e.clipboardData;
      if (!cd) return;
      var html = cd.getData('text/html');
      var plain = cd.getData('text/plain');
      if (html && /<(h[1-6]|p|li)\b/i.test(html)) {
        try {
          var blocks = parseHTML(html);
          e.preventDefault();
          var asText = blocks.map(function (b) {
            if (b.type === 'heading') return '\n' + '#'.repeat(Math.min(6, b.level || 2)) + ' ' + b.text + '\n';
            if (b.type === 'bullet') return '- ' + b.text;
            return b.text + '\n';
          }).join('\n').replace(/\n{3,}/g, '\n\n').trim();
          ta.value = asText;
          source = null;
          updateCount();
          inputKind = 'paste-rich';
          setStatus('Pasted with headings and lists preserved.');
        } catch (err) { /* fall back to default paste */ }
      } else if (plain) { source = null; inputKind = 'paste'; }
    });
    ta.addEventListener('input', function (e) { source = null; if (inputKind !== 'paste' && inputKind !== 'paste-rich' && inputKind !== 'file') inputKind = 'typed'; updateCount(); });

    function loadFile(file) {
      if (!file) return;
      var name = file.name.toLowerCase();
      if (file.size > 5 * 1024 * 1024) { setStatus('That file is over 5 MB. Paste the text instead.', true); return; }
      setStatus('Reading ' + file.name + '\u2026');
      inputKind = 'file';
      if (/\.docx$/.test(name)) {
        file.arrayBuffer().then(function (buf) { return unzipEntry(buf, 'word/document.xml'); })
          .then(function (xml) {
            var blocks = parseDocxXml(xml);
            ta.value = blocks.map(function (b) {
              if (b.type === 'heading') return '\n' + '#'.repeat(Math.min(6, b.level || 2)) + ' ' + b.text + '\n';
              if (b.type === 'bullet') return '- ' + b.text;
              if (b.type === 'table') return '| ' + b.text + ' |';
              return b.text + '\n';
            }).join('\n').replace(/\n{3,}/g, '\n\n').trim();
            updateCount();
            setStatus('Loaded ' + file.name + '.');
          })
          .catch(function (err) { setStatus(err.message || 'Could not read that file.', true); });
      } else if (/\.(txt|md|markdown|html?|htm)$/.test(name) || /^text\//.test(file.type)) {
        file.text().then(function (txt) {
          if (/\.html?$/.test(name) || /<(h[1-6]|p)\b/i.test(txt)) {
            var blocks = parseHTML(txt);
            ta.value = blocks.map(function (b) {
              if (b.type === 'heading') return '\n' + '#'.repeat(Math.min(6, b.level || 2)) + ' ' + b.text + '\n';
              if (b.type === 'bullet') return '- ' + b.text;
              return b.text + '\n';
            }).join('\n').replace(/\n{3,}/g, '\n\n').trim();
          } else ta.value = txt;
          updateCount();
          setStatus('Loaded ' + file.name + '.');
        });
      } else if (/\.pdf$/.test(name)) {
        setStatus('PDFs lose their structure when text is extracted, which is what this tool measures. Open the PDF, copy the text and paste it here.', true);
      } else {
        setStatus('Upload a .docx, .txt, .md or .html file, or paste the text.', true);
      }
    }

    fileIn.addEventListener('change', function () { loadFile(fileIn.files[0]); fileIn.value = ''; });
    ['dragenter', 'dragover'].forEach(function (ev) {
      drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add('hsc-over'); });
    });
    ['dragleave', 'drop'].forEach(function (ev) {
      drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove('hsc-over'); });
    });
    drop.addEventListener('drop', function (e) { if (e.dataTransfer && e.dataTransfer.files[0]) loadFile(e.dataTransfer.files[0]); });

    runBtn.addEventListener('click', function () {
      var text = ta.value;
      var n = wordCount(text);
      if (n < minWords) { setStatus('Add at least ' + minWords + ' words. Structure needs room to show.', true); return; }
      if (maxWords && n > maxWords) { setStatus('That is ' + n.toLocaleString('en-US') + ' words. The checker works best on a single article or page of up to about 1,500 words, and stops at ' + maxWords.toLocaleString('en-US') + '. Check one section at a time.', true); return; }
      setStatus('');
      var r = analyze(parseText(text));
      out.innerHTML = renderReport(r) +
        '<div class="hsc-actions"><button type="button" class="hsc-btn hsc-pdf">Download PDF</button> <button type="button" class="hsc-btn hsc-btn-ghost hsc-copy">Copy report</button> <button type="button" class="hsc-btn hsc-btn-ghost hsc-again">Check another piece</button></div>';
      out.hidden = false;
      out.querySelector('.hsc-copy').addEventListener('click', function (e) {
        var md = reportMarkdown(r), btn = e.currentTarget;
        function done() { btn.textContent = 'Copied'; setTimeout(function () { btn.textContent = 'Copy report'; }, 1800); }
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(md).then(done, function () { fallbackCopy(md); done(); });
        else { fallbackCopy(md); done(); }
        track('copy', r);
      });
      var jai = out.querySelector('.hsc-jump-ai'); if (jai) jai.addEventListener('click', function (e) { e.preventDefault(); var t = out.querySelector('#hsc-signals'); if (t) t.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
      var jump = out.querySelector('.hsc-jump-claims'); if (jump) jump.addEventListener('click', function (e) { e.preventDefault(); var t = out.querySelector('#hsc-claims'); if (t) t.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
      Array.prototype.forEach.call(out.querySelectorAll('.hsc-pdf'), function (b) { b.addEventListener('click', function () { printReport(r, brand); track('pdf', r); }); });
      out.querySelector('.hsc-again').addEventListener('click', function () {
        ta.value = ''; inputKind = 'typed'; updateCount(); out.hidden = true; out.innerHTML = ''; ta.focus();
        rootEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
      out.scrollIntoView({ behavior: 'smooth', block: 'start' });
      track('check', r);
      try {
        rootEl.dispatchEvent(new CustomEvent('hsc:analyzed', { bubbles: true, detail: { words: r.words, passes: r.passes, fails: r.fails } }));
      } catch (e) { /* old browsers */ }
    });

    clearBtn.addEventListener('click', function () { ta.value = ''; source = null; inputKind = 'typed'; updateCount(); setStatus(''); out.hidden = true; out.innerHTML = ''; });
  }

  function fallbackCopy(t) {
    var el = document.createElement('textarea');
    el.value = t; el.setAttribute('readonly', ''); el.style.position = 'absolute'; el.style.left = '-9999px';
    document.body.appendChild(el); el.select();
    try { document.execCommand('copy'); } catch (e) { /* ignore */ }
    document.body.removeChild(el);
  }

  var api = { renderPrint: renderPrint, analyze: analyze, parseText: parseText, splitSentences: splitSentences, unzipEntry: unzipEntry, reportMarkdown: reportMarkdown };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; api.AI_MODEL = AI_MODEL;
  if (typeof document !== 'undefined') {
    root.HumanShapeChecker = api;
    var boot = function () { Array.prototype.forEach.call(document.querySelectorAll('[data-hsc]'), init); };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
    else boot();
  }
})(typeof window !== 'undefined' ? window : this);

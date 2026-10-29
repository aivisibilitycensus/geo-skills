# Example: local test run on synthetic pages

A real run of `scripts/schema_parity.py` on the synthetic pages in this folder (`sample-*.html`). Every business, person, address and phone number is fictional (555-01xx numbers are reserved for fiction). The pages were served from a local `python3 -m http.server 8765` so that URL fetching and `--check-links` could be tested without relying on live sites; that is why URLs point at 127.0.0.1. The output below is pasted unedited.

Planted problems, so you can see what each check catches:

| Page | Planted mismatches |
|---|---|
| sample-dental-faq.html (Dentist + FAQPage) | Phone in schema differs from the number shown; one FAQ answer reworded with a different duration; one FAQ answer only in a `display:none` element; one schema question not on the page; one page question not in the schema; one sameAs URL returns 404 |
| sample-coffee-product.html (Product) | Price 18.50 in schema, $19.50 on page; InStock vs "Sold out"; reviewCount 212 vs 187 |
| sample-plumbing-article.html (BlogPosting) | Headline differs from h1 and title; dateModified not shown on page |
| sample-js-injected.html | JSON-LD and content only exist after JavaScript runs |
| sample-broken-jsonld.html | Trailing comma makes the JSON-LD invalid |
| sample-review-microdata.html | Review matches; logo URL returns 404; has a microdata item |

## `python3 scripts/schema_parity.py http://127.0.0.1:8765/sample-dental-faq.html --check-links`

```
Schema parity check: http://127.0.0.1:8765/sample-dental-faq.html
HTTP status: 200
View checked: raw HTML (no JavaScript)
JSON-LD blocks: 1; types: Dentist, FAQPage
Microdata items: 0; RDFa attributes: 0
Checked: Dentist, FAQPage

Findings: 5 high, 1 medium, 1 low. Confirmed on page: 11.

[HIGH] Dentist | telephone
  Matches a tel: link, but the number shown on the page is different
  schema: "+1-555-0142"
  page:   "tel: links: +15550142; numbers shown: 5550147"

[HIGH] FAQPage | Answer to: Do you offer weekend appointments?
  Not found on the visible page (similarity 0.39)
  schema: "Yes, we are open every Saturday from 9am to 1pm."
  page:   "yes we accept new patients of all ages and"

[HIGH] FAQPage | Answer to: How long does a checkup take?
  Wording differs and the schema has numbers the page does not show: 45 (similarity 0.79)
  schema: "A standard checkup and cleaning takes about 45 minutes."
  page:   "a standard checkup and cleaning usually takes around"

[HIGH] FAQPage | Answer to: Is parking available?
  Text is only in a hidden element (hidden, aria-hidden or display:none)
  schema: "Free parking is available behind the building."
  page:   "Free parking is available behind the building."

[HIGH] FAQPage | Question: Do you offer weekend appointments?
  Not found on the visible page (similarity 0.47)
  schema: "Do you offer weekend appointments?"
  page:   "do you accept new patients"

[MEDIUM] Dentist | sameAs
  URL returns HTTP 404
  schema: "http://127.0.0.1:8765/profiles/old-listing"
  page:   "http://127.0.0.1:8765/profiles/old-listing"

[LOW] FAQPage | page question
  Question-style heading on the page is not in the FAQPage schema (fine if it is not part of the FAQ)
  page:   "Do you treat dental emergencies?"

Confirmed:
  ok  Dentist | name: found on page
  ok  Dentist | address.streetAddress: found on page
  ok  Dentist | address.addressLocality: found on page
  ok  Dentist | address.addressRegion: found on page
  ok  Dentist | address.postalCode: found on page
  ok  Dentist | sameAs: HTTP 200
  ok  Dentist | logo: HTTP 200
  ok  FAQPage | Question: Do you accept new patients?: found on page
  ok  FAQPage | Answer to: Do you accept new patients?: found on page
  ok  FAQPage | Question: How long does a checkup take?: found on page
  ok  FAQPage | Question: Is parking available?: found on page
```

## `python3 scripts/schema_parity.py sample-coffee-product.html`

```
Schema parity check: sample-coffee-product.html
View checked: raw HTML (no JavaScript)
JSON-LD blocks: 1; types: Product
Microdata items: 0; RDFa attributes: 0
Checked: Product

Findings: 3 high, 0 medium, 0 low. Confirmed on page: 2.

[HIGH] Product | aggregateRating.reviewCount
  Number not found on the visible page
  schema: "212"
  page:   "50 Sold out. Back in two weeks. Rated 4.8 out of 5 from 187 reviews. A medium roast with notes of cocoa and toasted almond. Tidewick Coffee"

[HIGH] Product | offers.availability
  Page wording contradicts the schema availability
  schema: "InStock"
  page:   "sold out"

[HIGH] Product | offers.price
  Number not found on the visible page
  schema: "18.50"
  page:   "Harbor Fog Blend $19.50 Sold out. Back in two weeks. Rated 4.8 out of 5 from 187 reviews. A mediu"

Confirmed:
  ok  Product | name: found on page
  ok  Product | aggregateRating.ratingValue: number found: ...9.50 Sold out. Back in two weeks. Rated 4.8 out of 5 from 187 reviews. A medium roa...
```

## `python3 scripts/schema_parity.py sample-plumbing-article.html`

```
Schema parity check: sample-plumbing-article.html
View checked: raw HTML (no JavaScript)
JSON-LD blocks: 1; types: BlogPosting
Microdata items: 0; RDFa attributes: 0
Checked: BlogPosting

Findings: 1 high, 1 medium, 0 low. Confirmed on page: 2.

[HIGH] BlogPosting | headline
  Headline does not match the h1 or the title and is not on the page (similarity 0.44)
  schema: "The Complete Guide to Fixing Any Toilet Problem"
  page:   "h1: How to stop a running toilet | title: How to Stop a Running Toilet | Ashgrove Valley Plumbing"

[MEDIUM] BlogPosting | dateModified
  Date not shown on the page
  schema: "2026-10-01"
  page:   "dates on page: 2026-03-04 (<time datetime=2026-03-04> March 4, 2026)"

Confirmed:
  ok  BlogPosting | datePublished: page shows <time datetime=2026-03-04> March 4, 2026
  ok  BlogPosting | author: found on page
```

## `python3 scripts/schema_parity.py sample-js-injected.html`

```
Schema parity check: sample-js-injected.html
View checked: raw HTML (no JavaScript)
JSON-LD blocks: 0; types: none
Microdata items: 0; RDFa attributes: 0
Checked: nothing (no supported types)
WARNING: No JSON-LD found in the raw HTML. If you expected some, it may be injected by JavaScript: re-run with --render, or check Google's Rich Results Test (URL input), which renders the page.

Findings: 0 high, 0 medium, 0 low. Confirmed on page: 0.
```

## `python3 scripts/schema_parity.py sample-js-injected.html --render   (Playwright installed)`

```
Schema parity check: sample-js-injected.html
View checked: rendered
Render: rendered with Playwright (Chromium)
  raw JSON-LD types: none; rendered: Bakery
  words raw: 0; rendered: 6
JSON-LD blocks: 1; types: Bakery
Microdata items: 0; RDFa attributes: 0
Checked: Bakery
WARNING: Some JSON-LD only exists after JavaScript runs: Bakery. Crawlers that do not render JavaScript will not see it.

Findings: 0 high, 0 medium, 0 low. Confirmed on page: 2.

Confirmed:
  ok  Bakery | name: found on page
  ok  Bakery | telephone: digits match a phone number on the page
```

## `python3 scripts/schema_parity.py sample-broken-jsonld.html`

```
Schema parity check: sample-broken-jsonld.html
View checked: raw HTML (no JavaScript)
JSON-LD blocks: 1; types: none
  JSON-LD error: block 1: invalid JSON (Illegal trailing comma before end of object at line 1 col 87)
Microdata items: 0; RDFa attributes: 0
Checked: nothing (no supported types)

Findings: 1 high, 0 medium, 0 low. Confirmed on page: 0.

[HIGH] JSON-LD | syntax
  Block cannot be parsed, so no tool can read it
  schema: "block 1: invalid JSON (Illegal trailing comma before end of object at line 1 col 87)"
```

## `python3 scripts/schema_parity.py sample-review-microdata.html --base-url http://127.0.0.1:8765/review.html --check-links`

```
Schema parity check: sample-review-microdata.html
View checked: raw HTML (no JavaScript)
JSON-LD blocks: 1; types: Organization, Review
Microdata items: 1 (https://schema.org/BreadcrumbList); RDFa attributes: 0
  Note: microdata/RDFa presence is reported but not compared in this version.
Checked: Organization, Product, Review

Findings: 0 high, 1 medium, 0 low. Confirmed on page: 5.

[MEDIUM] Organization | logo
  URL returns HTTP 404
  schema: "http://127.0.0.1:8765/img/missing-logo.png"
  page:   "http://127.0.0.1:8765/img/missing-logo.png"

Confirmed:
  ok  Review | reviewRating.ratingValue: number found: ...review Reviewed by Rowan Asher. Rating: 4 out of 5. Comfortable for long days, bu...
  ok  Review | author: found on page
  ok  Review | reviewBody: found on page
  ok  Product | name: found on page
  ok  Organization | name: found in navigation/header/footer
```

## `python3 scripts/schema_parity.py converted.md   (edge case: Markdown instead of HTML)`

```
Schema parity check: converted.md
View checked: raw HTML (no JavaScript)
JSON-LD blocks: 0; types: none
Microdata items: 0; RDFa attributes: 0
Checked: nothing (no supported types)
WARNING: Input has no <html>, <head> or <body> tag. It may be converted text (for example Markdown from a fetch tool) rather than raw HTML. Structured data in <script> tags is lost in that conversion.
WARNING: No JSON-LD found in the raw HTML. If you expected some, it may be injected by JavaScript: re-run with --render, or check Google's Rich Results Test (URL input), which renders the page.

Findings: 0 high, 0 medium, 0 low. Confirmed on page: 0.
```

## `python3 scripts/schema_parity.py empty.html   (edge case: empty file)`

```
Schema parity check: empty.html
View checked: raw HTML (no JavaScript)
JSON-LD blocks: 0; types: none
Microdata items: 0; RDFa attributes: 0
Checked: nothing (no supported types)
WARNING: Input is empty.
WARNING: No JSON-LD found in the raw HTML. If you expected some, it may be injected by JavaScript: re-run with --render, or check Google's Rich Results Test (URL input), which renders the page.

Findings: 0 high, 0 medium, 0 low. Confirmed on page: 0.
```

## Edge case: Playwright not installed

Run with the `playwright` module blocked, to confirm the script degrades instead of failing:

```
Schema parity check: http://127.0.0.1:8765/sample-js-injected.html
HTTP status: 200
View checked: raw HTML (no JavaScript)
Render: Playwright is not installed (pip install playwright && playwright install chromium); used raw HTML only
JSON-LD blocks: 0; types: none
Microdata items: 0; RDFa attributes: 0
Checked: nothing (no supported types)
WARNING: No JSON-LD found in the raw HTML. If you expected some, it may be injected by JavaScript: re-run with --render, or check Google's Rich Results Test (URL input), which renders the page.

Findings: 0 high, 0 medium, 0 low. Confirmed on page: 0.
```

## Edge cases: missing file and unreachable host

```
Could not read nope.html: [Errno 2] No such file or directory: 'nope.html'
exit code 2
Could not fetch http://127.0.0.1:1/page: URLError: <urlopen error [Errno 111] Connection refused>
exit code 2
```

## Speed

A synthetic 60,000-word page with 15 FAQ items (30 strings to locate) took 9.4 seconds on the test machine. Pages with a very repetitive vocabulary are the slowest case for the fuzzy search.

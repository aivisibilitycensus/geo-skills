# Example: commercial cleaning, Manchester

An example run of the question-set-builder skill. Illustrative only. It is not a Census question set.

## Inputs

- **Service:** commercial and office cleaning
- **Market:** Greater Manchester, UK
- **Buyer:** office manager or operations lead at a business with 10 to 200 staff
- **Constraints buyers mention:** out-of-hours cleaning, contract length, sector rules (medical, food), budget
- **Spelling:** UK English

## Buying decision

An office manager in Greater Manchester is choosing a commercial cleaning company to clean their premises on a regular contract.

## Question set

| ID | Intent | Question |
|---|---|---|
| CLN01 | Vendor selection | Which commercial cleaning companies in Manchester are best for offices? |
| CLN02 | Vendor selection | Can you recommend an office cleaning company in Manchester that cleans out of hours? |
| CLN03 | Vendor selection | Who are the most reliable contract cleaners in Greater Manchester for a 50-person office? |
| CLN04 | Vendor selection | Which cleaning companies in Manchester specialise in GP surgeries and medical clinics? |
| CLN05 | Vendor selection | I run a small office in Salford. Which cleaning companies should I get quotes from? |
| CLN06 | Vendor selection | What are the best cleaning companies in Manchester for warehouses and industrial units? |
| CLN07 | Comparison | Should I use a national cleaning contractor or a local Manchester cleaning company? |
| CLN08 | Comparison | How do the larger commercial cleaning companies in Manchester compare? |
| CLN09 | Specific need | Who can do a one-off deep clean of an office in Manchester before we move in next week? |
| CLN10 | Specific need | Which Manchester cleaning companies offer monthly contracts with no long minimum term? |
| CLN11 | Educational | How much does office cleaning cost per hour in Manchester? |
| CLN12 | Educational | What should I look for when choosing a commercial cleaning company? |

Mix: 6 vendor selection, 2 comparison, 2 specific need, 2 educational.

## CSV

```csv
id,service,intent,question
CLN01,commercial cleaning,vendor selection,Which commercial cleaning companies in Manchester are best for offices?
CLN02,commercial cleaning,vendor selection,Can you recommend an office cleaning company in Manchester that cleans out of hours?
CLN03,commercial cleaning,vendor selection,Who are the most reliable contract cleaners in Greater Manchester for a 50-person office?
CLN04,commercial cleaning,vendor selection,Which cleaning companies in Manchester specialise in GP surgeries and medical clinics?
CLN05,commercial cleaning,vendor selection,I run a small office in Salford. Which cleaning companies should I get quotes from?
CLN06,commercial cleaning,vendor selection,What are the best cleaning companies in Manchester for warehouses and industrial units?
CLN07,commercial cleaning,comparison,Should I use a national cleaning contractor or a local Manchester cleaning company?
CLN08,commercial cleaning,comparison,How do the larger commercial cleaning companies in Manchester compare?
CLN09,commercial cleaning,specific need,Who can do a one-off deep clean of an office in Manchester before we move in next week?
CLN10,commercial cleaning,specific need,Which Manchester cleaning companies offer monthly contracts with no long minimum term?
CLN11,commercial cleaning,educational,How much does office cleaning cost per hour in Manchester?
CLN12,commercial cleaning,educational,What should I look for when choosing a commercial cleaning company?
```

## Sub-questions (content gaps)

For CLN04 (medical clinics), an assistant would likely need to know:

- What extra standards apply to cleaning a GP surgery in England (infection control guidance, clinical waste handling)?
- Which cleaning companies in Manchester say they clean medical premises?
- What do clinics pay for specialist cleaning compared with standard office cleaning?
- What do existing medical clients say about these companies?

A cleaning company that wants to be named for CLN04 needs pages answering these: a medical-premises service page stating the standards it follows, pricing guidance, and named or quoted clinic clients where it has permission.

## Check notes

- CLN05 names Salford rather than Manchester on purpose. Buyers name their own town, and assistants handle the area differently.
- No question names a cleaning company.
- CLN11 and CLN12 will mostly name no company. They are there to see which sources (price guides, directories, trade bodies) get cited.

# Evidence and Identification

Use this reference for literature positioning, evidence tracking, and claim
calibration.

## Start from the claim

Classify each material claim before searching or drafting:

- `descriptive`: a measured pattern in a defined sample;
- `associational`: a conditional relationship without causal identification;
- `predictive`: out-of-sample performance under a stated validation design;
- `causal`: an effect supported by an identification strategy and assumptions;
- `structural`: a model parameter tied to explicit behavioral restrictions;
- `accounting`: an identity or mechanical decomposition.

Do not upgrade a claim because the estimate is precise, robust standard errors
were used, or several specifications have similar signs.

## Evidence ledger

Use `assets/evidence-ledger.csv` when persistent claim tracking is useful. Each
row needs a stable claim ID, the claim text and class, a source or result
locator, one evidence state, a date, an exact location, material limitations,
and the next action.

Allowed states:

- `VERIFIED`: the cited location was inspected and directly supports the claim;
- `PARTIAL`: inspected evidence supports only part of the claim or with limits;
- `UNVERIFIED`: a candidate exists but its relevant content was not inspected;
- `CONTRADICTED`: inspected evidence conflicts with the claim;
- `NOT_APPLICABLE`: the claim does not require empirical or source verification.

Missing evidence stays `UNVERIFIED`; it is not `CONTRADICTED`. Retrieval proves
access, not substantive support.

## Literature discovery

Search provider-neutrally across available scholarly indexes, public metadata,
repositories, cited references, and ordinary web sources. Bound each search to
a stated literature question. Record provider, query, date, position, title,
authors, year, DOI when present, and the original landing page.

A configured SerpApi MCP may be used only as an optional secondary source with
`engine=google_scholar` and structured results. Never scrape Google Scholar,
use a regular-search scholarly-articles shortcut, place a credential in a URL,
or stop the search merely because this provider is unavailable. Disclose the
coverage gap and continue through other sources.

Deduplicate first by normalized DOI, then by normalized title. Search rank,
citation counts, abstracts, and snippets are discovery signals only. Cite the
original work, not a search-results page or provider.

## Identification check

For every causal or structural claim, write down:

1. the target estimand and population;
2. the variation that identifies it;
3. the maintained assumptions;
4. plausible violations and their likely direction;
5. diagnostics that bear on those violations;
6. the interpretation that remains supported after limitations.

If the design supports only description or association, preserve that ceiling
in the title, abstract, tables, and conclusion.

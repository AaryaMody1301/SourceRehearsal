# SourceRehearsal implementation plan

## Product and contribution

Given a baseline country/year population dataset and a report contract, discover public
replacement sources through SerpApi, inspect their data and metadata, and replay the same
report. Show numerical changes separately from changed rankings and threshold decisions.
The contribution is this integrated workflow, not a claim that dataset comparison or
source migration has never existed. No result establishes truth or universal equivalence.

## MVP architecture

- Streamlit: baseline upload or labelled synthetic demo, explicit mappings, contract form,
  live discovery, publisher selection, metadata review, results, JSON/HTML downloads.
- Python data layer: bounded UTF-8 CSV ingestion, explicit column mapping and scaling,
  country/year uniqueness, finite positive values, source metadata and SHA-256 lineage.
- SerpApi Google Search: contract-derived queries, organic result evidence, deduplication,
  supported publisher recognition. No fabricated results or fallback masquerading as search.
- Publisher adapters: World Bank SP.POP.TOTL JSON and OWID population-unwpp Grapher CSV
  plus metadata. Adapters execute only after a matching search result is found. Unsupported
  sources remain visible for manual follow-up. Fixed HTTPS hosts, no arbitrary URL fetches.
- DuckDB: fixed parameterized report SQL. Annual growth joins exactly year minus one;
  deterministic ranks and threshold decisions evaluated for the same country/year scope.
- Evidence: complete contract, retrieval times, file hashes, reviewed metadata, search IDs,
  transforms, missing keys, value deltas, growth deltas, rank shifts, flag flips, caveats.
- Local SQLite search cache: 24-hour TTL, no secrets, conservative 200-attempt budget per
  local cache, explicit reset after billing-cycle review. At most three calls per discovery.

## Milestones and acceptance

1. Contract and replay engine: passing equivalence control, threshold-flip control,
   duplicate/missing-year failures, wrong units and unreviewed metadata hold the verdict.
2. Discovery and download: successful and failed SerpApi fixtures; no result means no
   automatic candidate. Complete World Bank pagination and strict indicator validation.
   OWID metadata/schema checks; no guessed units or undocumented projections.
3. Interface: an offline demo works without a key and is labelled synthetic. A live flow
   visibly records search evidence and downloads. Uploads support explicit mappings.
4. Evidence and reliability: reproducible JSON and escaped standalone HTML, tests,
   linting, CI, clean installation, setup docs, and CLI without Streamlit launch.
5. Submission: real public-data recording under three minutes, public repository,
   AI-development disclosure, and track Open Innovation. Submit before October 10,
   2026 at 23:59 IST; recording and submission are manual owner tasks.

## Verdict policy

"Insufficient evidence" takes precedence over report comparisons when either dataset
fails structural, coverage, unit, definition, license-documentation, or review checks.
When checks pass, distinguish "Changes the report", "Exceeds value tolerance", and
"Passes stated checks". Compare full required scope, not only overlapping available rows.
Never auto-replace a source. Shared upstream UN population estimates are disclosed.
Human review is attestation, not automatic proof of semantic equivalence or legal advice.

## Boundaries

Historical annual population only (1960–2025); maximum 20 ISO3 country codes, 30 years,
10 MB per response/upload, and 100,000 rows. No arbitrary SQL, crawling, login-gated
sources, GDP/other indicators, silent imputations, scheduled monitoring, or paid runtime LLM.
Synthetic tests do not count as evidence of performance on real source replacements.

## Delivery order and remaining external validation

Build phase-wise and deliver one reviewable PR per phase: **three planned PRs total**.
The five acceptance milestones above describe functionality, not five separate PRs.

| Phase / PR | Scope | Acceptance / status |
| --- | --- | --- |
| 1 — MVP | Contract engine, discovery/adapters, interface, evidence, CI | PR #1 merged October 3; 63 tests and real publisher downloads verified |
| 2 — Live-workflow readiness | Search diagnostics, local budget visibility, discovery exports, repeatable live-check command, stale-baseline fix | Deterministic regressions and browser checks; owner-run SerpApi check recorded separately |
| 3 — Submission preparation | Real-data evaluation, final fixes, demo walkthrough, limitations and AI disclosure | Reviewed real-data evidence, public repo, owner-recorded video under three minutes, submission |

Tests run without paid services. Live publisher/API and SerpApi validation are reported
separately from mocked tests; a missing key or unavailable network never counts as a pass.
No new database, runtime LLM, or indicator expansion is planned. Additional PRs are only
for a concrete defect or requested scope change, not per file or minor feature.
Target October 4–8 for owner-run validation and evaluation, October 9 for recording,
and October 10 for submission. Recheck official rules before relying on the schedule.

## Primary references

- https://serpapi.com/search-api
- https://serpapi.com/pricing
- https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures
- https://docs.owid.io/projects/etl/api/chart-api/
- https://ourworldindata.org/population-sources
- https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html

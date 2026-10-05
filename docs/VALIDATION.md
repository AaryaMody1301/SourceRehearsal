# Validation status — October 5, 2026

## Pre-submission audit

### Owner live result and theme follow-up

- The owner-provided source-discovery.json contains three completed searches with IDs,
  no reported API errors, and 29 organic results: nine excluded World Bank baseline
  results and 20 unsupported results. All three exports were local cache hits; the ledger
  records three uncached attempts. No supported OWID replacement was returned. This is
  evidence of search completion, not download/review/rehearsal completion.
- Hard-coded pale app/metric backgrounds and dark headings conflicted with dark-mode
  text. Removed the custom color overrides; all surfaces now use native Streamlit themes.
- The first contrast run also caught white text on Streamlit's default filled red
  rehearsal button at 3.30:1. The action now uses the standard native button style.
- Streamlit dims captions with ancestor opacity. Captions now retain full opacity
  without overriding theme colors; browser contrast checks account for ancestor opacity.
- The report table now shows before/after growth, highlights and ranks together instead
  of burying them among raw population columns.
- Search queries now target dataset pages without forcing ISO3 codes and selected years
  into indexing terms or restricting site searches to one exact URL. Downloaded coverage
  still has to match the contract. New query strings bypass the old query cache entries.
- Optional Refresh cached searches bypasses both caches using SerpApi's documented
  no_cache parameter. It reserves new attempts within the existing ledger and budget;
  a regression verifies fresh results, subsequent cache reuse and budget exhaustion.
- Local suite: 96 passing tests, including refresh and actionable no-candidate UI checks.
  CI now verifies both native light and dark modes, captures screenshots and checks actual
  foreground/background contrast for visible text, labels, controls and result metrics.
  Light/dark checks passed in run 37278074031. Retrieved and inspected both themes'
  screenshots and contrast reports: sampled DOM text minimum 4.74:1 in light mode and
  10.35:1 in dark mode, including ancestor opacity. Zero page errors. Charts/tables were
  inspected visually; these samples are not a full accessibility conformance audit.
  Console logs retain Streamlit sidebar-theme fallback and Vega chart warnings.
  Evidence: https://github.com/AaryaMody1301/SourceRehearsal/actions/runs/37278074031
  Push run 37278067994 also passed Python 3.11/3.13 and both themes; real publisher
  downloads returned nine records each with only the expected human-review hold.
- The revised live queries and a reviewed real-data comparison require an owner rerun.
  The uploaded evidence contains no supported replacement or report verdict. No key was
  configured in this execution, and no live success is inferred from fixtures/web search.

The audit reviewed every application module and test file against README.md,
IMPLEMENTATION_PLAN.md and primary SerpApi, World Bank and OWID documentation.
PR #2 is merged at `97509de80ecb92bb0c6f4a4f21e6317956ebb6c0`.

| Confirmed issue | Fix / evidence |
| --- | --- |
| First-year rank changes could incorrectly pass | Rank every required year; regression swaps 2020 ranks within 0.5% tolerance and expects Changes the report |
| Comparison chart added baseline and replacement growth visually | Display side-by-side bars with an Annual growth (%) axis and clear series labels; AppTest asserts grouping and disabled stacking |
| Invalid HTTPS references could pass | Parse URLs, require a host/valid port, reject embedded credentials/whitespace |
| Fractional World Bank years/pagination silently truncated; boolean counts accepted | Strict integer pagination and four-digit year strings; reject boolean population values |
| Interrupted HTTP body reads escaped error handling | Translate HTTP protocol/read failures into sanitized NetworkError |
| Corrupt SQLite cache crashed UI/CLI | Close connections, translate database errors, show actionable UI/CLI messages without network calls |
| Successful searches without IDs supplied candidates | Require a nonempty string search ID before caching/selecting results |
| Nonstandard NaN/Infinity JSON could break strict exports | Reject non-finite JSON constants at network/publisher boundaries |

- 96 tests pass locally on Python 3.12; Ruff lint and format checks pass. Concurrent
  unique queries cannot exceed the local attempt budget.
- Uploaded CSV mapping/review is exercised through Streamlit AppTest with bytes supplied
  at the upload boundary: missing metadata blocks the result, completed review passes,
  and changing the unit multiplier invalidates the review and report.
- All eight synthetic verdict controls pass. The threshold-flip CLI still shows exactly
  one changed highlight, zero rank changes, and zero beyond-tolerance values. It now
  compares nine report rows instead of six because first-year ranks are included.
- JSON evidence version is now 1.1. First-year growth/delta fields are null, never a
  fabricated zero; first-year highlights are false. HTML handles unavailable growth.
- The browser installer remains blocked locally by an UnknownIssuer certificate error.
  A CI browser job uses the runner's installed Chrome through pinned agent-browser 0.38.2,
  exercises the rendered offline workflow, and saves screenshots/errors as an artifact.
  Browser verification succeeded in run 37273133012 with zero page errors. Both Python
  matrix jobs passed. Screenshots and accessibility snapshots were
  inspected from the artifact. The final browser check also waits for evidence downloads
  before capture and scrolls to the result so streamed charts/controls finish rendering.
  Evidence: https://github.com/AaryaMody1301/SourceRehearsal/actions/runs/37273133012
  The completed chart emitted a Vega scale-binding warning; it is not a page error.
  Visual inspection of completed-chart screenshots identified the stacking issue above.
- Both real publisher downloads succeeded again in run 37272941245: nine scoped records
  each, with only the expected human metadata-review hold. This checks download/coverage,
  not an approved comparison or search-driven discovery.
  Evidence: https://github.com/AaryaMody1301/SourceRehearsal/actions/runs/37272941245
- Owner-provided live search evidence is analysed above. Revised-query validation,
  real-data cross-publisher rehearsal and the recording remain unverified. No credentials
  were configured in this execution. This audit does not rule out undiscovered bugs.

Documentation now explicitly states the first-year policy, URL-syntax/accessibility
distinction, three-letter identifier validation (not a complete ISO registry), and that
the extra audit PR precedes the final submission-preparation PR.

## Phase 2 — live-workflow readiness

- PR #1 is merged into main at `d79d4aed673bcfb2908f8f4461d29e57c0ed39ea`.
- Clean Python 3.12 environment: 70 tests pass; Ruff lint and format checks pass.
- Discovery diagnostics cover supported, unsupported, duplicate, and baseline-excluded
  results. Local budget accounting is visible and cached queries do not consume attempts.
- SerpApi's documented `Success` plus `Fully empty`/error response is recorded as empty
  search evidence, not an authentication failure. Non-success responses still fail closed.
- Streamlit regression checks confirm changing the baseline hides prior discovery choices;
  downloaded evidence includes result-selection diagnostics and search failures.
- `--check-discovery` tests cover missing credentials, successful fixture downloads,
  no candidates, failed searches, and failed downloads. They verify sanitized exports and
  that metadata is never automatically approved. These are fixtures, not live API outcomes.
- Synthetic CLI replay still produces one threshold flip, zero rank changes, and zero
  values beyond tolerance. This is not a real-data evaluation.
- Browser visual verification was attempted, but the browser installer failed with an
  `UnknownIssuer` certificate error fetching Chrome version information. Certificate
  verification was not bypassed; no browser rendering claim is made. AppTest is verified.
- No SerpApi key was configured; live SerpApi search/download verification remains an
  owner-run acceptance check. No new project dependencies were added.

## Phase 1 — completed locally

- Clean virtual environment and editable installation of the app plus development tools.
- 63 passing tests on Python 3.13, including a full Streamlit discovery → download →
  metadata hold → review → rehearsal interaction with mocked SerpApi/World Bank responses.
- Ruff lint and formatting checks.
- CLI run and JSON/HTML evidence generation: the synthetic threshold-flip scenario
  produces exactly one highlight flip with no values beyond the default tolerance.
- Primary API documentation reviewed for SerpApi organic results, World Bank pagination,
  and OWID chart CSV/metadata endpoints. OWID requests long column names explicitly.
- GitHub CI passed on Python 3.11 and 3.13 for the initial implementation commit.
- Ponytail build pass: strict stdlib CSV parsing, readable HTML reports, baseline-source
  exclusion, malformed-response handling, integer-scaling overflow prevention, review resets
  when source evidence changes, and stale-download invalidation regression checks.
- The public-source CLI records real downloads separately from metadata approval. Branch
  pushes run it in a non-blocking CI step; check that step rather than the workflow's overall
  green status to determine whether actual publisher downloads succeeded.

## Live status and remaining checks

- No SerpApi key configured in this execution. The owner-provided export records three
  completed searches from local cache, with no supported replacement; see the follow-up.
- World Bank live download succeeded in GitHub run 37106256855: nine records for
  IND/USA/BRA, 2020–2022; only the expected human metadata-review hold remained.
  The local execution proxy still blocks publisher networking.
- OWID's first live check exposed different metadata and CSV measure names. The adapter
  now aligns exactly one metadata measure with exactly one CSV measure, records both names,
  and rejects ambiguous exports. The fixed live run 37106549046 downloaded all nine OWID
  records successfully, as well as all nine World Bank records. Both retained only the
  expected human metadata-review hold. Metadata key: `Population - Sex: all - Age: all -
  Variant: estimates`; CSV column: `Population (historical estimates)`.
  Evidence: https://github.com/AaryaMody1301/SourceRehearsal/actions/runs/37106549046
- Cross-publisher numerical/decision differences on real datasets.
- Offline browser visual review is complete through CI Chrome screenshots. The live
  discovery/review workflow and screen recording remain unverified; Streamlit AppTest
  exercises fixtures and does not establish live network behavior.

## Owner live acceptance procedure

1. Install from the implementation branch/merged main and run `streamlit run app.py`.
   Optionally set `SERPAPI_API_KEY` locally and first run
   `source-rehearsal --check-discovery --output reports/live-discovery`.
   Keep the generated JSON as observed search/download evidence. Inspect download checks;
   a completed command does not approve metadata or establish a report verdict.
2. Use IND/USA/BRA, 2020–2022; choose World Bank and fetch the baseline.
3. Read the definition, units, and terms; confirm the metadata review.
4. Enter the SerpApi key locally and discover alternatives. Verify three or fewer query
   attempts, real search IDs, and a genuine supported OWID result. Inspect selection
   diagnostics and the local ledger (not the account billing balance). Do not claim the
   discovery passes if no supported replacement was found.
5. Download OWID and review the retrieved metadata; verify required country/year coverage.
6. Rehearse, inspect every result category, and save the JSON evidence with hashes,
   search provenance, publisher metadata, and the shared upstream-source caveat.
7. Record observed results and any schema/network issues here before calling the live
   flow verified. Do not tune the threshold to conceal a real mismatch.

The labelled synthetic controls illustrate behavior and test failure handling. They are
not a benchmark of source replacement quality and cannot support a live-performance claim.


## Final-readiness engineering pass — October 5, 2026

- Fresh Linux virtual environment installed successfully with Python 3.12.3, Streamlit
  1.65.0, pandas 3.0.6 and DuckDB 1.5.6. Windows owner verification remains pending.
- 100 deterministic tests pass, including the real-mode OWID → World Bank UI flow with
  fixture responses, searched CSV provenance/review invalidation, returned-query mismatch
  withholding, and the shared mixed-source guard. Fixtures do not establish live API success.
- Ruff lint and formatting pass. The CLI synthetic control retains one highlight flip.
- Both actual publisher adapters downloaded all nine IND/USA/BRA 2020–2022 records in this
  environment. Each retains a metadata-review hold; neither was auto-approved.
- No key is configured here. Actual SerpApi discovery followed by reviewed real comparison,
  public real-run artifacts, local video and submission remain owner acceptance gates.
- Required Python 3.11/3.13 and light/dark browser jobs run on the final PR; their final
  statuses must be inspected before release. See SUBMISSION.md.

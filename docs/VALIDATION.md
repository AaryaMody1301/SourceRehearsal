# Validation status — October 3, 2026

## Completed locally

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

- SerpApi credentials and live query results: no key configured in this execution.
- World Bank live download succeeded in GitHub run 37106256855: nine records for
  IND/USA/BRA, 2020–2022; only the expected human metadata-review hold remained.
  The local execution proxy still blocks publisher networking.
- OWID's first live check exposed different metadata and CSV measure names. The adapter
  now aligns exactly one metadata measure with exactly one CSV measure, records both names,
  and rejects ambiguous exports. Check the latest live-run logs for verification of that fix.
- Cross-publisher numerical/decision differences on real datasets.
- A real browser visual review and screen recording. Streamlit AppTest exercised the
  widgets and interactions; it does not validate browser rendering.

## Owner live acceptance procedure

1. Install from the implementation branch/merged main and run `streamlit run app.py`.
2. Use IND/USA/BRA, 2020–2022; choose World Bank and fetch the baseline.
3. Read the definition, units, and terms; confirm the metadata review.
4. Enter the SerpApi key locally and discover alternatives. Verify three or fewer query
   attempts, real search IDs, and a genuine supported OWID result. Do not claim the
   discovery passes if no supported replacement was found.
5. Download OWID and review the retrieved metadata; verify required country/year coverage.
6. Rehearse, inspect every result category, and save the JSON evidence with hashes,
   search provenance, publisher metadata, and the shared upstream-source caveat.
7. Record observed results and any schema/network issues here before calling the live
   flow verified. Do not tune the threshold to conceal a real mismatch.

The labelled synthetic controls illustrate behavior and test failure handling. They are
not a benchmark of source replacement quality and cannot support a live-performance claim.

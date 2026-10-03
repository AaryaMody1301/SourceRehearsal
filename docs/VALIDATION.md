# Validation status — October 3, 2026

## Completed locally

- Clean virtual environment and editable installation of the app plus development tools.
- 55 passing tests on Python 3.13, including a full Streamlit discovery → download →
  metadata hold → review → rehearsal interaction with mocked SerpApi/World Bank responses.
- Ruff lint and formatting checks.
- CLI run and JSON/HTML evidence generation: the synthetic threshold-flip scenario
  produces exactly one highlight flip with no values beyond the default tolerance.
- Primary API documentation reviewed for SerpApi organic results, World Bank pagination,
  and OWID chart CSV/metadata endpoints. OWID requests long column names explicitly.

## Not yet validated live

- SerpApi credentials and live query results: no key configured in this execution.
- Runtime downloads from both publishers: an attempted World Bank HTTPS request timed
  out at the execution environment's proxy. That is an environmental observation, not
  evidence that the publisher is down. Search-service retrieval of World Bank indicator
  metadata succeeded, but it does not substitute for an application download test.
- Cross-publisher numerical/decision differences on real datasets.
- CI on GitHub's Python 3.11 and 3.13 runners (check the PR's workflow status).
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

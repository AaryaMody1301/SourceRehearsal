# Submission guide

Status: engineering preparation complete; live owner acceptance and submission pending.
The final PR is not a declaration that the project has been submitted.

## Project description

SourceRehearsal helps analysts assess a replacement public population dataset before
switching a report's source. It discovers alternatives through SerpApi, checks country/year
coverage, units, keys and reviewed metadata, then replays annual growth, rankings and
threshold highlights. JSON and HTML reports preserve source hashes, transformations,
search provenance, differences and unresolved checks.

## SerpApi contribution

Google Search supplies the actual replacement choices; an alternative is never invented
when search fails. Publisher-specific queries prioritize alternatives to the selected
baseline. Search IDs, requested/returned queries and cache labels reach exported evidence.
Supported World Bank and OWID results can be downloaded automatically. Other HTTPS
results can be linked to user-supplied CSV bytes after explicit provenance attestation and
metadata review. That attestation is not automatic verification of the original download.

## Track and disclosures

Recommended track: Open Innovation. Confirm the best fit when completing the form.
Development used ChatGPT/Codex for planning, implementation, debugging, tests and
technical documentation, with the Ponytail plugin guiding minimal changes and dependency
reuse. Calculations use deterministic Python/DuckDB, with no runtime LLM required.
Confirm project history and participant/community information accurately in the entry;
do not describe an existing project as new solely because this PR was added.

## Real acceptance run

1. Install from the final PR/release checkout using the README commands.
2. Start `python -m streamlit run app.py`; set IND,USA,BRA and 2020–2022.
3. Select **Our World in Data**, fetch the baseline and review its definition, scope,
   units and terms. Keep the default 1% growth threshold and 0.5% value tolerance.
4. Configure the SerpApi key locally, then **Discover alternatives**. Inspect requested
   and returned query evidence. Refresh only when necessary; it can consume credits.
5. Select an actual World Bank result, download it and review its metadata/terms.
6. Rehearse and export `source-rehearsal.json` and `source-rehearsal.html`.
7. Verify `synthetic: false`, both reviews, nine required keys, a genuine replacement
   search ID, source hashes, the actual verdict and shared-upstream caveat.
8. Repeat with IND,USA and 2019–2023 if the first run succeeds. Expect ten required keys,
   or record the actual coverage hold. Do not change values to manufacture a finding.

If search finds no supported alternative, keep its evidence and diagnose the response.
Use manual CSV only for a genuinely selected useful result with verified units/definitions.
Unknown metadata or incomplete coverage must remain a hold. Never mark fixture responses
or cached captured reports as fresh API calls.

For a separate search/download check (not metadata approval or rehearsal):

```bash
source-rehearsal --check-discovery --baseline owid --output reports/live-discovery
```

## Demo: aim for 2 minutes 40 seconds

| Time | What to show |
| --- | --- |
| 0:00–0:20 | Analyst problem: compatible columns can still change report conclusions |
| 0:20–1:05 | Real baseline, review, SerpApi discovery and different publisher/search ID |
| 1:05–1:40 | Download, review, actual rehearsal result and shared-upstream caveat |
| 1:40–2:10 | Visibly switch to Synthetic example; show its invented threshold flip |
| 2:10–2:30 | Missing-year hold and readable exported evidence |
| 2:30–2:40 | Population-only scope, repository and reproducible setup |

Configure the key before recording and avoid displaying private account/company information.
Record the application running locally; report the real verdict even if no decisions change.

## Release gates

- [ ] Owner completes real searched comparison and checks the exported evidence.
- [ ] Actual real-run evidence is sanitized, attributed and made available for review.
- [ ] Python CI and light/dark browser jobs pass on the final commit.
- [ ] Owner verifies Windows installation; current automated install checks run on Linux.
- [ ] Public repository and video open in a private window without requesting access.
- [ ] Video is a local screen recording under three minutes.
- [ ] Accurate participant/history information, AI disclosure and agreements are completed.
- [ ] Owner selects Submit project and verifies submitted status.

Target October 9; official deadline October 10, 2026, 23:59 IST. Recheck the official rules
before submission. A saved draft is not a submitted entry.

Official rules: https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html

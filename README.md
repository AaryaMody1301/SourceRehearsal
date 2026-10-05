# SourceRehearsal

**Find a replacement data source. Rehearse what changes in your report before you switch.**

SourceRehearsal searches for public country/year population datasets using SerpApi,
downloads supported sources, checks an explicit contract, and compares annual growth,
population ranks, and threshold highlights. A small value change can flip a report decision
even when every column is compatible. Every result includes evidence and scope limits.

This is a first MVP, not a claim of unprecedented invention or a guarantee of accuracy.
The default example is **synthetic** and clearly labelled. Real discovery requires your own
SerpApi key and network access. Search and publisher errors are shown; no fake live results
are substituted.

## Run locally

Python 3.11 or later:

```bash
git clone https://github.com/AaryaMody1301/SourceRehearsal.git
cd SourceRehearsal
python -m venv .venv
```

Activate the environment:

```bash
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Windows Command Prompt
.venv\Scripts\activate.bat
```

```bash
python -m pip install -e ".[dev]"
python -m streamlit run app.py
```

The sidebar password field accepts your SerpApi key. Alternatively set `SERPAPI_API_KEY`
in the shell before launch. `.env.example` is documentation; `.env` is not automatically
loaded. Never commit your key. It is not included in caches or exported evidence.

Light and dark modes use Streamlit's native theme throughout the app. Change the theme
in the app's settings menu. The result table places before/after growth, highlights and
ranks together; all population values remain available in the expanded evidence table.

## Try the synthetic example (no API key)

1. Keep the default IND/USA/BRA contract for 2020–2022.
2. Use **Synthetic example** and the **Threshold flip** replacement scenario.
3. Click **Rehearse replacement**. One highlight changes, while all values remain within
   the default 0.5% tolerance. This illustrates why compatibility alone is insufficient.
4. Try **Equivalent copy**, **Missing year**, **Wrong units**, and the other controls.
5. Download the full JSON or standalone HTML evidence. HTML shows source snapshots,
   blocking checks, a comparison summary, changed conclusions, and expandable full evidence.

CLI alternative:

```bash
source-rehearsal --scenario "Threshold flip" --output reports/demo
```

## Use real public data

1. Set countries and years in the sidebar (historical years, 1960–2025).
2. Choose **World Bank** and fetch a baseline, or upload your own UTF-8 CSV. Uploaded data
   needs explicit country/year/value mappings, units, source reference, definition, and terms.
3. Review baseline metadata and the publisher's reuse terms.
4. Choose **SerpApi discovery**, enter your key, and discover alternatives.
5. Inspect search evidence. The baseline publisher is excluded from replacement choices.
   The result table explains baseline exclusions, duplicates, and unsupported sources.
   Download discovery JSON even when no replacement is found; it preserves queries,
   search IDs, errors, cache labels, and the local attempt ledger. Changing the baseline
   hides searches made for the previous baseline; discover again for the new source.
   Queries find dataset pages; selected countries/years are validated after download.
   The UI counts excluded baseline and unsupported results. If results are stale, enable
   **Refresh cached searches** before discovery to bypass both local and SerpApi caches.
   This reserves up to three new attempts, may consume credits, and never resets the ledger.
   A successful search with no supported alternative is not a completed live workflow;
   refresh does not guarantee a match. CSV upload remains available with metadata review.
   The MVP automatically downloads only results identifying
   World Bank `SP.POP.TOTL` or OWID `population-unwpp`. Other results remain in the evidence.
6. Select a replacement, download it, and review its metadata before running the rehearsal.

Both publishers may derive estimates from UN World Population Prospects. Matching data
is not independent corroboration. Missing years, unknown units, or unreviewed definitions
block a passing verdict. The app never replaces a source automatically.

To check real publisher downloads without SerpApi credentials:

```bash
source-rehearsal --check-public-sources --output reports/public-sources
```

This downloads real IND/USA/BRA population data for 2020–2022 and records source hashes,
metadata, and validation holds. It does not approve metadata or test SerpApi discovery.
The same non-blocking check runs on branch pushes in CI; inspect that step's actual status
and logs, because an unavailable publisher does not fail the deterministic test jobs.

To verify real SerpApi discovery and download any supported alternative, set
`SERPAPI_API_KEY` in your shell and run:

```bash
source-rehearsal --check-discovery --output reports/live-discovery
```

This uses the same IND/USA/BRA 2020–2022 contract, excludes World Bank as the baseline,
and saves sanitized discovery/download evidence. It shares the app's cache and 200-attempt
guard. Exit 1 means a search/cache error, no supported alternative, or a failed download; exit 2
means missing configuration. Exit 0 verifies search and download completion only, not
metadata approval, complete coverage, or a report verdict. Inspect the recorded checks,
then complete metadata review and rehearsal in the app. Do not paste your key into chat
or include it in a demo recording.

## Results

| Verdict | Meaning |
| --- | --- |
| Insufficient evidence | Required coverage, keys, values, metadata, or review checks failed |
| Changes the report | At least one threshold flag or population rank changes |
| Exceeds value tolerance | Decisions are unchanged but values exceed your allowed difference |
| Passes stated checks | Required checks, value tolerance, ranks, and flags pass for this scope |

Ranks cover **every selected year**, including the first. Annual growth uses the exact
preceding calendar year within the contract; first-year growth is unavailable and is not
highlighted. JSON evidence version 1.1 includes first-year rows with null growth fields.
Rank ties share a rank. Floating
point comparisons use a 1e-9 percentage-point margin at the threshold/tolerance boundary.
No passing result proves semantic equivalence or future stability. Full required coverage
is checked, rather than only the overlapping rows.
Growth bars compare baseline and replacement side by side; their heights are not added.

## Cost and limits

The app needs no paid runtime LLM or hosted database. ChatGPT/Codex can assist development;
calculation and verification are deterministic Python/DuckDB operations.

Discovery uses at most three SerpApi calls per run and a 24-hour local cache. Its SQLite
ledger usage is visible in the discovery panel; cache hits do not increment it.
The ledger conservatively caps uncached attempts at 200, including failures. This is a local
guard, **not** your account's billing-cycle balance. It cannot see calls made elsewhere.
Check your SerpApi dashboard before using it. After reviewing a new billing cycle, deleting
`.cache/search.sqlite` resets the local ledger and cache. No automatic paid upgrade occurs.

Limits: 20 countries, 30 years, 10 MB per response/upload, 100,000 rows. CSV uploads are
not sent to SerpApi; queries use only the country codes, year range, and public indicator.
Dataset downloads use fixed HTTPS publisher hosts and do not follow redirects. Uploaded
source URLs must be valid HTTPS references without embedded credentials; they are never
fetched automatically. Valid syntax does not establish public accessibility or authenticity.
Country identifiers are checked for three-letter syntax, not against a complete ISO registry.
CSV headers must be unique and each row must match the header's field count. Quoted commas
and newlines are supported. Failed refreshes clear the prior download and its report.

## Development and verification

```bash
python -m pytest -q
ruff check .
ruff format --check .
```

Tests exercise report behavior, metadata holds, complete pagination, caching/budget rules,
source recognition, HTML escaping, and Streamlit interactions. Network tests use fixtures;
passing them is **not** a claim of successful live API validation. Record actual live search
and publisher outcomes separately in [docs/VALIDATION.md](docs/VALIDATION.md).
CI also opens the app in Chrome through pinned `agent-browser`, runs the offline rehearsal
in both native themes, and checks page errors and sampled rendered text contrast.
Screenshots, snapshots and contrast reports are saved in `browser-evidence-light` and
`browser-evidence-dark` artifacts. Caption opacity is adjusted for readable guidance text.
This browser check uses synthetic inputs and does not validate live SerpApi discovery.

See [the implementation plan](docs/IMPLEMENTATION_PLAN.md) for milestones and boundaries.

## Hackathon preparation

Suggested track: **Open Innovation**. Explain why SerpApi matters: replacement candidates
come from real organic search results, with query/search ID provenance. Fixed adapters make
those discovered sources executable; adapters are not treated as search results themselves.

Before submitting: run the real-data path, review attribution/terms, make a locally running
screen recording under three minutes, and disclose AI development tools. Recording, final
submission, and verifying remaining credits are owner tasks. Hackathon deadline currently:
October 10, 2026 at 23:59 IST. Verify the official rules before submitting.

Primary documentation:

- [SerpApi Google Search API](https://serpapi.com/search-api)
- [SerpApi pricing](https://serpapi.com/pricing)
- [World Bank API](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures)
- [OWID chart API](https://docs.owid.io/projects/etl/api/chart-api/)
- [OWID population sources](https://ourworldindata.org/population-sources)
- [Hackathon rules](https://serpapi.github.io/serpapi-india-hackathon-2026/rules.html)

## License

Project code is MIT-licensed. Source datasets retain their publisher's licenses and attribution
requirements; the code license does not relicense third-party data. Bundled example values
are project-authored synthetic fixtures.

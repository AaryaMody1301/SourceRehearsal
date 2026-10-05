# Captured real rehearsal — October 5, 2026

This is an owner-provided captured result, not a fresh API response or synthetic fixture.
Generated at 10:18:42 UTC (15:48:42 IST). Inspect the [JSON](source-rehearsal.json) or
[HTML](source-rehearsal.html). The report retains the owner's metadata-review attestations;
these are not independent verification of the sources' semantic equivalence.

Baseline: Our World in Data, Population (historical estimates), population-unwpp.
Replacement: World Bank, Population, total, SP.POP.TOTL, discovered through SerpApi.
Contract: IND/USA/BRA, 2020–2022; growth highlight above 1%; value tolerance 0.5%.
All nine country/year keys are present in each source; both review checks are true.

| Result | Observed value |
| --- | --- |
| Verdict | Exceeds value tolerance |
| US value differences (2020/2021/2022) | −2.3150% / −2.3698% / −2.2070% |
| Values beyond tolerance | 3 of 9 |
| Highlight flips / rank changes | 0 / 0 |

India and Brazil differ only by tiny amounts in this snapshot. The US differences are
observations, not evidence that either publisher is wrong; their cause was not established.
Both publishers reference UN World Population Prospects; World Bank also lists national
statistical offices and other sources. These estimates are not independent corroboration.

The selected fresh search ID is `6ac379727223f4a042b35297`. Requested and returned queries
match; the selected World Bank result occurs in the report's embedded organic results.
The result page has a regional `locations=C4` query. The adapter identifies SP.POP.TOTL
and fetches IND/USA/BRA from the official country API using the user's explicit contract;
it does not use that regional filter as the dataset's scope.

One other query timed out. The supported replacement still completed the required flow.
The separately uploaded source-discovery.json belonged to an earlier unsuccessful attempt
with different search IDs; it is not included here as proof of this successful run.

Review independently recalculated population deltas, annual growth, ranks and highlights,
checked complete unique coverage, and confirmed the HTML's embedded JSON equals the
JSON export. Original full publisher files were not supplied, so raw response hashes are
preserved provenance references, not independently rehashed downloads.

Attribution and terms:

- Our World in Data: https://ourworldindata.org/grapher/population-unwpp
- OWID reuse terms: https://ourworldindata.org/how-to-use-our-world-in-data
- World Bank indicator: https://data.worldbank.org/indicator/SP.POP.TOTL
- World Bank reuse terms: https://datacatalog.worldbank.org/int/public-licenses#cc-by
- UN World Population Prospects: https://population.un.org/wpp/

Publisher data retains its original terms. The repository's MIT code license does not
relicense this evidence or third-party data. Recording and entry submission remain pending.

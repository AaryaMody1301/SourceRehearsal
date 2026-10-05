import math
from dataclasses import asdict
from itertools import product
from urllib.parse import urlsplit

import duckdb
import pandas as pd

from .ingest import timestamp
from .models import MAX_ROWS, Contract, Dataset


def checks(dataset: Dataset, contract: Contract) -> list[str]:
    errors = []
    frame, meta = dataset.frame, dataset.metadata
    if not {"country", "year", "population"} <= set(frame.columns):
        return ["Required normalized columns are absent."]
    if frame.empty or len(frame) > MAX_ROWS:
        return ["Dataset must contain 1–100,000 rows."]
    if frame[["country", "year", "population"]].isna().any().any():
        errors.append("Missing or unparseable country, year, or population values.")
    if not frame["country"].astype("string").str.fullmatch(r"[A-Z]{3}").fillna(False).all():
        errors.append("Country identifiers must be ISO3-style three-letter codes.")
    try:
        if not frame["year"].map(lambda x: math.isfinite(x) and x == int(x)).all():
            errors.append("Years must be finite integers.")
        if not frame["population"].map(lambda x: math.isfinite(x) and 1 <= x <= 1e11).all():
            errors.append("Population must be finite counts between 1 and 100 billion persons.")
    except (TypeError, ValueError):
        errors.append("Year and population must be numeric.")
    if frame.duplicated(["country", "year"]).any():
        errors.append("Duplicate country/year keys; no automatic deduplication is allowed.")
    expected = set(product(contract.countries, range(contract.start_year, contract.end_year + 1)))
    available = set(zip(frame["country"], frame["year"], strict=True))
    missing = sorted(expected - available)
    if missing:
        example = ", ".join(f"{c}/{y}" for c, y in missing[:5])
        errors.append(f"Missing {len(missing)} required country/year keys: {example}.")
    for field in ["indicator", "unit", "kind"]:
        if getattr(meta, field) != getattr(contract, field):
            errors.append(f"Metadata {field} does not match the contract: {getattr(meta, field)}.")
    if not meta.definition.strip():
        errors.append("The indicator definition is undocumented.")
    try:
        source = urlsplit(meta.source_url)
        valid_source = (
            source.scheme == "https"
            and bool(source.hostname)
            and source.username is None
            and source.password is None
            and source.port != 0
            and not any(c.isspace() for c in meta.source_url)
        )
    except ValueError:
        valid_source = False
    if not valid_source and not meta.synthetic:
        errors.append("A valid HTTPS source reference without embedded credentials is required.")
    if meta.license.strip().lower() in ("", "unknown", "unspecified"):
        errors.append("Source license is undocumented; review the publisher's terms.")
    if not meta.reviewed:
        errors.append(
            "Confirm the source definition, units, historical scope, and license evidence."
        )
    return errors


def replay(dataset: Dataset, contract: Contract) -> pd.DataFrame:
    scope = dataset.frame[
        dataset.frame.country.isin(contract.countries)
        & dataset.frame.year.between(contract.start_year, contract.end_year)
    ].copy()
    scope["year"] = scope.year.astype(int)
    with duckdb.connect(":memory:") as connection:
        connection.register("population_data", scope)
        return connection.execute(
            """
            WITH growth AS (
              SELECT current.country, current.year, current.population,
                100.0 * (current.population / previous.population - 1) AS growth_pct
              FROM population_data current
              LEFT JOIN population_data previous
                ON current.country = previous.country AND current.year = previous.year + 1
            )
            SELECT *, COALESCE(growth_pct > ?, FALSE) AS highlighted,
              RANK() OVER (PARTITION BY year ORDER BY population DESC) AS population_rank
            FROM growth ORDER BY year, country
            """,
            [contract.threshold_pct + 1e-9],
        ).df()


def records(frame: pd.DataFrame) -> list[dict]:
    # DuckDB/pandas scalar types become JSON-safe built-in Python values.
    import json

    return json.loads(frame.to_json(orient="records", double_precision=15))


def describe(dataset: Dataset) -> dict:
    return {
        "metadata": asdict(dataset.metadata),
        "raw_sha256": dataset.sha256,
        "retrieved_at": dataset.retrieved_at,
        "rows_loaded": len(dataset.frame),
        "transforms": dataset.transforms,
        "evidence": dataset.evidence,
    }


def compare(baseline: Dataset, candidate: Dataset, contract: Contract) -> dict:
    problems = {"baseline": checks(baseline, contract), "candidate": checks(candidate, contract)}
    if baseline.metadata.synthetic != candidate.metadata.synthetic:
        problems["candidate"].append(
            "Synthetic and real sources cannot be compared; use separate workflows."
        )
    report = {
        "format_version": "1.1",
        "generated_at": timestamp(),
        "contract": asdict(contract),
        "baseline": describe(baseline),
        "candidate": describe(candidate),
        "checks": problems,
        "synthetic": baseline.metadata.synthetic or candidate.metadata.synthetic,
        "caveats": [
            "Results cover only this contract, required country/year scope, and calculations.",
            "An unchanged report does not prove equivalence, accuracy, or future stability.",
            "Metadata review is a human attestation, not automatic verification of the definition.",
        ],
        "values": [],
        "report_rows": [],
        "summary": {},
    }
    shared = sorted(set(baseline.metadata.upstream) & set(candidate.metadata.upstream))
    if shared:
        report["caveats"].append("Shared upstream sources: " + ", ".join(shared))
    if any(problems.values()):
        report["verdict"] = "Insufficient evidence"
        return report
    b = baseline.frame[
        baseline.frame.country.isin(contract.countries)
        & baseline.frame.year.between(contract.start_year, contract.end_year)
    ]
    c = candidate.frame[
        candidate.frame.country.isin(contract.countries)
        & candidate.frame.year.between(contract.start_year, contract.end_year)
    ]
    values = b.merge(
        c, on=["country", "year"], suffixes=("_baseline", "_candidate"), validate="one_to_one"
    )
    values["delta_pct"] = 100 * (values.population_candidate / values.population_baseline - 1)
    values["exceeds_tolerance"] = values.delta_pct.abs() > contract.value_tolerance_pct + 1e-9
    decisions = replay(baseline, contract).merge(
        replay(candidate, contract),
        on=["country", "year"],
        suffixes=("_baseline", "_candidate"),
        validate="one_to_one",
    )
    decisions["growth_delta_pp"] = decisions.growth_pct_candidate - decisions.growth_pct_baseline
    decisions["flag_changed"] = decisions.highlighted_baseline != decisions.highlighted_candidate
    decisions["rank_changed"] = (
        decisions.population_rank_baseline != decisions.population_rank_candidate
    )
    report["values"] = records(values.sort_values(["year", "country"]))
    report["report_rows"] = records(decisions)
    report["summary"] = {
        "required_keys": len(values),
        "decision_rows": len(decisions),
        "flag_changes": int(decisions.flag_changed.sum()),
        "rank_changes": int(decisions.rank_changed.sum()),
        "values_exceeding_tolerance": int(values.exceeds_tolerance.sum()),
        "max_absolute_value_delta_pct": float(values.delta_pct.abs().max()),
    }
    if decisions.flag_changed.any() or decisions.rank_changed.any():
        report["verdict"] = "Changes the report"
    elif values.exceeds_tolerance.any():
        report["verdict"] = "Exceeds value tolerance"
    else:
        report["verdict"] = "Passes stated checks"
    return report

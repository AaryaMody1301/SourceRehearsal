import json
from dataclasses import replace

import pytest

from source_rehearsal import demo
from source_rehearsal.engine import compare, replay
from source_rehearsal.evidence import to_html, to_json
from source_rehearsal.ingest import csv_dataset, read_csv
from source_rehearsal.models import Contract, Mapping


@pytest.mark.parametrize(
    "scenario,verdict",
    [
        ("Equivalent copy", "Passes stated checks"),
        ("Threshold flip", "Changes the report"),
        ("Rank shift", "Changes the report"),
        ("Exceeds tolerance", "Exceeds value tolerance"),
        ("Missing year", "Insufficient evidence"),
        ("Duplicate key", "Insufficient evidence"),
        ("Wrong units", "Insufficient evidence"),
        ("Unreviewed definition", "Insufficient evidence"),
    ],
)
def test_controls(scenario, verdict):
    result = compare(demo.baseline(), demo.candidate(scenario), demo.demo_contract())
    assert result["verdict"] == verdict
    assert json.loads(to_json(result))["synthetic"] is True


def test_small_value_change_can_flip_a_decision():
    result = compare(demo.baseline(), demo.candidate("Threshold flip"), demo.demo_contract())
    assert result["summary"]["flag_changes"] == 1
    assert result["summary"]["values_exceeding_tolerance"] == 0
    change = next(r for r in result["report_rows"] if r["flag_changed"])
    assert (change["country"], change["year"]) == ("IND", 2022)
    assert change["highlighted_baseline"] is False
    assert change["highlighted_candidate"] is True


def test_threshold_boundary_is_not_highlighted():
    row = replay(demo.baseline(), demo.demo_contract()).query("country == 'IND' and year == 2021")
    assert not row.iloc[0].highlighted


def test_missing_predecessor_never_becomes_two_year_growth():
    data = demo.candidate("Missing year")
    rows = replay(data, demo.demo_contract())
    assert rows[rows.country == "IND"].empty
    assert compare(demo.baseline(), data, demo.demo_contract())["report_rows"] == []


def test_missing_baseline_blocks_comparison():
    result = compare(demo.candidate("Missing year"), demo.baseline(), demo.demo_contract())
    assert result["verdict"] == "Insufficient evidence"
    assert result["checks"]["baseline"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 0, 0.000001, 1e308])
def test_invalid_population_cannot_pass(value):
    data = demo.baseline()
    data.frame = data.frame.astype({"population": float})
    data.frame.loc[0, "population"] = value
    result = compare(demo.baseline(), data, demo.demo_contract())
    assert result["verdict"] == "Insufficient evidence"
    to_json(result)


@pytest.mark.parametrize(
    "field,value",
    [("indicator", "gdp"), ("kind", "projection"), ("license", "unknown"), ("definition", "")],
)
def test_semantic_unknowns_block_result(field, value):
    data = demo.baseline()
    data.metadata = replace(data.metadata, **{field: value})
    assert (
        compare(demo.baseline(), data, demo.demo_contract())["verdict"] == "Insufficient evidence"
    )


def test_entire_required_scope_not_just_overlap():
    contract = replace(demo.demo_contract(), end_year=2023)
    result = compare(demo.baseline(), demo.baseline(), contract)
    assert "Missing 3 required" in " ".join(result["checks"]["candidate"])


def test_shuffled_rows_have_same_result():
    data = demo.baseline()
    data.frame = data.frame.sample(frac=1, random_state=7)
    assert compare(demo.baseline(), data, demo.demo_contract())["verdict"] == "Passes stated checks"


def test_ranking_ties_are_equal_and_deterministic():
    data = demo.baseline()
    data.frame.loc[data.frame.country == "BRA", "population"] = data.frame.loc[
        data.frame.country == "USA", "population"
    ].values
    ranks = replay(data, demo.demo_contract()).query("year == 2022")
    assert ranks.query("country in ['BRA','USA']").population_rank.tolist() == [1, 1]


def test_explicit_scale_and_mapping():
    data = csv_dataset(
        b"Code,Year,Count\nind,2020,1\n",
        Mapping("Code", "Year", "Count", 1000),
        demo.demo_metadata(),
    )
    assert data.frame.iloc[0].to_dict() == {"country": "IND", "year": 2020, "population": 1000}
    with pytest.raises(ValueError, match="three different"):
        csv_dataset(
            demo.BASELINE, Mapping("country", "country", "population"), demo.demo_metadata()
        )


def test_html_escapes_untrusted_source_text():
    data = demo.baseline()
    data.metadata = replace(data.metadata, publisher="<script>alert(1)</script>")
    html = to_html(compare(data, data, demo.demo_contract()))
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_shared_upstream_is_disclosed():
    data = demo.baseline()
    data.metadata = replace(data.metadata, upstream=("UN WPP",))
    result = compare(data, data, demo.demo_contract())
    assert "Shared upstream sources: UN WPP" in result["caveats"]


def test_contract_and_upload_limits():
    with pytest.raises(ValueError):
        Contract(("IND",), 2020, 2020)
    with pytest.raises(ValueError):
        Contract(("IND", "IND"), 2020, 2022)
    with pytest.raises(ValueError):
        Contract(("IND",), 2020, 2022, value_tolerance_pct=float("nan"))
    with pytest.raises(ValueError):
        read_csv(b"x" * (10 * 1024 * 1024 + 1))
    with pytest.raises(ValueError):
        read_csv(b"")


def test_noninteger_year_fails():
    data = demo.baseline()
    data.frame = data.frame.astype({"year": float})
    data.frame.loc[0, "year"] = 2020.5
    assert compare(data, data, demo.demo_contract())["verdict"] == "Insufficient evidence"

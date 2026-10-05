"""Run with: streamlit run app.py"""

import json
import os
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path

import pandas as pd
import streamlit as st

from source_rehearsal import demo
from source_rehearsal.discovery import Candidate, SearchClient
from source_rehearsal.engine import compare
from source_rehearsal.evidence import to_html, to_json
from source_rehearsal.ingest import csv_dataset, read_csv
from source_rehearsal.models import Contract, Mapping, Metadata
from source_rehearsal.network import HttpClient
from source_rehearsal.publishers import download, world_bank

st.set_page_config(page_title="SourceRehearsal", page_icon="🔁", layout="wide")
st.markdown(
    """<style>
.stApp {background: #f8faf6;} h1,h2,h3 {color: #174b3c;}
div[data-testid="stMetric"] {background: #eef3eb; padding: 18px; border-radius: 12px;}
</style>""",
    unsafe_allow_html=True,
)
st.title("SourceRehearsal")
st.write("Find a replacement data source. See what changes in your report before you switch.")


def fingerprint(value):
    return sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def review(data, prefix):
    meta = data.metadata
    with st.expander(f"Review {prefix} source evidence", expanded=not meta.reviewed):
        st.write(f"Publisher: {meta.publisher}")
        st.write(f"Source: {meta.source_url}")
        st.write(f"Definition: {meta.definition or 'Undocumented'}")
        st.write(f"Indicator: {meta.indicator} · Unit: {meta.unit} · Type: {meta.kind}")
        st.write(f"License reference: {meta.license}")
        if meta.upstream:
            st.write("Upstream: " + ", ".join(meta.upstream))
        with st.expander("Raw publisher evidence and transformations"):
            st.json(data.evidence)
            st.write(data.transforms)
        if meta.synthetic:
            st.caption("Project-authored synthetic fixture. No publisher data is represented.")
            return data
        reviewed = st.checkbox(
            "I reviewed the definition, units, country/year meaning, scope, and reuse terms.",
            key=prefix
            + "_review_"
            + fingerprint([data.sha256, asdict(meta), data.transforms, data.evidence]),
        )
        return replace(data, metadata=replace(meta, reviewed=reviewed))


def upload_dataset(prefix):
    file = st.file_uploader(f"{prefix} CSV", type=["csv"], key=prefix + "_file")
    if not file:
        st.info("Upload a UTF-8 CSV containing ISO3 country codes, years, and population values.")
        return None
    raw = file.getvalue()
    try:
        frame = read_csv(raw)
    except ValueError as exc:
        st.error(str(exc))
        return None
    st.dataframe(frame.head(10), hide_index=True)
    columns = list(frame.columns)
    mapped = []
    for label, preferred in [
        ("Country", "country"),
        ("Year", "year"),
        ("Population", "population"),
    ]:
        index = columns.index(preferred) if preferred in columns else 0
        mapped.append(st.selectbox(label + " column", columns, index=index, key=prefix + label))
    scale = st.selectbox("Population unit multiplier", [1, 1000, 1_000_000], key=prefix + "_scale")
    st.caption(
        "Use 1 for persons, 1,000 for thousands, or 1,000,000 for millions; verify the source."
    )
    publisher = st.text_input("Publisher", key=prefix + "_publisher")
    source_url = st.text_input("Public HTTPS source URL", key=prefix + "_url")
    definition = st.text_area(
        "Population definition and historical scope evidence", key=prefix + "_def"
    )
    license_ref = st.text_input("License name or terms URL", key=prefix + "_license")
    attested = st.checkbox(
        "This measure is annual total population estimates in the mapped units.",
        key=prefix + "_indicator",
    )
    meta = Metadata(
        publisher,
        source_url,
        indicator="population_total" if attested else "unknown",
        unit="persons" if attested else "unknown",
        kind="estimate" if attested else "unknown",
        license=license_ref,
        definition=definition,
    )
    try:
        return review(csv_dataset(raw, Mapping(*mapped, scale=scale), meta), prefix)
    except ValueError as exc:
        st.error(str(exc))
        return None


with st.sidebar:
    st.header("Report contract")
    country_text = st.text_input("ISO3 countries (comma separated)", "IND,USA,BRA")
    start_year = st.number_input("First year", 1960, 2024, 2020)
    end_year = st.number_input("Last year", 1961, 2025, 2022)
    threshold = st.number_input("Highlight growth above (%)", value=1.0, step=0.1)
    tolerance = st.number_input(
        "Acceptable population difference (%)", min_value=0.0, value=0.5, step=0.1
    )
    st.caption("Full coverage is required for every selected country and year.")
    st.divider()
    key = st.text_input("SerpApi key", type="password", value=os.environ.get("SERPAPI_API_KEY", ""))
    st.caption("Used for live search only. Never included in evidence reports.")

try:
    contract = Contract(
        tuple(c.strip().upper() for c in country_text.split(",") if c.strip()),
        int(start_year),
        int(end_year),
        threshold,
        tolerance,
    )
except ValueError as exc:
    st.error(str(exc))
    st.stop()

scope_id = fingerprint([contract.countries, contract.start_year, contract.end_year])
left, right = st.columns(2, gap="large")
with left:
    st.header("1. Baseline")
    baseline_mode = st.radio(
        "Baseline source", ["Synthetic example", "Upload CSV", "World Bank"], horizontal=True
    )
    baseline = None
    if baseline_mode == "Synthetic example":
        st.warning(
            "Synthetic demonstration: these numbers are invented, including the country values."
        )
        baseline = demo.baseline()
        st.dataframe(baseline.frame, hide_index=True)
    elif baseline_mode == "Upload CSV":
        baseline = upload_dataset("Baseline")
    else:
        if st.button("Fetch World Bank baseline"):
            st.session_state.pop("wb_baseline", None)
            st.session_state.pop("report", None)
            try:
                with st.spinner("Loading population data and indicator metadata…"):
                    st.session_state["wb_baseline"] = (scope_id, world_bank(contract, HttpClient()))
            except ValueError as exc:
                st.error(str(exc))
        saved = st.session_state.get("wb_baseline")
        if saved and saved[0] == scope_id:
            baseline = review(saved[1], "Baseline")
            st.dataframe(baseline.frame, hide_index=True)
        else:
            st.info("Fetch a source snapshot for the selected countries and years.")

with right:
    st.header("2. Replacement")
    replacement_mode = st.radio(
        "Replacement source",
        ["Synthetic scenario", "SerpApi discovery", "Upload CSV"],
        horizontal=True,
    )
    candidate = None
    if replacement_mode == "Synthetic scenario":
        scenario = st.selectbox("Scenario", demo.SCENARIOS)
        candidate = demo.candidate(scenario)
        st.caption("Synthetic controls demonstrate behavior; they do not benchmark real datasets.")
        st.dataframe(candidate.frame, hide_index=True)
    elif replacement_mode == "Upload CSV":
        candidate = upload_dataset("Replacement")
    else:
        st.write("Search for public total population datasets matching this contract.")
        baseline_url = baseline.metadata.source_url if baseline else ""
        discovery_id = fingerprint([scope_id, baseline_mode, baseline_url])
        client, usage = None, None
        if key.strip():
            try:
                client = SearchClient(key, Path(".cache/search.sqlite"))
                usage = client.usage()
            except ValueError as exc:
                client = None
                st.error(str(exc))
        if st.button("Discover alternatives", disabled=client is None):
            st.session_state.pop("discovery", None)
            st.session_state.pop("live_candidate", None)
            st.session_state.pop("report", None)
            with st.spinner("Searching up to three queries…"):
                try:
                    result = client.discover(contract, baseline_url)
                    usage = result["local_budget"]
                    st.session_state["discovery"] = (discovery_id, result)
                except ValueError as exc:
                    st.error(str(exc))
        if client:
            st.caption(
                f"Local search guard: {usage['attempts']}/{usage['limit']} uncached attempts used; "
                f"{usage['remaining']} remaining. Not your account balance. "
                "At most 3 new attempts per run; cached queries need none."
            )
        if not key.strip():
            st.info("Enter your SerpApi key in the sidebar to enable live discovery.")
        saved = st.session_state.get("discovery")
        if saved and saved[0] == discovery_id:
            discovery = saved[1]
            cached_count = sum(search["cached"] for search in discovery["searches"])
            st.caption(
                f"{len(discovery['searches'])} completed queries · "
                f"{cached_count} local cache hits · "
                f"{len(discovery['errors'])} errors · {len(discovery['candidates'])} candidates"
            )
            for error in discovery["errors"]:
                st.warning(error["error"])
            if discovery["diagnostics"]:
                with st.expander("Why results were selected or skipped"):
                    st.dataframe(pd.DataFrame(discovery["diagnostics"]), hide_index=True)
            with st.expander("Search evidence, including unsupported results"):
                st.json(discovery)
            st.download_button(
                "Download discovery evidence",
                to_json(
                    {"contract": asdict(contract), "baseline_source": baseline_url, **discovery}
                ),
                "source-discovery.json",
                "application/json",
            )
            found = discovery["candidates"]
            if found:
                selected = st.selectbox(
                    "Supported replacement",
                    range(len(found)),
                    format_func=lambda i: found[i]["publisher"],
                )
                chosen = Candidate(**found[selected])
                choice_id = fingerprint([scope_id, asdict(chosen)])
                st.write(chosen.title)
                st.write(chosen.source_url)
                if st.button("Download replacement"):
                    st.session_state.pop("live_candidate", None)
                    st.session_state.pop("report", None)
                    try:
                        with st.spinner("Downloading data and metadata…"):
                            loaded = download(chosen, contract)
                            loaded.evidence["searches"] = discovery["searches"]
                            loaded.evidence["search_diagnostics"] = discovery["diagnostics"]
                            loaded.evidence["search_errors"] = discovery["errors"]
                            st.session_state["live_candidate"] = (choice_id, loaded)
                    except ValueError as exc:
                        st.error(str(exc))
                loaded = st.session_state.get("live_candidate")
                if loaded and loaded[0] == choice_id:
                    candidate = review(loaded[1], "Replacement")
                    st.dataframe(candidate.frame, hide_index=True)
            else:
                st.info(
                    "No supported alternative source found. The baseline source is excluded; "
                    "search evidence is available above."
                )

st.divider()
if baseline is None or candidate is None:
    st.info("Load both datasets to rehearse the report.")
    st.stop()

input_id = fingerprint(
    {
        "contract": asdict(contract),
        "baseline": baseline.sha256,
        "candidate": candidate.sha256,
        "bmeta": asdict(baseline.metadata),
        "cmeta": asdict(candidate.metadata),
        "btransforms": baseline.transforms,
        "ctransforms": candidate.transforms,
        "bevidence": baseline.evidence,
        "cevidence": candidate.evidence,
    }
)
if st.button("Rehearse replacement", type="primary"):
    st.session_state["report"] = (input_id, compare(baseline, candidate, contract))
saved = st.session_state.get("report")
if not saved or saved[0] != input_id:
    st.caption("Run the rehearsal after loading data or changing the contract.")
    st.stop()

report = saved[1]
st.header("3. Rehearsal result")
if report["synthetic"]:
    st.warning(
        "This result includes synthetic data. It is a demonstration, not real-world validation."
    )
verdict = report["verdict"]
if verdict == "Insufficient evidence":
    st.error(verdict)
    for source, errors in report["checks"].items():
        for error in errors:
            st.write(f"**{source.title()}:** {error}")
else:
    if verdict == "Passes stated checks":
        st.success(verdict)
    else:
        st.warning(verdict)
    summary = report["summary"]
    metrics = st.columns(4)
    for slot, label, field in zip(
        metrics,
        ["Required keys", "Highlight flips", "Rank changes", "Beyond tolerance"],
        ["required_keys", "flag_changes", "rank_changes", "values_exceeding_tolerance"],
        strict=True,
    ):
        slot.metric(label, summary[field])
    decisions = pd.DataFrame(report["report_rows"])
    st.subheader("Changes to the report")
    changed = decisions[decisions.flag_changed | decisions.rank_changed]
    st.dataframe(changed if not changed.empty else decisions, hide_index=True)
    chart = decisions.copy()
    chart["label"] = chart.country + " / " + chart.year.astype(str)
    st.bar_chart(chart.set_index("label")[["growth_pct_baseline", "growth_pct_candidate"]])
    st.caption(
        "Ranks cover every selected year. First-year growth is unavailable without a prior "
        "year in the contract and is not highlighted."
    )
    with st.expander("All population values and differences"):
        st.dataframe(pd.DataFrame(report["values"]), hide_index=True)

for caveat in report["caveats"]:
    st.caption(caveat)
json_col, html_col = st.columns(2)
json_col.download_button(
    "Download JSON evidence", to_json(report), "source-rehearsal.json", "application/json"
)
html_col.download_button(
    "Download HTML evidence", to_html(report), "source-rehearsal.html", "text/html"
)

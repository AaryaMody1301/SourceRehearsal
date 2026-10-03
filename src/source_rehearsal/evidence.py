import json
from html import escape

import pandas as pd


def to_json(report: dict) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)


def to_html(report: dict) -> str:
    # All source content is escaped; no scripts, remote resources, or embedded raw HTML.
    payload = escape(to_json(report))
    verdict = escape(report["verdict"])
    banner = (
        "Synthetic demonstration — not real population figures."
        if report["synthetic"]
        else ("Evaluation of supplied source snapshots; review the contract and caveats.")
    )

    def table(rows):
        return pd.DataFrame(rows).to_html(index=False, escape=True, border=0)

    contract = report["contract"]
    scope = escape(
        f"{', '.join(contract['countries'])} · {contract['start_year']}–{contract['end_year']} "
        f"· highlight growth above {contract['threshold_pct']:g}% "
        f"· value tolerance {contract['value_tolerance_pct']:g}%"
    )
    sources = table(
        [
            {
                "Role": role.title(),
                "Publisher": report[role]["metadata"]["publisher"],
                "Source": report[role]["metadata"]["source_url"],
                "Retrieved (UTC)": report[role]["retrieved_at"],
                "SHA-256": report[role]["raw_sha256"],
            }
            for role in ("baseline", "candidate")
        ]
    )
    problems = (
        table(
            [
                {"Source": source.title(), "Issue": issue}
                for source, issues in report["checks"].items()
                for issue in issues
            ]
        )
        if any(report["checks"].values())
        else "<p>Required checks passed for this scope.</p>"
    )
    summary = (
        table(
            [
                {
                    "Required records": report["summary"]["required_keys"],
                    "Highlight flips": report["summary"]["flag_changes"],
                    "Rank changes": report["summary"]["rank_changes"],
                    "Values beyond tolerance": report["summary"]["values_exceeding_tolerance"],
                    "Largest value difference (%)": round(
                        report["summary"]["max_absolute_value_delta_pct"], 6
                    ),
                }
            ]
        )
        if report["summary"]
        else ""
    )
    changed = [row for row in report["report_rows"] if row["flag_changed"] or row["rank_changed"]]
    changes = (
        table(
            [
                {
                    "Country": row["country"],
                    "Year": row["year"],
                    "Growth before (%)": round(row["growth_pct_baseline"], 6),
                    "Growth after (%)": round(row["growth_pct_candidate"], 6),
                    "Highlighted before": row["highlighted_baseline"],
                    "Highlighted after": row["highlighted_candidate"],
                    "Rank before": row["population_rank_baseline"],
                    "Rank after": row["population_rank_candidate"],
                }
                for row in changed
            ]
        )
        if changed
        else (
            "<p>Comparison was blocked by the issues above.</p>"
            if not report["summary"]
            else "<p>No threshold flags or ranks changed.</p>"
        )
    )
    caveats = "".join(f"<li>{escape(item)}</li>" for item in report["caveats"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>SourceRehearsal evidence</title>
    <style>body{{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px;
    color:#18352e;background:#fafbf8}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;
    background:#edf2ed;padding:24px;border-radius:12px}}h1{{color:#176652}}
    section{{overflow-x:auto;margin:24px 0}}
    table{{border-collapse:collapse;width:100%;font-size:14px}}
    th,td{{padding:12px;border-bottom:1px solid #cedbce;text-align:left;overflow-wrap:anywhere}}
    th{{background:#edf2ed}}summary{{cursor:pointer;font-weight:bold}}li{{margin:8px 0}}
    </style></head><body>
    <h1>SourceRehearsal</h1><p>{banner}</p><h2>{verdict}</h2>
    <p>{scope}</p><section><h2>Source snapshots</h2>{sources}</section>
    <section><h2>Data checks</h2>{problems}</section>
    <section><h2>Comparison summary</h2>{summary}</section>
    <section><h2>Changed conclusions</h2>{changes}</section>
    <h2>Interpretation limits</h2><ul>{caveats}</ul>
    <details><summary>Full reproducible evidence</summary><pre>{payload}</pre></details>
    </body></html>"""

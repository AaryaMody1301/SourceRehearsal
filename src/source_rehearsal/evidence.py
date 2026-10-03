import json
from html import escape


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
    return f"""<!doctype html><html lang="en"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>SourceRehearsal evidence</title>
    <style>body{{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px;
    color:#18352e;background:#fafbf8}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;
    background:#edf2ed;padding:24px;border-radius:12px}}h1{{color:#176652}}</style>
    <h1>SourceRehearsal</h1><p>{banner}</p><h2>{verdict}</h2>
    <p>Full contract, provenance, checks, and report comparison:</p><pre>{payload}</pre></html>"""

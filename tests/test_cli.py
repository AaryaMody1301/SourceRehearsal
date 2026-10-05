import json
import sys
from dataclasses import replace

import pytest

from source_rehearsal import cli, demo
from source_rehearsal.network import HttpClient, NetworkError


def test_live_check_requires_environment_key_before_network(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["source-rehearsal", "--check-discovery"])
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 2
    assert "Set SERPAPI_API_KEY" in capsys.readouterr().err
    assert not (tmp_path / ".cache").exists()


def test_live_check_reports_corrupt_cache_without_a_traceback(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SERPAPI_API_KEY", "fixture-secret")
    monkeypatch.setattr(sys, "argv", ["source-rehearsal", "--check-discovery"])
    (tmp_path / ".cache").mkdir()
    (tmp_path / ".cache/search.sqlite").write_bytes(b"not SQLite")
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 1
    output = capsys.readouterr().err
    assert "cache is unavailable or invalid" in output
    assert "fixture-secret" not in output


@pytest.mark.parametrize("outcome", ["download", "empty", "search-error", "download-error"])
def test_discovery_check_exports_evidence_without_approving_metadata(
    monkeypatch, tmp_path, capsys, outcome
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SERPAPI_API_KEY", "fixture-secret")
    monkeypatch.setattr(
        sys, "argv", ["source-rehearsal", "--check-discovery", "--output", "reports/search"]
    )

    def search(self, url):
        if outcome == "search-error":
            raise NetworkError("API unavailable.")
        return {
            "search_metadata": {"status": "Success", "id": "cli-fixture"},
            "search_parameters": {"api_key": "fixture-secret"},
            "organic_results": []
            if outcome == "empty"
            else [
                {
                    "title": "Population",
                    "link": "https://data.worldbank.org/indicator/SP.POP.TOTL",
                }
            ],
        }

    def download(candidate, contract):
        assert candidate.search_id == "cli-fixture"
        if outcome == "download-error":
            raise NetworkError("Publisher unavailable.")
        data = demo.baseline()
        data.metadata = replace(data.metadata, reviewed=False, synthetic=False)
        return data

    monkeypatch.setattr(HttpClient, "json", search)
    monkeypatch.setattr(cli, "download", download)
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == (0 if outcome == "download" else 1)
    raw = (tmp_path / "reports/search.json").read_text()
    assert "fixture-secret" not in raw + capsys.readouterr().out
    result = json.loads(raw)
    assert result["local_budget"]["attempts"] == 3
    if outcome == "download":
        assert not result["downloads"][0]["metadata"]["reviewed"]
        assert result["downloads"][0]["checks"]
    else:
        assert result["status"] == "incomplete"

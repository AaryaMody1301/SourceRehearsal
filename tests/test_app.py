import json
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

from streamlit.testing.v1 import AppTest

from source_rehearsal import demo
from source_rehearsal.network import HttpClient, NetworkError

APP = Path(__file__).parents[1] / "app.py"


def button(app, label):
    return next(item for item in app.button if item.label == label)


def test_default_demo_rehearsal_and_contract_invalidation():
    app = AppTest.from_file(str(APP)).run(timeout=20)
    assert not app.exception
    button(app, "Rehearse replacement").click().run(timeout=20)
    assert not app.exception
    assert any(w.value == "Changes the report" for w in app.warning)
    assert app.session_state["report"][1]["summary"]["flag_changes"] == 1
    app.sidebar.number_input[3].set_value(2.0).run(timeout=20)
    assert not app.exception
    assert not app.metric


def test_equivalent_and_missing_data_scenarios():
    app = AppTest.from_file(str(APP)).run(timeout=20)
    app.selectbox[0].select("Equivalent copy").run()
    button(app, "Rehearse replacement").click().run(timeout=20)
    assert any(item.value == "Passes stated checks" for item in app.success)
    app.selectbox[0].select("Missing year").run()
    button(app, "Rehearse replacement").click().run(timeout=20)
    assert any(item.value == "Insufficient evidence" for item in app.error)
    assert not app.exception


def test_live_discovery_without_key_is_disabled():
    app = AppTest.from_file(str(APP)).run(timeout=20)
    app.radio[1].set_value("SerpApi discovery").run()
    assert button(app, "Discover alternatives").disabled
    assert not app.exception


def test_corrupt_search_cache_does_not_crash_the_app(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".cache").mkdir()
    (tmp_path / ".cache/search.sqlite").write_bytes(b"invalid sqlite data")
    app = AppTest.from_file(str(APP)).run(timeout=20)
    app.sidebar.text_input[1].set_value("fixture-key").run()
    app.radio[1].set_value("SerpApi discovery").run()
    assert not app.exception
    assert button(app, "Discover alternatives").disabled
    assert any("cache is unavailable or invalid" in error.value for error in app.error)


def test_uploaded_csv_mapping_review_export_and_unit_change(monkeypatch):
    # AppTest does not implement upload actions; supply the bytes at that boundary.
    monkeypatch.setattr("streamlit.file_uploader", lambda *args, **kwargs: BytesIO(demo.BASELINE))
    app = AppTest.from_file(str(APP)).run(timeout=20)
    app.radio[1].set_value("Upload CSV").run()
    button(app, "Rehearse replacement").click().run(timeout=20)
    assert app.session_state["report"][1]["verdict"] == "Insufficient evidence"
    for label, value in [
        ("Publisher", "Uploaded synthetic control"),
        ("Public HTTPS source URL", "https://example.com/population"),
        ("License name or terms URL", "Project-authored software fixture"),
    ]:
        next(e for e in app.text_input if e.label == label).set_value(value).run()
    app.text_area[0].set_value(
        "Synthetic annual total population estimates for a software test."
    ).run()
    app.checkbox[0].check().run()
    app.checkbox[1].check().run()
    button(app, "Rehearse replacement").click().run(timeout=20)
    assert app.session_state["report"][1]["verdict"] == "Passes stated checks"
    assert not app.exception
    app.selectbox[3].select(1000).run()
    assert not app.checkbox[1].value
    assert not app.metric
    button(app, "Rehearse replacement").click().run(timeout=20)
    assert app.session_state["report"][1]["verdict"] == "Insufficient evidence"
    assert not app.exception


def test_full_discovery_download_review_and_rehearsal(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    calls = []
    definition = {"text": "Total population."}

    def fake_json(self, url):
        calls.append(urlsplit(url).hostname)
        if urlsplit(url).hostname == "serpapi.com":
            return {
                "search_metadata": {"status": "Success", "id": "integration-fixture"},
                "organic_results": [
                    {
                        "title": "Population, total",
                        "link": "https://data.worldbank.org/indicator/SP.POP.TOTL",
                    }
                ],
            }
        return [{"pages": 1}, [{"id": "SP.POP.TOTL", "sourceNote": definition["text"]}]]

    def fake_get(self, url):
        rows = [
            {
                "indicator": {"id": "SP.POP.TOTL"},
                "countryiso3code": row.country,
                "date": str(row.year),
                "value": int(row.population),
            }
            for row in demo.baseline().frame.itertuples()
        ]
        return json.dumps([{"page": 1, "pages": 1, "total": 9}, rows]).encode()

    monkeypatch.setattr(HttpClient, "json", fake_json)
    monkeypatch.setattr(HttpClient, "get", fake_get)
    app = AppTest.from_file(str(APP)).run(timeout=20)
    app.sidebar.text_input[1].set_value("fixture-key").run()
    app.radio[1].set_value("SerpApi discovery").run()
    button(app, "Discover alternatives").click().run(timeout=20)
    assert len([host for host in calls if host == "serpapi.com"]) == 3
    assert any("3/200 uncached attempts used" in c.value for c in app.caption)
    assert not app.exception
    button(app, "Download replacement").click().run(timeout=20)
    button(app, "Rehearse replacement").click().run(timeout=20)
    assert app.session_state["report"][1]["verdict"] == "Insufficient evidence"
    app.checkbox[0].check().run()
    button(app, "Rehearse replacement").click().run(timeout=20)
    result = app.session_state["report"][1]
    assert result["verdict"] == "Passes stated checks"
    assert result["candidate"]["evidence"]["discovery"]["search_id"] == "integration-fixture"
    assert result["candidate"]["evidence"]["search_diagnostics"]
    assert any("Local search guard:" in c.value for c in app.caption)
    assert "fixture-key" not in json.dumps(result)
    assert not app.exception

    definition["text"] = "Revised population definition."
    button(app, "Download replacement").click().run(timeout=20)
    assert not app.checkbox[0].value  # Same CSV bytes, different evidence needs a fresh review.
    button(app, "Rehearse replacement").click().run(timeout=20)
    assert app.session_state["report"][1]["verdict"] == "Insufficient evidence"

    def failed_get(self, url):
        raise NetworkError("Publisher is unavailable.")

    monkeypatch.setattr(HttpClient, "get", failed_get)
    button(app, "Download replacement").click().run(timeout=20)
    assert "live_candidate" not in app.session_state
    assert "report" not in app.session_state
    assert not app.exception

    monkeypatch.setattr(HttpClient, "get", fake_get)
    app.radio[0].set_value("World Bank").run()
    assert not any(s.label == "Supported replacement" for s in app.selectbox)
    button(app, "Fetch World Bank baseline").click().run(timeout=20)
    assert "wb_baseline" in app.session_state
    assert not any(s.label == "Supported replacement" for s in app.selectbox)
    button(app, "Discover alternatives").click().run(timeout=20)
    assert not app.session_state["discovery"][1]["candidates"]
    assert any("Baseline source excluded" in j.value for j in app.json)
    monkeypatch.setattr(HttpClient, "get", failed_get)
    button(app, "Fetch World Bank baseline").click().run(timeout=20)
    assert "wb_baseline" not in app.session_state
    assert not app.exception

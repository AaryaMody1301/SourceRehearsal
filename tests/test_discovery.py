import json
from concurrent.futures import ThreadPoolExecutor
from http.client import IncompleteRead
from urllib.parse import parse_qs, urlsplit

import pytest

from source_rehearsal.demo import demo_contract
from source_rehearsal.discovery import SearchClient, recognize
from source_rehearsal.network import HttpClient, NetworkError


class SearchFixture:
    def __init__(self, empty=False, error=False):
        self.calls = []
        self.empty, self.error = empty, error

    def json(self, url):
        self.calls.append(url)
        if self.error:
            return {"error": "secret-bearing message that must not be exported"}
        return {
            "search_metadata": {"status": "Success", "id": "fixture-id"},
            "search_parameters": {"api_key": "SUPER-SECRET"},
            "organic_results": []
            if self.empty
            else [
                {"title": "Population", "link": "https://data.worldbank.org/indicator/SP.POP.TOTL"},
                {
                    "title": "Population",
                    "link": "https://ourworldindata.org/grapher/population-unwpp",
                },
                {"title": "GDP", "link": "https://data.worldbank.org/indicator/NY.GDP.MKTP.CD"},
            ],
        }


def test_discovery_uses_queries_deduplicates_and_caches(tmp_path):
    fixture = SearchFixture()
    client = SearchClient("SUPER-SECRET", tmp_path / "cache.sqlite", fixture)
    result = client.discover(demo_contract())
    assert len(fixture.calls) == 3
    assert len(result["candidates"]) == 2
    assert "SUPER-SECRET" not in json.dumps(result)
    assert b"SUPER-SECRET" not in (tmp_path / "cache.sqlite").read_bytes()
    assert all(parse_qs(urlsplit(url).query)["engine"] == ["google"] for url in fixture.calls)
    second = client.discover(demo_contract())
    assert len(fixture.calls) == 3
    assert all(row["cached"] for row in second["searches"])
    assert second["local_budget"] == {"attempts": 3, "limit": 200, "remaining": 197}
    assert {row["reason"] for row in result["diagnostics"]} == {
        "Unsupported source or indicator",
        "Duplicate source",
        "Downloadable candidate; metadata review required",
    }


def test_zero_results_never_invents_candidates(tmp_path):
    result = SearchClient("key", tmp_path / "cache.sqlite", SearchFixture(empty=True)).discover(
        demo_contract()
    )
    assert result["candidates"] == []
    assert result["errors"] == []


def test_refresh_bypasses_both_caches_and_keeps_the_attempt_budget(tmp_path):
    fixture = SearchFixture(empty=True)
    client = SearchClient("key", tmp_path / "cache.sqlite", fixture, budget=6)
    assert not client.discover(demo_contract())["candidates"]
    fixture.empty = False
    result = client.discover(demo_contract(), refresh=True)
    assert len(result["candidates"]) == 2
    assert len(fixture.calls) == result["local_budget"]["attempts"] == 6
    assert all(not row["cached"] for row in result["searches"])
    assert all(parse_qs(urlsplit(url).query)["no_cache"] == ["true"] for url in fixture.calls[3:])
    assert all(row["cached"] for row in client.discover(demo_contract())["searches"])
    assert len(client.discover(demo_contract(), refresh=True)["errors"]) == 3
    assert len(fixture.calls) == 6


def test_baseline_publisher_is_excluded_but_search_evidence_is_kept(tmp_path):
    result = SearchClient("key", tmp_path / "cache.sqlite", SearchFixture()).discover(
        demo_contract(), "https://data.worldbank.org/indicator/SP.POP.TOTL?locations=IN"
    )
    assert [c["publisher"] for c in result["candidates"]] == ["Our World in Data"]
    assert len(result["searches"][0]["organic_results"]) == 3
    assert sum(d["reason"] == "Baseline source excluded" for d in result["diagnostics"]) == 3


def test_failed_search_has_no_fake_candidates_or_secret(tmp_path):
    result = SearchClient("key", tmp_path / "cache.sqlite", SearchFixture(error=True)).discover(
        demo_contract()
    )
    assert result["candidates"] == []
    assert len(result["errors"]) == 3
    assert "secret-bearing" not in json.dumps(result)


def test_budget_reserves_before_call_and_counts_failures(tmp_path):
    fixture = SearchFixture(error=True)
    client = SearchClient("key", tmp_path / "cache.sqlite", fixture, budget=1)
    result = client.discover(demo_contract())
    assert len(fixture.calls) == 1
    assert any("budget" in e["error"] for e in result["errors"])
    assert client.usage() == {"attempts": 1, "limit": 1, "remaining": 0}


def test_concurrent_queries_cannot_overrun_the_local_budget(tmp_path):
    fixture = SearchFixture()
    client = SearchClient("fixture-key", tmp_path / "cache.sqlite", fixture, budget=2)

    def attempt(index):
        try:
            client.search(f"unique query {index}")
            return True
        except NetworkError:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(8)))
    assert sum(results) == len(fixture.calls) == client.usage()["attempts"] == 2


@pytest.mark.parametrize("status", ["Success", "Error"])
def test_documented_empty_results_are_evidence_not_authentication_failure(tmp_path, status):
    class EmptyResponse:
        def json(self, url):
            return {
                "search_metadata": {"status": status, "id": "empty-fixture"},
                "search_information": {"organic_results_state": "Fully empty"},
                "error": "Google hasn't returned any results for this query.",
            }

    client = SearchClient("secret", tmp_path / "cache.sqlite", EmptyResponse())
    result = client.discover(demo_contract())
    assert not result["candidates"]
    if status == "Success":
        assert not result["errors"]
        assert len(result["searches"]) == 3
        assert result["searches"][0]["organic_results_state"] == "Fully empty"
        assert all(r["cached"] for r in client.discover(demo_contract())["searches"])
    else:
        assert len(result["errors"]) == 3
        assert not result["searches"]


def test_missing_key_never_calls_network(tmp_path):
    fixture = SearchFixture()
    result = SearchClient("", tmp_path / "cache.sqlite", fixture).discover(demo_contract())
    assert len(result["errors"]) == 3
    assert fixture.calls == []


@pytest.mark.parametrize(
    "url",
    [
        "https://data.worldbank.org.evil.test/indicator/SP.POP.TOTL",
        "https://data.worldbank.org/indicator/NY.GDP.MKTP.CD",
        "https://user:pass@data.worldbank.org/indicator/SP.POP.TOTL",
        "http://ourworldindata.org/grapher/population-unwpp",
        "https://ourworldindata.org/grapher/population-density",
        "https://[invalid",
        "https://data.worldbank.org:bad/indicator/SP.POP.TOTL",
    ],
)
def test_source_recognition_is_strict(url):
    assert recognize(url) is None


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/data",
        "https://127.0.0.1/data",
        "file:///etc/passwd",
        "https://api.worldbank.org.evil.test/data",
        "https://user:pass@api.worldbank.org/data",
        "https://api.worldbank.org:bad/data",
        "https://[invalid",
    ],
)
def test_downloads_reject_unapproved_urls_before_network(url):
    with pytest.raises(NetworkError):
        HttpClient().get(url)


def test_interrupted_download_is_a_sanitized_network_error(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, limit):
            raise IncompleteRead(b"private partial response", 100)

    class Opener:
        def open(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr("source_rehearsal.network.build_opener", lambda *args: Opener())
    with pytest.raises(NetworkError) as error:
        HttpClient().get("https://serpapi.com/search.json?api_key=fixture-secret")
    assert "private" not in str(error.value)
    assert "fixture-secret" not in str(error.value)


@pytest.mark.parametrize("raw", [b'{"unit":NaN}', b'{"value":Infinity}', b'{"value":-Infinity}'])
def test_nonfinite_json_is_rejected_before_evidence_export(monkeypatch, raw):
    monkeypatch.setattr(HttpClient, "get", lambda self, url: raw)
    with pytest.raises(NetworkError, match="valid JSON"):
        HttpClient().json("https://api.worldbank.org/v2/data")


def test_corrupt_cache_has_an_actionable_error_and_no_network_call(tmp_path):
    cache = tmp_path / "search.sqlite"
    cache.write_bytes(b"not a SQLite database")
    fixture = SearchFixture()
    with pytest.raises(NetworkError, match="cache is unavailable or invalid"):
        SearchClient("fixture-secret", cache, fixture)
    assert not fixture.calls


@pytest.mark.parametrize("search_id", [None, "", 123])
def test_success_without_search_id_cannot_supply_candidates(tmp_path, search_id):
    class MissingId:
        def json(self, url):
            return {
                "search_metadata": {"status": "Success", "id": search_id},
                "organic_results": [{"link": "https://data.worldbank.org/indicator/SP.POP.TOTL"}],
            }

    result = SearchClient("fixture-key", tmp_path / "cache.sqlite", MissingId()).discover(
        demo_contract()
    )
    assert not result["candidates"]
    assert len(result["errors"]) == 3


def test_returned_query_mismatch_is_retained_but_cannot_supply_candidates(tmp_path):
    class Mismatched:
        def json(self, url):
            return {
                "search_metadata": {"status": "Success", "id": "mismatch"},
                "search_parameters": {"q": "unrelated secret-token", "api_key": "secret-token"},
                "organic_results": [{"link": "https://data.worldbank.org/indicator/SP.POP.TOTL"}],
            }

    result = SearchClient("secret-token", tmp_path / "search.sqlite", Mismatched()).discover(
        demo_contract()
    )
    assert not result["candidates"]
    assert all(r["query_matches_request"] is False for r in result["searches"])
    assert all("result withheld" in r["reason"] for r in result["diagnostics"])
    assert "secret-token" not in json.dumps(result)
    assert b"secret-token" not in (tmp_path / "search.sqlite").read_bytes()


def test_returned_query_is_allowlisted_and_provider_queries_avoid_baseline(tmp_path):
    class Echo:
        def json(self, url):
            query = parse_qs(urlsplit(url).query)["q"][0]
            return {
                "search_metadata": {"status": "Success", "id": "echo"},
                "search_parameters": {
                    "q": query,
                    "engine": "google",
                    "hl": "en",
                    "api_key": "private",
                },
                "organic_results": [],
            }

    result = SearchClient("private", tmp_path / "search.sqlite", Echo()).discover(
        demo_contract(), "https://ourworldindata.org/grapher/population-unwpp"
    )
    assert all(r["query_matches_request"] for r in result["searches"])
    assert all("site:ourworldindata" not in r["query"] for r in result["searches"])
    assert "private" not in json.dumps(result)

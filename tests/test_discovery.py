import json
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


def test_zero_results_never_invents_candidates(tmp_path):
    result = SearchClient("key", tmp_path / "cache.sqlite", SearchFixture(empty=True)).discover(
        demo_contract()
    )
    assert result["candidates"] == []
    assert result["errors"] == []


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
    ],
)
def test_downloads_reject_unapproved_urls_before_network(url):
    with pytest.raises(NetworkError):
        HttpClient().get(url)

import json
from urllib.parse import parse_qs, urlsplit

import pytest

from source_rehearsal.demo import demo_contract
from source_rehearsal.discovery import Candidate
from source_rehearsal.network import NetworkError
from source_rehearsal.publishers import download, our_world_in_data, world_bank


class WorldBankFixture:
    def __init__(self, missing=False):
        self.pages = []
        self.missing = missing

    def json(self, url):
        return [{"pages": 1}, [{"id": "SP.POP.TOTL", "sourceNote": "Total resident population."}]]

    def get(self, url):
        page = int(parse_qs(urlsplit(url).query)["page"][0])
        self.pages.append(page)
        rows = [
            {
                "indicator": {"id": "SP.POP.TOTL"},
                "countryiso3code": country,
                "date": str(year),
                "value": 1000 + year,
            }
            for country in ("IND", "USA", "BRA")
            for year in (2020, 2021, 2022)
        ]
        selected = rows[:5] if page == 1 else rows[5:]
        if self.missing and page == 2:
            selected = selected[:-1]
        return json.dumps([{"page": page, "pages": 2, "total": 9}, selected]).encode()


def test_worldbank_loads_every_page_and_keeps_unreviewed_metadata():
    fixture = WorldBankFixture()
    data = world_bank(demo_contract(), fixture)
    assert fixture.pages == [1, 2]
    assert len(data.frame) == 9
    assert not data.metadata.reviewed
    assert data.metadata.unit == "persons"


def test_worldbank_rejects_partial_pagination():
    with pytest.raises(NetworkError, match="incomplete"):
        world_bank(demo_contract(), WorldBankFixture(missing=True))


class OwidFixture:
    def __init__(self, unit="people"):
        self.unit = unit
        self.url = None

    def json(self, url):
        return {
            "columns": {
                "Population": {
                    "unit": self.unit,
                    "descriptionShort": "Mid-year population estimates.",
                }
            }
        }

    def get(self, url):
        self.url = url
        return b"Entity,Code,Year,Population\nIndia,IND,2020,1000\nWorld,OWID_WRL,2020,5000\n"


def test_owid_uses_actual_measure_metadata_and_explicit_column_names():
    fixture = OwidFixture()
    data = our_world_in_data(demo_contract(), fixture)
    assert data.frame.country.tolist() == ["IND"]
    assert data.metadata.unit == "persons"
    assert not data.metadata.reviewed
    assert "useColumnShortNames=false" in fixture.url


def test_owid_never_guesses_an_unknown_unit():
    data = our_world_in_data(demo_contract(), OwidFixture("thousands"))
    assert data.metadata.unit == "unknown"


def test_unsupported_candidate_cannot_download():
    candidate = Candidate("World Bank", "https://evil.test/data", "Title", "query", "id")
    with pytest.raises(NetworkError):
        download(candidate, demo_contract())


def test_discovery_provenance_is_attached():
    candidate = Candidate(
        "World Bank",
        "https://data.worldbank.org/indicator/SP.POP.TOTL",
        "Population",
        "population query",
        "fixture-id",
    )
    data = download(candidate, demo_contract(), WorldBankFixture())
    assert data.evidence["discovery"]["search_id"] == "fixture-id"

import json
from hashlib import sha256
from urllib.parse import urlencode

import pandas as pd

from .discovery import Candidate, recognize
from .ingest import csv_dataset, timestamp
from .models import MAX_BYTES, Contract, Dataset, Mapping, Metadata
from .network import HttpClient, NetworkError

WB_LICENSE = "https://datacatalog.worldbank.org/int/public-licenses#cc-by"


def world_bank(contract: Contract, http: HttpClient) -> Dataset:
    root = "https://api.worldbank.org/v2/"
    meta_payload = http.json(root + "indicator/SP.POP.TOTL?format=json")
    if (
        not isinstance(meta_payload, list)
        or len(meta_payload) != 2
        or not isinstance(meta_payload[1], list)
        or len(meta_payload[1]) != 1
        or not isinstance(meta_payload[1][0], dict)
    ):
        raise NetworkError("World Bank indicator metadata is unavailable.")
    indicator = meta_payload[1][0]
    if indicator.get("id") != "SP.POP.TOTL" or not isinstance(indicator.get("sourceNote", ""), str):
        raise NetworkError("World Bank returned an unexpected indicator.")
    raw_pages, rows, total, pages = [], [], None, None
    page = 1
    while pages is None or page <= pages:
        url = (
            root
            + f"country/{';'.join(contract.countries)}/indicator/SP.POP.TOTL?"
            + urlencode(
                {
                    "format": "json",
                    "date": f"{contract.start_year}:{contract.end_year}",
                    "per_page": 1000,
                    "page": page,
                }
            )
        )
        raw = http.get(url)
        raw_pages.append(raw)
        if sum(map(len, raw_pages)) > MAX_BYTES:
            raise NetworkError("World Bank combined responses exceed 10 MB.")
        try:
            payload = json.loads(raw)
            header, values = payload
            if not isinstance(header, dict) or not isinstance(values, list):
                raise ValueError
            if pages is None:
                pages, total = int(header["pages"]), int(header["total"])
                if not 1 <= pages <= 10 or not 1 <= total <= 100_000:
                    raise ValueError
            if int(header["pages"]) != pages or int(header["total"]) != total:
                raise ValueError
            if int(header["page"]) != page:
                raise ValueError
            for row in values:
                if (
                    not isinstance(row, dict)
                    or not isinstance(row.get("indicator"), dict)
                    or row["indicator"].get("id") != "SP.POP.TOTL"
                    or not isinstance(row.get("countryiso3code"), str)
                ):
                    raise ValueError
                rows.append(
                    {
                        "country": row["countryiso3code"],
                        "year": int(row["date"]),
                        "population": row["value"],
                    }
                )
        except (ValueError, TypeError, KeyError):
            raise NetworkError(
                "World Bank returned malformed or incomplete population data."
            ) from None
        page += 1
    if len(rows) != total:
        raise NetworkError("World Bank pagination is incomplete; no partial result was accepted.")
    meta = Metadata(
        publisher="World Bank",
        source_url="https://data.worldbank.org/indicator/SP.POP.TOTL",
        indicator="population_total",
        unit="persons",
        kind="estimate",
        license=WB_LICENSE,
        definition=indicator.get("sourceNote", ""),
        upstream=("UN World Population Prospects",),
    )
    frame = pd.DataFrame(rows)
    frame["population"] = pd.to_numeric(frame.population, errors="coerce")
    return Dataset(
        frame,
        meta,
        sha256(b"\n".join(raw_pages)).hexdigest(),
        timestamp(),
        ["World Bank JSON → country/year/population; persons, no scaling", "All API pages loaded"],
        {
            "indicator_metadata": indicator,
            "page_count": pages,
            "declared_rows": total,
            "hash_convention": "SHA-256 of raw JSON pages separated by LF",
        },
    )


def our_world_in_data(contract: Contract, http: HttpClient) -> Dataset:
    root = "https://ourworldindata.org/grapher/population-unwpp"
    metadata = http.json(root + ".metadata.json")
    if not isinstance(metadata, dict) or not isinstance(metadata.get("columns"), dict):
        raise NetworkError("OWID chart metadata is unavailable or has changed schema.")
    columns = metadata["columns"]
    if len(columns) != 1:
        raise NetworkError(
            "Expected a single population measure; review the changed chart manually."
        )
    value_column, measure = next(iter(columns.items()))
    if not isinstance(measure, dict):
        raise NetworkError("OWID measure metadata has changed schema.")
    data_url = root + ".csv?useColumnShortNames=false"
    raw = http.get(data_url)
    unit_raw = str(measure.get("unit", "unknown"))
    unit = "persons" if unit_raw.lower() in ("people", "persons", "person") else "unknown"
    description = measure.get("descriptionShort") or measure.get("description") or ""
    if isinstance(description, list):
        description = "\n".join(map(str, description))
    definition = str(description)
    meta = Metadata(
        publisher="Our World in Data",
        source_url=root,
        indicator="population_total",
        unit=unit,
        kind="estimate",
        license="https://ourworldindata.org/how-to-use-our-world-in-data",
        definition=definition,
        upstream=("UN World Population Prospects",),
    )
    data = csv_dataset(raw, Mapping("Code", "Year", value_column), meta)
    # Region aggregates are outside the MVP. Keep every requested year; do not sample.
    data.frame = data.frame[
        data.frame.country.isin(contract.countries)
        & data.frame.year.between(contract.start_year, contract.end_year)
    ].copy()
    data.transforms.append("Select only requested ISO3 country codes and historical years")
    data.evidence = {"chart_metadata": metadata, "original_unit": unit_raw, "data_url": data_url}
    return data


def download(candidate: Candidate, contract: Contract, http=None) -> Dataset:
    expected = recognize(candidate.source_url)
    if expected != (candidate.publisher, candidate.slug):
        raise NetworkError("Candidate does not match a supported population source.")
    client = http or HttpClient()
    if candidate.publisher == "World Bank":
        dataset = world_bank(contract, client)
    else:
        dataset = our_world_in_data(contract, client)
    dataset.evidence["discovery"] = {
        "query": candidate.query,
        "search_id": candidate.search_id,
        "result_url": candidate.source_url,
        "title": candidate.title,
        "cached": candidate.cached,
    }
    return dataset

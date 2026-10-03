from dataclasses import replace

from .ingest import csv_dataset
from .models import Contract, Mapping, Metadata

BASELINE = b"""country,year,population
IND,2020,1000
IND,2021,1010
IND,2022,1020
USA,2020,1500
USA,2021,1510
USA,2022,1520
BRA,2020,800
BRA,2021,820
BRA,2022,840
"""

SCENARIOS = (
    "Threshold flip",
    "Equivalent copy",
    "Rank shift",
    "Missing year",
    "Duplicate key",
    "Wrong units",
    "Unreviewed definition",
    "Exceeds tolerance",
)


def demo_contract() -> Contract:
    return Contract(("IND", "USA", "BRA"), 2020, 2022)


def demo_metadata(publisher="Synthetic baseline") -> Metadata:
    return Metadata(
        publisher=publisher,
        source_url="https://example.invalid/synthetic",
        indicator="population_total",
        unit="persons",
        kind="estimate",
        license="Project-authored synthetic fixture",
        definition="Artificial population counts for software demonstration only.",
        reviewed=True,
        synthetic=True,
    )


def baseline():
    return csv_dataset(BASELINE, Mapping(), demo_metadata())


def candidate(scenario: str):
    if scenario not in SCENARIOS:
        raise ValueError("Unknown synthetic scenario.")
    raw, meta = BASELINE, demo_metadata("Synthetic replacement")
    if scenario == "Threshold flip":
        raw = raw.replace(b"IND,2022,1020", b"IND,2022,1020.2")
    elif scenario == "Rank shift":
        raw = raw.replace(b"USA,2022,1520", b"USA,2022,1000")
    elif scenario == "Missing year":
        raw = raw.replace(b"IND,2021,1010\n", b"")
    elif scenario == "Duplicate key":
        raw += b"IND,2022,1020\n"
    elif scenario == "Wrong units":
        meta = replace(meta, unit="thousands of persons")
    elif scenario == "Unreviewed definition":
        meta = replace(meta, reviewed=False)
    elif scenario == "Exceeds tolerance":
        # Uniform scaling preserves growth and rank but violates the value tolerance.
        dataset = csv_dataset(raw, Mapping(), meta)
        dataset.frame.population *= 1.01
        dataset.transforms.append("Synthetic control: multiply all populations by 1.01")
        return dataset
    return csv_dataset(raw, Mapping(), meta)

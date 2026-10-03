import math
import re
from dataclasses import dataclass, field

import pandas as pd

MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 100_000


@dataclass(frozen=True)
class Contract:
    countries: tuple[str, ...]
    start_year: int
    end_year: int
    threshold_pct: float = 1.0
    value_tolerance_pct: float = 0.5
    indicator: str = "population_total"
    unit: str = "persons"
    kind: str = "estimate"

    def __post_init__(self):
        if not 1 <= len(self.countries) <= 20:
            raise ValueError("Select 1–20 ISO3 country codes.")
        if len(set(self.countries)) != len(self.countries):
            raise ValueError("Country codes must be unique.")
        if any(not re.fullmatch(r"[A-Z]{3}", code) for code in self.countries):
            raise ValueError("Country codes must be three uppercase letters.")
        if not 1960 <= self.start_year < self.end_year <= 2025:
            raise ValueError("Select at least two historical years between 1960 and 2025.")
        if self.end_year - self.start_year > 29:
            raise ValueError("Select at most 30 years.")
        if not all(math.isfinite(v) for v in [self.threshold_pct, self.value_tolerance_pct]):
            raise ValueError("Threshold and tolerance must be finite.")
        if self.value_tolerance_pct < 0:
            raise ValueError("Tolerance cannot be negative.")
        if (self.indicator, self.unit, self.kind) != ("population_total", "persons", "estimate"):
            raise ValueError("The MVP supports historical total population estimates in persons.")


@dataclass(frozen=True)
class Mapping:
    country: str = "country"
    year: str = "year"
    value: str = "population"
    scale: float = 1.0


@dataclass(frozen=True)
class Metadata:
    publisher: str
    source_url: str
    indicator: str = "unknown"
    unit: str = "unknown"
    kind: str = "unknown"
    license: str = "unknown"
    definition: str = ""
    reviewed: bool = False
    synthetic: bool = False
    upstream: tuple[str, ...] = ()


@dataclass
class Dataset:
    frame: pd.DataFrame
    metadata: Metadata
    sha256: str
    retrieved_at: str
    transforms: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)

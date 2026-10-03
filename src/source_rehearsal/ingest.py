import csv
import math
from datetime import datetime, timezone
from hashlib import sha256
from io import StringIO

import pandas as pd

from .models import MAX_BYTES, MAX_ROWS, Dataset, Mapping, Metadata


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_csv(raw: bytes) -> pd.DataFrame:
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("CSV must be nonempty and at most 10 MB.")
    try:
        reader = csv.reader(StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
        header = [name.strip() for name in next(reader)]
        if not header or not all(header) or len(set(header)) != len(header):
            raise ValueError("CSV column names must be nonempty and unique.")
        rows = []
        for row in reader:
            if not row:
                continue
            if len(row) != len(header):
                raise ValueError("Every CSV row must have the same number of fields as the header.")
            rows.append(row)
            if len(rows) > MAX_ROWS:
                raise ValueError("CSV must contain 1–100,000 rows.")
    except (UnicodeError, csv.Error, StopIteration) as exc:
        raise ValueError("Upload a valid UTF-8 comma-separated CSV.") from exc
    if not rows:
        raise ValueError("CSV must contain 1–100,000 rows.")
    return pd.DataFrame(rows, columns=header, dtype="string")


def normalize(frame: pd.DataFrame, mapping: Mapping) -> pd.DataFrame:
    columns = [mapping.country, mapping.year, mapping.value]
    if len(set(columns)) != 3 or not set(columns) <= set(frame.columns):
        raise ValueError("Map three different existing columns to country, year, and population.")
    if not math.isfinite(mapping.scale) or mapping.scale not in (1, 1000, 1_000_000):
        raise ValueError("Supported explicit unit multipliers are 1, 1,000, and 1,000,000.")
    out = frame[columns].copy()
    out.columns = ["country", "year", "population"]
    out["country"] = out["country"].astype("string").str.strip().str.upper()
    for column in ["year", "population"]:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    out["population"] = out["population"].astype(float) * mapping.scale
    return out


def csv_dataset(raw: bytes, mapping: Mapping, metadata: Metadata) -> Dataset:
    frame = normalize(read_csv(raw), mapping)
    return Dataset(
        frame=frame,
        metadata=metadata,
        sha256=sha256(raw).hexdigest(),
        retrieved_at=timestamp(),
        transforms=[
            f"Columns: {mapping.country}→country; {mapping.year}→year; {mapping.value}→population",
            "Country codes: trim whitespace and uppercase",
            f"Explicit population multiplier: {mapping.scale:g}",
        ],
    )

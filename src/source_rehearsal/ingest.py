import math
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO

import pandas as pd

from .models import MAX_BYTES, MAX_ROWS, Dataset, Mapping, Metadata


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_csv(raw: bytes) -> pd.DataFrame:
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("CSV must be nonempty and at most 10 MB.")
    try:
        frame = pd.read_csv(BytesIO(raw), encoding="utf-8-sig", dtype=str)
    except (UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise ValueError("Upload a valid UTF-8 comma-separated CSV.") from exc
    if frame.empty or len(frame) > MAX_ROWS:
        raise ValueError("CSV must contain 1–100,000 rows.")
    return frame


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
    out["population"] *= mapping.scale
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

"""Resolve source CSV paths for local data/ and UC Volume landing."""

from __future__ import annotations

from datetime import date
from pathlib import Path


SOURCE_FILES = ("installs", "events", "offers", "user_profile")

# Unity Catalog Volume used in this workspace (rewards schema).
DEFAULT_LANDING_ROOT = "/Volumes/workspace/rewards/landing"


def resolve_source_csv(
    data_dir: str | Path,
    source_name: str,
    *,
    load_date: date | str | None = None,
) -> str:
    """Return the CSV path for a source.

    Supports two layouts:

    1. Local / flat (tests)::

           data/installs.csv

    2. Databricks Volume under ``workspace.rewards.landing``::

           /Volumes/workspace/rewards/landing/installs/load_date=YYYY-MM-DD/installs.csv

    If ``data_dir`` points at the landing root (or contains a source subfolder),
    the hive-style ``load_date=`` path is preferred when ``load_date`` is set.
    """
    if source_name not in SOURCE_FILES:
        raise ValueError(f"unknown source_name={source_name!r}")

    root = Path(str(data_dir))
    flat = root / f"{source_name}.csv"
    source_dir = root / source_name

    # Volume / hive layout: .../landing/<source>/load_date=.../<source>.csv
    if load_date is not None:
        load_date_str = (
            load_date.isoformat() if isinstance(load_date, date) else str(load_date)
        )
        hive = source_dir / f"load_date={load_date_str}" / f"{source_name}.csv"
        return str(hive)

    # If source subdirectories exist without an explicit load_date, read the folder
    # (Spark will pick up nested CSVs / partitions).
    if source_dir.exists() and source_dir.is_dir():
        return str(source_dir)

    # Flat local file for unit tests / offline runs.
    return str(flat)

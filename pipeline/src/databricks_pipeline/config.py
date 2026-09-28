"""Central configuration for the rewards medallion pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from databricks_pipeline.utils.paths import DEFAULT_LANDING_ROOT

# Ideal target (when custom catalogs are allowed): rewards_pipeline.{bronze,silver,gold}
# Free Edition limitation: only the managed `workspace` catalog is available, so we use
# rewards-prefixed schemas that already exist in this workspace.
DEFAULT_CATALOG = "workspace"
DEFAULT_BRONZE_SCHEMA = "rewards_bronze"
DEFAULT_SILVER_SCHEMA = "rewards_silver"
DEFAULT_GOLD_SCHEMA = "rewards_gold"
DEFAULT_CORRECTION_WINDOW_DAYS = 7


@dataclass(frozen=True)
class PipelineConfig:
    """Unity Catalog names and processing window parameters.

    Defaults target Databricks Free Edition::

        catalog  = workspace
        schemas  = rewards_bronze / rewards_silver / rewards_gold
        CSVs     = /Volumes/workspace/rewards/landing/<source>/load_date=...

    Override ``data_dir`` / ``load_date`` for local tests (flat ``data/*.csv``).
    """

    catalog: str = DEFAULT_CATALOG
    bronze_schema: str = DEFAULT_BRONZE_SCHEMA
    silver_schema: str = DEFAULT_SILVER_SCHEMA
    gold_schema: str = DEFAULT_GOLD_SCHEMA
    data_dir: Path = field(default_factory=lambda: Path(DEFAULT_LANDING_ROOT))
    load_date: date | None = None
    correction_window_days: int = DEFAULT_CORRECTION_WINDOW_DAYS

    def table(self, layer: str, name: str) -> str:
        """Return fully-qualified Unity Catalog table name."""
        schema = {
            "bronze": self.bronze_schema,
            "silver": self.silver_schema,
            "gold": self.gold_schema,
        }[layer]
        return f"{self.catalog}.{schema}.{name}"

    @property
    def bronze_installs(self) -> str:
        return self.table("bronze", "installs")

    @property
    def bronze_events(self) -> str:
        return self.table("bronze", "events")

    @property
    def bronze_offers(self) -> str:
        return self.table("bronze", "offers")

    @property
    def bronze_user_profile(self) -> str:
        return self.table("bronze", "user_profile")

    @property
    def silver_installs(self) -> str:
        return self.table("silver", "installs")

    @property
    def silver_events(self) -> str:
        return self.table("silver", "events")

    @property
    def silver_offers(self) -> str:
        return self.table("silver", "offers")

    @property
    def silver_user_profile(self) -> str:
        return self.table("silver", "user_profile")

    @property
    def gold_daily_metrics(self) -> str:
        return self.table("gold", "daily_metrics")

    def correction_window(self, process_date: date) -> tuple[date, date]:
        """Return inclusive [start_date, end_date] for late-arrival correction."""
        start = process_date - timedelta(days=self.correction_window_days - 1)
        return start, process_date

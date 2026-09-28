"""Gold SQL loading helpers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from databricks_pipeline.config import PipelineConfig
from databricks_pipeline.utils.sql_templates import load_and_render_sql

_DEFAULT_SQL = (
    Path(__file__).resolve().parents[3] / "gold" / "sql" / "daily_metrics.sql"
)


def gold_sql_path() -> Path:
    """Return the canonical Gold daily-metrics SQL path."""
    return _DEFAULT_SQL


def load_gold_sql(
    config: PipelineConfig,
    start_date: date,
    end_date: date,
    sql_path: Path | None = None,
) -> str:
    """Render Gold SQL with table names and an inclusive date window."""
    return load_and_render_sql(
        sql_path or gold_sql_path(),
        {
            "silver_installs": config.silver_installs,
            "silver_events": config.silver_events,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
    )

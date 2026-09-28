"""Gold layer helpers — load SQL from ``pipeline/gold/sql/`` via utils."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from databricks_pipeline.config import PipelineConfig
from databricks_pipeline.utils.sql_templates import load_and_render_sql

_DEFAULT_SQL = (
    Path(__file__).resolve().parents[3] / "gold" / "sql" / "daily_metrics.sql"
)


def gold_sql_path() -> Path:
    """Return path to the Gold daily metrics SQL file."""
    return _DEFAULT_SQL


def load_gold_sql(
    config: PipelineConfig,
    start_date: date,
    end_date: date,
    sql_path: Path | None = None,
) -> str:
    """Load Gold SQL and substitute table names / date window placeholders."""
    return load_and_render_sql(
        sql_path or gold_sql_path(),
        {
            "silver_installs": config.silver_installs,
            "silver_events": config.silver_events,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
    )


def merge_gold_sql(config: PipelineConfig) -> str:
    """Return MERGE statement that upserts the temp updates view into Gold."""
    target = config.gold_daily_metrics
    return f"""
MERGE INTO {target} AS target
USING gold_daily_metrics_updates AS source
ON  target.metric_date = source.metric_date
AND target.country = source.country
AND target.platform = source.platform
WHEN MATCHED THEN UPDATE SET
    installs = source.installs,
    unique_app_open_users = source.unique_app_open_users,
    unique_offer_view_users = source.unique_offer_view_users,
    unique_offer_start_users = source.unique_offer_start_users,
    unique_goal_reached_users = source.unique_goal_reached_users,
    unique_reward_paid_users = source.unique_reward_paid_users,
    reward_payouts = source.reward_payouts,
    reward_cost_eur = source.reward_cost_eur,
    _updated_at = source._updated_at
WHEN NOT MATCHED THEN INSERT (
    metric_date, country, platform,
    installs,
    unique_app_open_users, unique_offer_view_users,
    unique_offer_start_users, unique_goal_reached_users,
    unique_reward_paid_users,
    reward_payouts, reward_cost_eur, _updated_at
) VALUES (
    source.metric_date, source.country, source.platform,
    source.installs,
    source.unique_app_open_users, source.unique_offer_view_users,
    source.unique_offer_start_users, source.unique_goal_reached_users,
    source.unique_reward_paid_users,
    source.reward_payouts, source.reward_cost_eur, source._updated_at
)
"""


def delete_scope_sql(config: PipelineConfig, start_date: date, end_date: date) -> str:
    """Delete Gold rows in the correction window before insert."""
    target = config.gold_daily_metrics
    return (
        f"DELETE FROM {target} "
        f"WHERE metric_date BETWEEN DATE '{start_date.isoformat()}' "
        f"AND DATE '{end_date.isoformat()}'"
    )

"""Orchestrate Bronze → Silver → Gold for a process_date window."""

from __future__ import annotations

from datetime import date

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from databricks_pipeline.bronze import run_bronze
from databricks_pipeline.config import PipelineConfig
from databricks_pipeline.gold import delete_scope_sql, load_gold_sql
from databricks_pipeline.silver import (
    transform_events,
    transform_installs,
    transform_offers,
    transform_user_profile,
)
from databricks_pipeline.utils import (
    correction_window,
    ensure_schemas,
    write_delta_overwrite,
)


def run_silver(spark: SparkSession, config: PipelineConfig) -> dict[str, int]:
    """Transform Bronze → Silver and overwrite Silver Delta tables."""
    bronze_installs = spark.table(config.bronze_installs)
    bronze_events = spark.table(config.bronze_events)
    bronze_offers = spark.table(config.bronze_offers)
    bronze_profile = spark.table(config.bronze_user_profile)

    silver_offers = transform_offers(bronze_offers)
    silver_installs = transform_installs(bronze_installs)
    silver_events = transform_events(bronze_events, silver_installs, silver_offers)
    silver_profile = transform_user_profile(bronze_profile)

    frames = {
        config.silver_offers: silver_offers,
        config.silver_installs: silver_installs,
        config.silver_events: silver_events,
        config.silver_user_profile: silver_profile,
    }
    counts: dict[str, int] = {}
    for table_name, df in frames.items():
        write_delta_overwrite(df, table_name)
        counts[table_name] = df.count()
    return counts


def ensure_gold_table(spark: SparkSession, config: PipelineConfig) -> None:
    """Create empty Gold table if it does not exist."""
    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {config.gold_daily_metrics} (
            metric_date DATE,
            country STRING,
            platform STRING,
            installs BIGINT,
            unique_app_open_users BIGINT,
            unique_offer_view_users BIGINT,
            unique_offer_start_users BIGINT,
            unique_goal_reached_users BIGINT,
            unique_reward_paid_users BIGINT,
            reward_payouts BIGINT,
            reward_cost_eur DECIMAL(18,2),
            _updated_at TIMESTAMP
        ) USING DELTA
        """
    )


def run_gold(
    spark: SparkSession,
    config: PipelineConfig,
    process_date: date,
    *,
    full_refresh: bool = False,
) -> DataFrame:
    """Recompute Gold for the correction window (or full history) idempotently."""
    ensure_gold_table(spark, config)

    if full_refresh:
        start_date = date(1970, 1, 1)
        end_date = process_date
    else:
        start_date, end_date = correction_window(
            process_date, window_days=config.correction_window_days
        )

    spark.sql(load_gold_sql(config, start_date, end_date))
    spark.sql(delete_scope_sql(config, start_date, end_date))
    spark.sql(
        f"""
        INSERT INTO {config.gold_daily_metrics}
        SELECT * FROM gold_daily_metrics_updates
        """
    )
    return spark.table(config.gold_daily_metrics).filter(
        (F.col("metric_date") >= F.lit(start_date))
        & (F.col("metric_date") <= F.lit(end_date))
    )


def run_pipeline(
    spark: SparkSession,
    config: PipelineConfig,
    process_date: date,
    *,
    full_refresh: bool = False,
) -> dict[str, object]:
    """Run Bronze → Silver → Gold end-to-end."""
    ensure_schemas(spark, config)
    bronze_counts = run_bronze(spark, config)
    silver_counts = run_silver(spark, config)
    gold_df = run_gold(spark, config, process_date, full_refresh=full_refresh)
    return {
        "bronze_counts": bronze_counts,
        "silver_counts": silver_counts,
        "gold_rows": gold_df.count(),
        "process_date": process_date.isoformat(),
        "full_refresh": full_refresh,
    }

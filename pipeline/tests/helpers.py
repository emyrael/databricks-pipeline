"""Shared builders used by multiple test modules."""

from __future__ import annotations

from datetime import date

from pyspark.sql import DataFrame, SparkSession

from databricks_pipeline.config import PipelineConfig
from databricks_pipeline.gold import load_gold_sql
from databricks_pipeline.silver import (
    transform_events,
    transform_installs,
    transform_offers,
)


def build_silver_events(
    spark: SparkSession,
    installs_rows: list[dict],
    events_rows: list[dict],
    offers_rows: list[dict],
) -> tuple[DataFrame, DataFrame, DataFrame]:
    """Bronze-like rows → silver installs/events/offers DataFrames."""
    installs_bronze = spark.createDataFrame(installs_rows)
    events_bronze = spark.createDataFrame(events_rows)
    offers_bronze = spark.createDataFrame(offers_rows)

    silver_offers = transform_offers(offers_bronze)
    silver_installs = transform_installs(installs_bronze)
    silver_events = transform_events(events_bronze, silver_installs, silver_offers)
    return silver_installs, silver_events, silver_offers


def compute_gold_via_sql(
    spark: SparkSession,
    silver_installs: DataFrame,
    silver_events: DataFrame,
    *,
    start_date: date,
    end_date: date,
) -> DataFrame:
    """Run the real Gold SQL against temp views (no Python metric duplicate)."""
    silver_installs.createOrReplaceTempView("test_silver_installs")
    silver_events.createOrReplaceTempView("test_silver_events")

    config = PipelineConfig(
        catalog="ignored",
        bronze_schema="b",
        silver_schema="s",
        gold_schema="g",
    )
    sql = load_gold_sql(config, start_date, end_date)
    sql = sql.replace(config.silver_installs, "test_silver_installs").replace(
        config.silver_events, "test_silver_events"
    )
    spark.sql(sql)
    return spark.table("gold_daily_metrics_updates")

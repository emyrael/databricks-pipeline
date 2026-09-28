"""Orchestrate Bronze → Silver → Gold for a process-date window."""

from __future__ import annotations

from datetime import date

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from databricks_pipeline.bronze import run_bronze
from databricks_pipeline.config import PipelineConfig
from databricks_pipeline.gold import load_gold_sql
from databricks_pipeline.quality.checks import (
    assert_event_replay_shape,
    assert_no_key_conflicts,
    assert_no_unresolved_rewards,
    assert_required_non_null,
    assert_unique_key,
)
from databricks_pipeline.silver import (
    transform_events,
    transform_installs,
    transform_offers,
    transform_user_profile,
)
from databricks_pipeline.utils import (
    ensure_schemas,
    merge_delta,
    table_exists,
    write_delta_overwrite,
)


def _write_reference_table(
    spark: SparkSession,
    incoming: DataFrame,
    target_table: str,
    *,
    key: str,
    immutable_columns: list[str],
    label: str,
    full_refresh: bool,
) -> None:
    """Write an immutable reference micro-batch without silently changing history."""
    assert_unique_key(incoming, key, label)

    if full_refresh or not table_exists(spark, target_table):
        write_delta_overwrite(incoming, target_table)
        return

    existing = spark.table(target_table)
    assert_unique_key(existing, key, f"existing {label}")
    assert_no_key_conflicts(
        incoming,
        existing,
        key=key,
        compare_columns=immutable_columns,
        label=label,
    )
    merge_delta(
        spark,
        incoming,
        target_table,
        key_columns=[key],
        update_matched=False,
    )


def run_silver(
    spark: SparkSession,
    config: PipelineConfig,
    *,
    full_refresh: bool = False,
) -> dict[str, int]:
    """Transform the current Bronze batch and merge it into Silver.

    Initial loads can use full_refresh=True. Normal runs only process the rows
    present in the current Bronze landing batch and merge them into existing
    Silver tables, so a single-day load does not rebuild full history.
    """
    bronze_installs = spark.table(config.bronze_installs)
    bronze_events = spark.table(config.bronze_events)
    bronze_offers = spark.table(config.bronze_offers)
    bronze_profile = spark.table(config.bronze_user_profile)

    assert_required_non_null(
        bronze_events,
        ["event_id", "user_id", "event_ts", "ingest_ts"],
        "bronze events",
    )
    assert_event_replay_shape(bronze_events)

    incoming_offers = transform_offers(bronze_offers)
    incoming_installs = transform_installs(bronze_installs)
    incoming_profile = transform_user_profile(bronze_profile)

    assert_required_non_null(
        incoming_installs,
        ["user_id", "install_ts", "install_date", "country", "platform"],
        "silver installs batch",
    )

    # Installs and offers are treated as immutable reference data for this exercise.
    # Conflicting repeats fail instead of silently rewriting historical meaning.
    _write_reference_table(
        spark,
        incoming_offers,
        config.silver_offers,
        key="offer_id",
        immutable_columns=["offer_category", "payout_type", "payout_eur"],
        label="silver offers",
        full_refresh=full_refresh,
    )
    _write_reference_table(
        spark,
        incoming_installs,
        config.silver_installs,
        key="user_id",
        immutable_columns=[
            "install_ts",
            "country",
            "platform",
            "media_source",
            "device_model",
            "campaign_id",
        ],
        label="silver installs",
        full_refresh=full_refresh,
    )

    # Enrich the event micro-batch against the complete current dimensions so an
    # event arriving today can belong to a user or offer first seen earlier.
    silver_installs_all = spark.table(config.silver_installs)
    silver_offers_all = spark.table(config.silver_offers)
    incoming_events = transform_events(
        bronze_events,
        silver_installs_all,
        silver_offers_all,
    )

    assert_unique_key(incoming_events, "event_id", "silver events batch")
    assert_required_non_null(
        incoming_events,
        ["event_id", "user_id", "event_ts", "ingest_ts", "event_date", "ingest_date"],
        "silver events batch",
    )
    assert_no_unresolved_rewards(incoming_events)

    if full_refresh or not table_exists(spark, config.silver_events):
        write_delta_overwrite(incoming_events, config.silver_events)
    else:
        existing_events = spark.table(config.silver_events)
        assert_unique_key(existing_events, "event_id", "existing silver events")
        assert_no_key_conflicts(
            incoming_events,
            existing_events,
            key="event_id",
            compare_columns=["user_id", "event_ts", "event_name", "offer_id"],
            label="silver events",
        )
        merge_delta(
            spark,
            incoming_events,
            config.silver_events,
            key_columns=["event_id"],
            update_matched=True,
            matched_condition="s.ingest_ts < t.ingest_ts",
        )

    # user_profile is a mutable backend snapshot and is not used to derive Gold.
    assert_unique_key(incoming_profile, "user_id", "silver user_profile batch")
    if full_refresh or not table_exists(spark, config.silver_user_profile):
        write_delta_overwrite(incoming_profile, config.silver_user_profile)
    else:
        merge_delta(
            spark,
            incoming_profile,
            config.silver_user_profile,
            key_columns=["user_id"],
            update_matched=True,
            matched_condition=(
                "NOT (s.events_lifetime <=> t.events_lifetime "
                "AND s.last_seen_ts <=> t.last_seen_ts "
                "AND s.revenue_30d_eur <=> t.revenue_30d_eur "
                "AND s.is_payer <=> t.is_payer)"
            ),
        )

    return {
        config.silver_offers: incoming_offers.count(),
        config.silver_installs: incoming_installs.count(),
        config.silver_events: incoming_events.count(),
        config.silver_user_profile: incoming_profile.count(),
    }


def ensure_gold_table(spark: SparkSession, config: PipelineConfig) -> None:
    """Create the Gold Delta table if it does not already exist."""
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
    """Build Gold in SQL and write it idempotently with Delta replaceWhere."""
    ensure_gold_table(spark, config)

    if full_refresh:
        start_date = date(1970, 1, 1)
        end_date = process_date
    else:
        start_date, end_date = config.correction_window(process_date)

    spark.sql(load_gold_sql(config, start_date, end_date))
    updates = spark.table("gold_daily_metrics_updates")

    writer = updates.write.format("delta").mode("overwrite")
    if full_refresh:
        writer.option("overwriteSchema", "true").saveAsTable(config.gold_daily_metrics)
    else:
        predicate = (
            f"metric_date >= DATE '{start_date.isoformat()}' "
            f"AND metric_date <= DATE '{end_date.isoformat()}'"
        )
        writer.option("replaceWhere", predicate).saveAsTable(config.gold_daily_metrics)

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
    """Run Bronze → Silver → Gold end to end."""
    ensure_schemas(spark, config)
    bronze_counts = run_bronze(spark, config)
    silver_counts = run_silver(spark, config, full_refresh=full_refresh)
    gold_df = run_gold(spark, config, process_date, full_refresh=full_refresh)
    return {
        "bronze_counts": bronze_counts,
        "silver_counts": silver_counts,
        "gold_rows": gold_df.count(),
        "process_date": process_date.isoformat(),
        "full_refresh": full_refresh,
    }

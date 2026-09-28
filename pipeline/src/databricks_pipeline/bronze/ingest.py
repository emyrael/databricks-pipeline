"""Bronze ingestion: raw CSV → DataFrames (no normalize / filter / dedupe)."""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import StructType

from databricks_pipeline.bronze.schemas import (
    EVENTS_SCHEMA,
    INSTALLS_SCHEMA,
    OFFERS_SCHEMA,
    USER_PROFILE_SCHEMA,
)
from databricks_pipeline.config import PipelineConfig
from databricks_pipeline.utils.io import read_csv_with_schema, write_delta_overwrite
from databricks_pipeline.utils.paths import resolve_source_csv


def _ingest_source(
    spark: SparkSession,
    config: PipelineConfig,
    source_name: str,
    schema: StructType,
) -> DataFrame:
    """Read one source CSV from the configured landing location."""
    path = resolve_source_csv(
        config.data_dir,
        source_name,
        load_date=config.load_date,
    )
    return read_csv_with_schema(spark, path, schema)


def ingest_installs(spark: SparkSession, config: PipelineConfig) -> DataFrame:
    """Ingest raw installs into a Bronze DataFrame."""
    return _ingest_source(spark, config, "installs", INSTALLS_SCHEMA)


def ingest_events(spark: SparkSession, config: PipelineConfig) -> DataFrame:
    """Ingest raw events; preserves repeated event_ids."""
    return _ingest_source(spark, config, "events", EVENTS_SCHEMA)


def ingest_offers(spark: SparkSession, config: PipelineConfig) -> DataFrame:
    """Ingest raw offers into a Bronze DataFrame."""
    return _ingest_source(spark, config, "offers", OFFERS_SCHEMA)


def ingest_user_profile(spark: SparkSession, config: PipelineConfig) -> DataFrame:
    """Ingest raw user_profile into a Bronze DataFrame."""
    return _ingest_source(spark, config, "user_profile", USER_PROFILE_SCHEMA)


def run_bronze(spark: SparkSession, config: PipelineConfig) -> dict[str, int]:
    """Land all four CSVs into Bronze Delta tables; return row counts."""
    frames = {
        config.bronze_installs: ingest_installs(spark, config),
        config.bronze_events: ingest_events(spark, config),
        config.bronze_offers: ingest_offers(spark, config),
        config.bronze_user_profile: ingest_user_profile(spark, config),
    }
    counts: dict[str, int] = {}
    for table_name, df in frames.items():
        write_delta_overwrite(df, table_name)
        counts[table_name] = df.count()
    return counts

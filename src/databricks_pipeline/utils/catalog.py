"""Catalog / schema helpers."""

from __future__ import annotations

from pyspark.sql import SparkSession

from databricks_pipeline.config import PipelineConfig


def ensure_schemas(spark: SparkSession, config: PipelineConfig) -> None:
    """Create Unity Catalog schemas if they do not already exist."""
    for schema in (config.bronze_schema, config.silver_schema, config.gold_schema):
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {config.catalog}.{schema}")

"""Reusable Spark I/O helpers."""

from __future__ import annotations

from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType


def read_csv_with_schema(
    spark: SparkSession,
    path: str | Path,
    schema: StructType,
    *,
    add_ingestion_metadata: bool = True,
) -> DataFrame:
    """Batch-read a CSV with an explicit schema (no Auto Loader)."""
    path_str = str(path)
    df = (
        spark.read.format("csv")
        .option("header", "true")
        .option("mode", "PERMISSIVE")
        .schema(schema)
        .load(path_str)
    )
    if add_ingestion_metadata:
        df = df.withColumn("_ingested_at", F.current_timestamp()).withColumn(
            "_source_file", F.lit(Path(path_str).name)
        )
    return df


def write_delta_overwrite(df: DataFrame, table_name: str) -> None:
    """Overwrite a Delta table idempotently (schema overwrite allowed)."""
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(table_name)
    )

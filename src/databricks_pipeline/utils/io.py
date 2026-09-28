"""Reusable Spark I/O helpers."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

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
        df = (
            df.withColumn("_ingested_at", F.current_timestamp())
            .withColumn("_source_file", F.col("_metadata.file_path"))
        )
    return df


def write_delta_overwrite(df: DataFrame, table_name: str) -> None:
    """Overwrite a bounded exercise table idempotently."""
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(table_name)
    )


def table_exists(spark: SparkSession, table_name: str) -> bool:
    """Return whether a catalog table already exists."""
    return spark.catalog.tableExists(table_name)


def merge_delta(
    spark: SparkSession,
    source_df: DataFrame,
    target_table: str,
    *,
    key_columns: list[str],
    update_matched: bool = False,
    matched_condition: str | None = None,
) -> None:
    """Merge a micro-batch DataFrame into a Delta table.

    key_columns define logical identity. By default matched rows are kept and
    only new keys are inserted. Set update_matched=True for mutable snapshots
    or when a deterministic condition should replace the existing row.

    matched_condition is SQL using aliases s (source) and t (target).
    Example: s.ingest_ts < t.ingest_ts keeps the earliest observed replay.
    """
    if not key_columns:
        raise ValueError("key_columns must not be empty")

    view_name = f"_merge_source_{uuid4().hex}"
    source_df.createOrReplaceTempView(view_name)

    on_clause = " AND ".join(f"t.{key} <=> s.{key}" for key in key_columns)

    matched_sql = ""
    if update_matched:
        condition = f" AND {matched_condition}" if matched_condition else ""
        matched_sql = f"WHEN MATCHED{condition} THEN UPDATE SET *"

    spark.sql(
        f"""
        MERGE INTO {target_table} AS t
        USING {view_name} AS s
        ON {on_clause}
        {matched_sql}
        WHEN NOT MATCHED THEN INSERT *
        """
    )
    spark.catalog.dropTempView(view_name)

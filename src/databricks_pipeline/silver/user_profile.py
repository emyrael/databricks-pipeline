"""Silver user_profile transforms (typing only; not used for Gold)."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def transform_user_profile(df: DataFrame) -> DataFrame:
    """Cast user_profile types for reconciliation only.

    Do not use this table to calculate Gold metrics — wrong grain and
    profiling shows lifetime fields are not a trustworthy projection of
    the event log.
    """
    return (
        df.withColumn("user_id", F.col("user_id").cast("string"))
        .withColumn("events_lifetime", F.col("events_lifetime").cast("bigint"))
        .withColumn("last_seen_ts", F.to_timestamp("last_seen_ts"))
        .withColumn("revenue_30d_eur", F.col("revenue_30d_eur").cast("decimal(10,2)"))
        .withColumn(
            "is_payer",
            F.when(F.lower(F.trim(F.col("is_payer"))) == "true", F.lit(True))
            .when(F.lower(F.trim(F.col("is_payer"))) == "false", F.lit(False))
            .otherwise(F.col("is_payer").cast("boolean")),
        )
    )

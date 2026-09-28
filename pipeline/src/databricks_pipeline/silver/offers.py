"""Silver offers transforms."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def transform_offers(df: DataFrame) -> DataFrame:
    """Type offers; payout_eur as DECIMAL(10,2) — never floating point."""
    return df.withColumn("payout_eur", F.col("payout_eur").cast("decimal(10,2)"))

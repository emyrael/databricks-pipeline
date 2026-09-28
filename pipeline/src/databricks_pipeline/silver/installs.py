"""Silver installs transforms."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def transform_installs(df: DataFrame) -> DataFrame:
    """Normalize installs while preserving one-row-per-user grain.

    - Cast install_ts and derive install_date
    - country = UPPER(TRIM(country))
    - platform / media_source lower+trim
    - blank campaign_id → null (organic rows retained)
    """
    return (
        df.withColumn("install_ts", F.to_timestamp("install_ts"))
        .withColumn("install_date", F.to_date("install_ts"))
        .withColumn("country", F.upper(F.trim(F.col("country"))))
        .withColumn("platform", F.lower(F.trim(F.col("platform"))))
        .withColumn("media_source", F.lower(F.trim(F.col("media_source"))))
        .withColumn(
            "campaign_id",
            F.when(F.trim(F.col("campaign_id")) == "", F.lit(None).cast("string")).otherwise(
                F.trim(F.col("campaign_id"))
            ),
        )
    )

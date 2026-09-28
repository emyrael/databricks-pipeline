"""Silver events transforms."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def transform_events(
    events_df: DataFrame,
    installs_df: DataFrame,
    offers_df: DataFrame,
) -> DataFrame:
    """Build trustworthy Silver events from Bronze.

    Exercise assumption: ``event_id`` is the logical event identity.
    Profiling shows 12,721 repeated rows where only ``ingest_ts`` differs.
    Within each event_id group we keep the earliest ingest_ts.

    Does NOT enforce the offer funnel. Unknown offers and pre-install
    events are retained and flagged, not dropped.
    """
    typed = (
        events_df.withColumn("event_ts", F.to_timestamp("event_ts"))
        .withColumn("ingest_ts", F.to_timestamp("ingest_ts"))
        .withColumn("event_date", F.to_date("event_ts"))
        .withColumn("ingest_date", F.to_date("ingest_ts"))
        .withColumn(
            "ingest_delay_seconds",
            F.unix_timestamp("ingest_ts") - F.unix_timestamp("event_ts"),
        )
        .withColumn(
            "ingest_delay_days",
            F.col("ingest_delay_seconds") / F.lit(86400.0),
        )
        .withColumn(
            "cross_day_arrival",
            F.col("event_date") != F.col("ingest_date"),
        )
    )

    dedupe_window = Window.partitionBy("event_id").orderBy(F.col("ingest_ts").asc())
    deduped = (
        typed.withColumn("_rn", F.row_number().over(dedupe_window))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )

    install_dims = installs_df.select(
        "user_id",
        F.col("install_ts").alias("install_ts"),
        "country",
        "platform",
    )

    enriched = (
        deduped.alias("e")
        .join(install_dims.alias("i"), on="user_id", how="left")
        .withColumn(
            "event_before_install",
            F.col("event_ts") < F.col("install_ts"),
        )
    )

    offer_dims = offers_df.select(
        "offer_id",
        F.col("payout_eur").alias("offer_payout_eur"),
    )

    with_offers = (
        enriched.join(offer_dims, on="offer_id", how="left")
        .withColumn("offer_resolved", F.col("offer_payout_eur").isNotNull())
        .withColumn(
            "payout_eur",
            F.when(
                F.col("event_name") == "reward_paid",
                F.col("offer_payout_eur"),
            ).otherwise(F.lit(None).cast("decimal(10,2)")),
        )
        .drop("offer_payout_eur")
    )

    return with_offers

"""Explicit Bronze schemas — all STRING to preserve raw source values."""

from __future__ import annotations

from pyspark.sql.types import StringType, StructField, StructType

INSTALLS_SCHEMA = StructType(
    [
        StructField("user_id", StringType(), True),
        StructField("install_ts", StringType(), True),
        StructField("country", StringType(), True),
        StructField("platform", StringType(), True),
        StructField("media_source", StringType(), True),
        StructField("device_model", StringType(), True),
        StructField("campaign_id", StringType(), True),
    ]
)

EVENTS_SCHEMA = StructType(
    [
        StructField("user_id", StringType(), True),
        StructField("event_ts", StringType(), True),
        StructField("event_name", StringType(), True),
        StructField("offer_id", StringType(), True),
        StructField("event_id", StringType(), True),
        StructField("ingest_ts", StringType(), True),
    ]
)

OFFERS_SCHEMA = StructType(
    [
        StructField("offer_id", StringType(), True),
        StructField("offer_category", StringType(), True),
        StructField("payout_type", StringType(), True),
        StructField("payout_eur", StringType(), True),
    ]
)

USER_PROFILE_SCHEMA = StructType(
    [
        StructField("user_id", StringType(), True),
        StructField("events_lifetime", StringType(), True),
        StructField("last_seen_ts", StringType(), True),
        StructField("revenue_30d_eur", StringType(), True),
        StructField("is_payer", StringType(), True),
    ]
)

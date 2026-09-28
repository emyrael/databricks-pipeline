"""Tests for Silver installs transforms (spec Test 3)."""

from __future__ import annotations

from databricks_pipeline.silver import transform_installs


def test_country_canonicalization(spark):
    """Test 3: 'DE' and 'de ' both become 'DE'."""
    bronze = spark.createDataFrame(
        [
            {
                "user_id": "u1",
                "install_ts": "2026-05-01 10:00:00",
                "country": "DE",
                "platform": "ios",
                "media_source": "meta",
                "device_model": "iphone15",
                "campaign_id": "cmp_1",
            },
            {
                "user_id": "u2",
                "install_ts": "2026-05-01 11:00:00",
                "country": "de ",
                "platform": "android",
                "media_source": "organic",
                "device_model": "pixel7",
                "campaign_id": "",
            },
        ]
    )
    silver = transform_installs(bronze)
    countries = {r["country"] for r in silver.collect()}
    assert countries == {"DE"}

    organic = silver.filter("user_id = 'u2'").collect()[0]
    assert organic["campaign_id"] is None
    assert organic["media_source"] == "organic"

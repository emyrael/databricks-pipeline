"""Runtime quality-check tests."""

from __future__ import annotations

from databricks_pipeline.quality import run_all_checks
from helpers import build_silver_events


def test_quality_checks_pass_on_clean_silver(spark):
    """Uniqueness and non-negative checks pass for well-formed Silver/Gold stubs."""
    installs = [
        {
            "user_id": "u1",
            "install_ts": "2026-05-01 09:00:00",
            "country": "DE",
            "platform": "ios",
            "media_source": "meta",
            "device_model": "iphone15",
            "campaign_id": "cmp_1",
        }
    ]
    offers = [
        {
            "offer_id": "of_1",
            "offer_category": "rpg",
            "payout_type": "cpe",
            "payout_eur": "2.00",
        }
    ]
    events = [
        {
            "user_id": "u1",
            "event_ts": "2026-05-01 10:00:00",
            "event_name": "app_open",
            "offer_id": "of_1",
            "event_id": "ev_1",
            "ingest_ts": "2026-05-01 11:00:00",
        },
        {
            "user_id": "u1",
            "event_ts": "2026-05-01 10:00:00",
            "event_name": "app_open",
            "offer_id": "of_1",
            "event_id": "ev_1",
            "ingest_ts": "2026-05-01 11:05:00",
        },
    ]
    bronze_events = spark.createDataFrame(events)
    silver_installs, silver_events, _ = build_silver_events(spark, installs, events, offers)

    gold = spark.createDataFrame(
        [
            {
                "metric_date": "2026-05-01",
                "country": "DE",
                "platform": "ios",
                "installs": 1,
                "unique_app_open_users": 1,
                "unique_offer_view_users": 0,
                "unique_offer_start_users": 0,
                "unique_goal_reached_users": 0,
                "unique_reward_paid_users": 0,
                "reward_payouts": 0,
                "reward_cost_eur": 0.0,
            }
        ]
    )

    results = {
        r.name: r
        for r in run_all_checks(
            bronze_events=bronze_events,
            silver_installs=silver_installs,
            silver_events=silver_events,
            gold=gold,
        )
    }
    assert results["silver_event_id_unique"].passed
    assert results["silver_install_user_id_unique"].passed
    assert results["gold_logical_key_unique"].passed
    assert results["reward_cost_eur_non_negative"].passed
    assert results["replay_count"].value == 1

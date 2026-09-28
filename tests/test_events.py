"""Tests for Silver events transforms (spec Tests 1, 4, 7-reward)."""

from __future__ import annotations

from decimal import Decimal

from helpers import build_silver_events


def _base_install(user_id: str = "u1", country: str = "DE"):
    return {
        "user_id": user_id,
        "install_ts": "2026-05-01 00:00:00",
        "country": country,
        "platform": "ios",
        "media_source": "meta",
        "device_model": "iphone15",
        "campaign_id": "cmp_1",
    }


def _offer(offer_id: str = "of_1", payout: str = "2.50"):
    return {
        "offer_id": offer_id,
        "offer_category": "rpg",
        "payout_type": "cpe",
        "payout_eur": payout,
    }


def test_duplicate_event_id_keeps_earliest_ingest(spark):
    """Test 1: repeated event_id → one Silver row, earliest ingest_ts retained."""
    installs = [_base_install()]
    offers = [_offer()]
    events = [
        {
            "user_id": "u1",
            "event_ts": "2026-05-01 12:00:00",
            "event_name": "offer_view",
            "offer_id": "of_1",
            "event_id": "ev_dup",
            "ingest_ts": "2026-05-01 13:00:00",
        },
        {
            "user_id": "u1",
            "event_ts": "2026-05-01 12:00:00",
            "event_name": "offer_view",
            "offer_id": "of_1",
            "event_id": "ev_dup",
            "ingest_ts": "2026-05-01 13:01:30",
        },
    ]
    _, silver_events, _ = build_silver_events(spark, installs, events, offers)
    rows = silver_events.filter("event_id = 'ev_dup'").collect()
    assert len(rows) == 1
    # Compare via Spark date_format to avoid local-tz string rendering surprises.
    kept = (
        silver_events.filter("event_id = 'ev_dup'")
        .selectExpr("date_format(ingest_ts, 'yyyy-MM-dd HH:mm:ss') AS ingest")
        .collect()[0]["ingest"]
    )
    assert kept == "2026-05-01 13:00:00"


def test_duplicate_reward_one_payout_and_cost(spark):
    """Duplicate reward_paid event_id → one payout after dedupe."""
    installs = [_base_install()]
    offers = [_offer("of_1", "3.00")]
    events = [
        {
            "user_id": "u1",
            "event_ts": "2026-05-02 10:00:00",
            "event_name": "reward_paid",
            "offer_id": "of_1",
            "event_id": "ev_reward",
            "ingest_ts": "2026-05-02 11:00:00",
        },
        {
            "user_id": "u1",
            "event_ts": "2026-05-02 10:00:00",
            "event_name": "reward_paid",
            "offer_id": "of_1",
            "event_id": "ev_reward",
            "ingest_ts": "2026-05-02 11:05:00",
        },
    ]
    _, silver_events, _ = build_silver_events(spark, installs, events, offers)
    rewards = silver_events.filter("event_name = 'reward_paid'").collect()
    assert len(rewards) == 1
    assert rewards[0]["payout_eur"] == Decimal("3.00")


def test_unknown_offer_preserved(spark):
    """Test 4: unknown offer_view survives with offer_resolved=false."""
    installs = [_base_install()]
    offers = [_offer("of_known")]
    events = [
        {
            "user_id": "u1",
            "event_ts": "2026-05-01 15:00:00",
            "event_name": "offer_view",
            "offer_id": "of_missing",
            "event_id": "ev_unknown",
            "ingest_ts": "2026-05-01 16:00:00",
        }
    ]
    _, silver_events, _ = build_silver_events(spark, installs, events, offers)
    row = silver_events.filter("event_id = 'ev_unknown'").collect()[0]
    assert row is not None
    assert row["offer_resolved"] is False
    assert row["payout_eur"] is None

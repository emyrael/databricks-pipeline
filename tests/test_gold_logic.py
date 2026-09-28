"""Gold SQL logic tests — execute the real SQL, not Python metric duplicates."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from helpers import build_silver_events, compute_gold_via_sql


def _install(
    user_id: str,
    country: str = "DE",
    platform: str = "ios",
    ts: str = "2026-05-01 09:00:00",
):
    return {
        "user_id": user_id,
        "install_ts": ts,
        "country": country,
        "platform": platform,
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


def test_gold_unique_app_open_users(spark):
    installs = [_install("u1")]
    offers = [_offer()]
    events = [
        {
            "user_id": "u1",
            "event_ts": f"2026-05-01 10:0{i}:00",
            "event_name": "app_open",
            "offer_id": "of_1",
            "event_id": f"ev_open_{i}",
            "ingest_ts": f"2026-05-01 11:0{i}:00",
        }
        for i in range(3)
    ]
    silver_installs, silver_events, _ = build_silver_events(
        spark, installs, events, offers
    )
    gold = compute_gold_via_sql(
        spark,
        silver_installs,
        silver_events,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 1),
    )
    row = gold.filter(
        "metric_date = '2026-05-01' AND country = 'DE' AND platform = 'ios'"
    ).collect()[0]
    assert row["unique_app_open_users"] == 1


def test_install_event_fanout_protection(spark):
    installs = [_install("u1")]
    offers = [_offer()]
    events = [
        {
            "user_id": "u1",
            "event_ts": f"2026-05-01 12:{i:02d}:00",
            "event_name": "app_open",
            "offer_id": "of_1",
            "event_id": f"ev_{i}",
            "ingest_ts": f"2026-05-01 13:{i:02d}:00",
        }
        for i in range(10)
    ]
    silver_installs, silver_events, _ = build_silver_events(
        spark, installs, events, offers
    )
    gold = compute_gold_via_sql(
        spark,
        silver_installs,
        silver_events,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 1),
    )
    row = gold.filter("metric_date = '2026-05-01' AND country = 'DE'").collect()[0]
    assert row["installs"] == 1
    assert row["unique_app_open_users"] == 1


def test_late_arrival_uses_event_date(spark):
    installs = [_install("u1", ts="2026-04-30 08:00:00")]
    offers = [_offer()]
    events = [
        {
            "user_id": "u1",
            "event_ts": "2026-05-01 10:00:00",
            "event_name": "app_open",
            "offer_id": "of_1",
            "event_id": "ev_late",
            "ingest_ts": "2026-05-04 10:00:00",
        }
    ]
    silver_installs, silver_events, _ = build_silver_events(
        spark, installs, events, offers
    )
    gold = compute_gold_via_sql(
        spark,
        silver_installs,
        silver_events,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 4),
    )
    may1 = gold.filter("metric_date = DATE '2026-05-01'").collect()
    may4 = gold.filter("metric_date = DATE '2026-05-04'").collect()

    assert len(may1) == 1
    assert may1[0]["unique_app_open_users"] == 1
    assert all(row["unique_app_open_users"] == 0 for row in may4)


def test_gold_sql_is_deterministic(spark):
    """Repeated Gold calculation yields identical logical metrics.

    Delta replaceWhere idempotency is exercised in Databricks; local tests verify
    the deterministic SQL update set without requiring Delta runtime packages.
    """
    installs = [
        _install("u1"),
        _install("u2", country="US", platform="android"),
    ]
    offers = [_offer("of_1", "1.25")]
    events = [
        {
            "user_id": "u1",
            "event_ts": "2026-05-01 10:00:00",
            "event_name": "reward_paid",
            "offer_id": "of_1",
            "event_id": "ev_r1",
            "ingest_ts": "2026-05-01 12:00:00",
        },
        {
            "user_id": "u1",
            "event_ts": "2026-05-01 10:00:00",
            "event_name": "reward_paid",
            "offer_id": "of_1",
            "event_id": "ev_r1",
            "ingest_ts": "2026-05-01 12:05:00",
        },
    ]
    silver_installs, silver_events, _ = build_silver_events(
        spark, installs, events, offers
    )

    def snapshot():
        gold = compute_gold_via_sql(
            spark,
            silver_installs,
            silver_events,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 1),
        )
        return {
            (
                str(row["metric_date"]),
                row["country"],
                row["platform"],
                int(row["installs"]),
                int(row["unique_reward_paid_users"]),
                int(row["reward_payouts"]),
                Decimal(str(row["reward_cost_eur"])),
            )
            for row in gold.collect()
        }

    first = snapshot()
    second = snapshot()
    assert first == second

    reward_rows = [row for row in first if row[4] == 1]
    assert len(reward_rows) == 1
    assert reward_rows[0][5] == 1
    assert reward_rows[0][6] == Decimal("1.25")


def test_unknown_offer_still_in_offer_view_metric(spark):
    installs = [_install("u1")]
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
    silver_installs, silver_events, _ = build_silver_events(
        spark, installs, events, offers
    )
    gold = compute_gold_via_sql(
        spark,
        silver_installs,
        silver_events,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 1),
    )
    row = gold.filter("country = 'DE'").collect()[0]
    assert row["unique_offer_view_users"] == 1

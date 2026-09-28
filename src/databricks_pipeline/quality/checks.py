"""Reusable PySpark data-quality checks. Report issues; do not delete rows."""

from __future__ import annotations

from dataclasses import dataclass

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a single quality check."""

    name: str
    passed: bool
    detail: str
    value: int | float | None = None


def check_event_id_unique(events: DataFrame) -> CheckResult:
    """Silver event_id must be unique after dedupe."""
    dupes = (
        events.groupBy("event_id")
        .count()
        .filter(F.col("count") > 1)
        .count()
    )
    return CheckResult(
        name="silver_event_id_unique",
        passed=dupes == 0,
        detail=f"duplicate event_id groups: {dupes}",
        value=dupes,
    )


def check_install_user_id_unique(installs: DataFrame) -> CheckResult:
    """Silver installs must remain one row per user_id."""
    dupes = (
        installs.groupBy("user_id")
        .count()
        .filter(F.col("count") > 1)
        .count()
    )
    return CheckResult(
        name="silver_install_user_id_unique",
        passed=dupes == 0,
        detail=f"duplicate user_id groups: {dupes}",
        value=dupes,
    )


def check_gold_key_unique(gold: DataFrame) -> CheckResult:
    """Gold logical key (metric_date, country, platform) must be unique."""
    dupes = (
        gold.groupBy("metric_date", "country", "platform")
        .count()
        .filter(F.col("count") > 1)
        .count()
    )
    return CheckResult(
        name="gold_logical_key_unique",
        passed=dupes == 0,
        detail=f"duplicate gold keys: {dupes}",
        value=dupes,
    )


def check_reward_cost_non_negative(gold: DataFrame) -> CheckResult:
    """reward_cost_eur must never be negative."""
    bad = gold.filter(F.col("reward_cost_eur") < 0).count()
    return CheckResult(
        name="reward_cost_eur_non_negative",
        passed=bad == 0,
        detail=f"rows with negative reward_cost_eur: {bad}",
        value=bad,
    )


def check_unknown_offer_count(events: DataFrame) -> CheckResult:
    """Count events whose offer_id did not resolve (informational)."""
    n = events.filter(~F.col("offer_resolved")).count()
    return CheckResult(
        name="unknown_offer_count",
        passed=True,
        detail=f"events with unresolved offer_id: {n}",
        value=n,
    )


def check_event_before_install_count(events: DataFrame) -> CheckResult:
    """Count events timestamped before install (informational)."""
    n = events.filter(F.col("event_before_install")).count()
    return CheckResult(
        name="event_before_install_count",
        passed=True,
        detail=f"events with event_ts < install_ts: {n}",
        value=n,
    )


def check_late_arrival_count(events: DataFrame) -> CheckResult:
    """Count cross-day arrivals (informational)."""
    n = events.filter(F.col("cross_day_arrival")).count()
    return CheckResult(
        name="late_arrival_count",
        passed=True,
        detail=f"events with ingest_date != event_date: {n}",
        value=n,
    )


def check_replay_count(bronze_events: DataFrame, silver_events: DataFrame) -> CheckResult:
    """Count rows removed by event_id dedupe (replay inflation)."""
    bronze_n = bronze_events.count()
    silver_n = silver_events.count()
    replay = bronze_n - silver_n
    return CheckResult(
        name="replay_count",
        passed=True,
        detail=f"bronze={bronze_n}, silver={silver_n}, replay_rows={replay}",
        value=replay,
    )


def run_all_checks(
    *,
    bronze_events: DataFrame | None = None,
    silver_installs: DataFrame | None = None,
    silver_events: DataFrame | None = None,
    gold: DataFrame | None = None,
) -> list[CheckResult]:
    """Run applicable quality checks and return results."""
    results: list[CheckResult] = []
    if silver_events is not None:
        results.append(check_event_id_unique(silver_events))
        results.append(check_unknown_offer_count(silver_events))
        results.append(check_event_before_install_count(silver_events))
        results.append(check_late_arrival_count(silver_events))
    if silver_installs is not None:
        results.append(check_install_user_id_unique(silver_installs))
    if gold is not None:
        results.append(check_gold_key_unique(gold))
        results.append(check_reward_cost_non_negative(gold))
    if bronze_events is not None and silver_events is not None:
        results.append(check_replay_count(bronze_events, silver_events))
    return results

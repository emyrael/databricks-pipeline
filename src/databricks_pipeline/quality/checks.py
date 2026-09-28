"""Reusable PySpark data-quality checks and fail-fast contracts."""

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


def assert_required_non_null(df: DataFrame, columns: list[str], label: str) -> None:
    """Fail when a required key or timestamp is null."""
    condition = None
    for column in columns:
        current = F.col(column).isNull()
        condition = current if condition is None else (condition | current)
    bad = df.filter(condition).limit(1).count() if condition is not None else 0
    if bad:
        raise ValueError(f"{label}: required columns contain nulls: {columns}")


def assert_unique_key(df: DataFrame, key: str, label: str) -> None:
    """Fail when a dimension or fact key is non-unique."""
    has_duplicate = (
        df.groupBy(key)
        .count()
        .filter(F.col("count") > 1)
        .limit(1)
        .count()
    )
    if has_duplicate:
        raise ValueError(f"{label}: {key} is not unique")


def assert_no_key_conflicts(
    incoming: DataFrame,
    existing: DataFrame,
    *,
    key: str,
    compare_columns: list[str],
    label: str,
) -> None:
    """Fail if an incoming existing key changes immutable business fields."""
    if not compare_columns:
        return

    joined = incoming.alias("s").join(
        existing.alias("t"),
        F.col(f"s.{key}").eqNullSafe(F.col(f"t.{key}")),
        "inner",
    )

    conflict = None
    for column in compare_columns:
        differs = ~F.col(f"s.{column}").eqNullSafe(F.col(f"t.{column}"))
        conflict = differs if conflict is None else (conflict | differs)

    if conflict is not None and joined.filter(conflict).limit(1).count():
        raise ValueError(
            f"{label}: incoming {key} conflicts with an existing business row"
        )

def assert_event_replay_shape(events: DataFrame) -> None:
    """Ensure repeated event_ids differ only by ingest_ts.

    The exercise dedupe rule is safe only while business fields for the same
    event_id agree. Conflicting rows are rejected instead of silently collapsed.
    """
    business_row = F.struct("user_id", "event_ts", "event_name", "offer_id")
    conflicts = (
        events.groupBy("event_id")
        .agg(F.countDistinct(business_row).alias("business_variants"))
        .filter(F.col("business_variants") > 1)
        .limit(1)
        .count()
    )
    if conflicts:
        raise ValueError(
            "bronze events: repeated event_id has conflicting business fields"
        )


def assert_no_unresolved_rewards(events: DataFrame) -> None:
    """Fail if a reward cannot resolve a payout."""
    unresolved = (
        events.filter(
            (F.col("event_name") == "reward_paid")
            & (~F.coalesce(F.col("offer_resolved"), F.lit(False)))
        )
        .limit(1)
        .count()
    )
    if unresolved:
        raise ValueError("silver events: reward_paid contains an unresolved offer")


def check_event_id_unique(events: DataFrame) -> CheckResult:
    dupes = (
        events.groupBy("event_id")
        .count()
        .filter(F.col("count") > 1)
        .count()
    )
    return CheckResult(
        "silver_event_id_unique",
        dupes == 0,
        f"duplicate event_id groups: {dupes}",
        dupes,
    )


def check_install_user_id_unique(installs: DataFrame) -> CheckResult:
    dupes = (
        installs.groupBy("user_id")
        .count()
        .filter(F.col("count") > 1)
        .count()
    )
    return CheckResult(
        "silver_install_user_id_unique",
        dupes == 0,
        f"duplicate user_id groups: {dupes}",
        dupes,
    )


def check_gold_key_unique(gold: DataFrame) -> CheckResult:
    dupes = (
        gold.groupBy("metric_date", "country", "platform")
        .count()
        .filter(F.col("count") > 1)
        .count()
    )
    return CheckResult(
        "gold_logical_key_unique",
        dupes == 0,
        f"duplicate gold keys: {dupes}",
        dupes,
    )


def check_reward_cost_non_negative(gold: DataFrame) -> CheckResult:
    bad = gold.filter(F.col("reward_cost_eur") < 0).count()
    return CheckResult(
        "reward_cost_eur_non_negative",
        bad == 0,
        f"rows with negative reward_cost_eur: {bad}",
        bad,
    )


def check_unresolved_reward_count(events: DataFrame) -> CheckResult:
    n = events.filter(
        (F.col("event_name") == "reward_paid")
        & (~F.coalesce(F.col("offer_resolved"), F.lit(False)))
    ).count()
    return CheckResult(
        "unresolved_reward_count",
        n == 0,
        f"reward_paid rows with unresolved offer: {n}",
        n,
    )


def check_unknown_offer_count(events: DataFrame) -> CheckResult:
    n = events.filter(~F.coalesce(F.col("offer_resolved"), F.lit(False))).count()
    return CheckResult(
        "unknown_offer_count",
        True,
        f"events with unresolved offer_id: {n}",
        n,
    )


def check_event_before_install_count(events: DataFrame) -> CheckResult:
    n = events.filter(F.col("event_before_install")).count()
    return CheckResult(
        "event_before_install_count",
        True,
        f"events with event_ts < install_ts: {n}",
        n,
    )


def check_late_arrival_count(events: DataFrame) -> CheckResult:
    n = events.filter(F.col("cross_day_arrival")).count()
    return CheckResult(
        "late_arrival_count",
        True,
        f"events with ingest_date != event_date: {n}",
        n,
    )


def check_replay_count(bronze_events: DataFrame, silver_events: DataFrame) -> CheckResult:
    bronze_n = bronze_events.count()
    silver_n = silver_events.count()
    replay = bronze_n - silver_n
    return CheckResult(
        "replay_count",
        True,
        f"bronze={bronze_n}, silver={silver_n}, replay_rows={replay}",
        replay,
    )


def run_all_checks(
    *,
    bronze_events: DataFrame | None = None,
    silver_installs: DataFrame | None = None,
    silver_events: DataFrame | None = None,
    gold: DataFrame | None = None,
) -> list[CheckResult]:
    """Run applicable checks. Informational anomalies are reported, not deleted."""
    results: list[CheckResult] = []
    if silver_events is not None:
        results.extend(
            [
                check_event_id_unique(silver_events),
                check_unresolved_reward_count(silver_events),
                check_unknown_offer_count(silver_events),
                check_event_before_install_count(silver_events),
                check_late_arrival_count(silver_events),
            ]
        )
    if silver_installs is not None:
        results.append(check_install_user_id_unique(silver_installs))
    if gold is not None:
        results.extend(
            [
                check_gold_key_unique(gold),
                check_reward_cost_non_negative(gold),
            ]
        )
    if bronze_events is not None and silver_events is not None:
        results.append(check_replay_count(bronze_events, silver_events))
    return results

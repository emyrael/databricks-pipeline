#!/usr/bin/env python3
"""Profile the exmox CSVs and write REPORT.md.

Reads every CSV as text so blank fields stay blank. Does not write the source files.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "exmox-data-engineer-databricks" / "data"
REPORT_PATH = ROOT / "REPORT.md"
EXPECTED = ("installs.csv", "events.csv", "offers.csv", "user_profile.csv")
TS_FORMAT = "%Y-%m-%d %H:%M:%S"
NULL_TOKENS = {"nan", "null", "none", "n/a", "na"}
EVENT_CHAIN = (
    ("offer_start", "offer_view"),
    ("goal_reached", "offer_start"),
    ("reward_paid", "goal_reached"),
)


def is_blank(series: pd.Series) -> pd.Series:
    """True for empty or whitespace-only strings."""
    return series.str.strip().eq("")


def read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV without turning empty fields into nulls."""
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)
    return frame.apply(lambda column: column.str.replace("\r", "", regex=False))


def md_table(headers: list[str], rows: list[tuple]) -> str:
    """Render a markdown table. Cell text is already escaped by the caller."""
    head = "| " + " | ".join(headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join([head, rule, *body])


def comma(value: int) -> str:
    """Integer with thousands separators."""
    return f"{int(value):,}"


def percent(part: int, whole: int) -> str:
    """Percent of whole, or n/a when the denominator is zero."""
    if whole == 0:
        return "n/a"
    return f"{(100.0 * part / whole):.2f}%"


def show(value: object) -> str:
    """Show strings in repr so whitespace stays visible."""
    if isinstance(value, str):
        return repr(value)
    return str(value)


def stamp(value: object) -> str:
    """Format a timestamp at second resolution."""
    if pd.isna(value):
        return ""
    return pd.Timestamp(value).strftime(TS_FORMAT)


def money(value: Decimal) -> str:
    """Format an exact decimal sum."""
    return f"{value:.2f}" if value == value.quantize(Decimal("0.01")) else format(value, "f")


def sum_decimal(values) -> Decimal:
    """Sum original numeric strings without binary float error."""
    total = Decimal("0")
    for value in values:
        total += Decimal(value)
    return total


def parse_timestamps(series: pd.Series) -> pd.Series:
    """Parse civil timestamps. Unparseable values become NaT."""
    return pd.to_datetime(series.where(~is_blank(series)), format=TS_FORMAT, errors="coerce")


def numeric(series: pd.Series) -> pd.Series:
    """Parse numbers. Blanks and junk become NaN."""
    return pd.to_numeric(series.where(~is_blank(series)), errors="coerce")


def infer_type(series: pd.Series) -> str:
    """Infer a type from parse success. The file itself stores text."""
    present = series[~is_blank(series)]
    if present.empty:
        return "empty"
    parsed_ts = pd.to_datetime(present, format=TS_FORMAT, errors="coerce")
    if float(parsed_ts.notna().mean()) >= 0.99:
        return "timestamp (no offset in the text)"
    parsed_num = pd.to_numeric(present, errors="coerce")
    if float(parsed_num.notna().mean()) < 0.99:
        return "string"
    whole = parsed_num.dropna() % 1 == 0
    if bool(whole.all()):
        return "integer"
    return "decimal"


def file_overview(path: Path, frame: pd.DataFrame) -> dict:
    """Size, shape, names, and inferred types."""
    return {
        "name": path.name,
        "bytes": path.stat().st_size,
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "types": {column: infer_type(frame[column]) for column in frame.columns},
    }


def missing_report(frame: pd.DataFrame) -> list[dict]:
    """Blank, null-token, and distinct counts for every column."""
    rows = []
    total = len(frame)
    for column in frame.columns:
        series = frame[column]
        blank = int(is_blank(series).sum())
        tokens = int(series.str.strip().str.lower().isin(NULL_TOKENS).sum())
        distinct = int(series.nunique(dropna=False))
        rows.append(
            {
                "column": column,
                "blank": blank,
                "blank_pct": percent(blank, total),
                "null_tokens": tokens,
                "distinct": distinct,
            }
        )
    return rows


def string_variants(series: pd.Series) -> list[tuple[str, list[str]]]:
    """Raw values that collapse together after strip and lower."""
    present = series[~is_blank(series)]
    if present.empty:
        return []
    grouped: dict[str, set[str]] = {}
    for raw in present.unique():
        grouped.setdefault(raw.strip().lower(), set()).add(raw)
    variants = []
    for key in sorted(grouped):
        raws = grouped[key]
        if len(raws) > 1:
            variants.append((key, sorted(raws, key=repr)))
    return variants


def whitespace_counts(series: pd.Series) -> tuple[int, int]:
    """Leading and trailing whitespace counts, excluding all-blank cells."""
    present = series[~is_blank(series)]
    leading = int((present != present.str.lstrip()).sum())
    trailing = int((present != present.str.rstrip()).sum())
    return leading, trailing


def value_counts(series: pd.Series, limit: int | None = None) -> list[tuple[str, int, str]]:
    """Counts in descending frequency, then by label, so ties are stable."""
    total = len(series)
    counts = series.value_counts(dropna=False)
    items = sorted(counts.items(), key=lambda item: (-item[1], repr(item[0])))
    if limit is not None:
        items = items[:limit]
    return [(show(value), int(count), percent(int(count), total)) for value, count in items]


def duplicate_keys(frame: pd.DataFrame, columns: list[str]) -> dict:
    """Duplicate statistics for one key or the full row."""
    if not columns:
        duplicated = frame.duplicated(keep=False)
    else:
        duplicated = frame.duplicated(columns, keep=False)
    extra = int(frame.duplicated(columns).sum()) if columns else int(frame.duplicated().sum())
    groups = int(frame.loc[duplicated, columns[0]].nunique()) if columns and duplicated.any() else 0
    if not columns and duplicated.any():
        groups = int(duplicated.sum())  # not used for full-row group count
    return {
        "rows_in_duplicate_groups": int(duplicated.sum()),
        "extra_rows": extra,
        "groups": groups,
    }


def varying_columns(frame: pd.DataFrame, key: str) -> dict[str, int]:
    """Max distinct values of each other column inside duplicate key groups."""
    duplicated = frame[key].duplicated(keep=False)
    subset = frame.loc[duplicated]
    if subset.empty:
        return {}
    varied = {}
    for column in frame.columns:
        if column == key:
            continue
        most = int(subset.groupby(key, sort=False)[column].nunique(dropna=False).max())
        if most > 1:
            varied[column] = most
    return varied


def example_duplicate_ids(frame: pd.DataFrame, key: str, sample: int = 3) -> list[str]:
    """Stable sample of duplicated key values."""
    duplicated = frame.loc[frame[key].duplicated(keep=False), key]
    return sorted(duplicated.unique(), key=repr)[:sample]


def datetime_report(series: pd.Series) -> dict:
    """Parse success and range. Malformed means non-blank and not the expected format."""
    blank = int(is_blank(series).sum())
    parsed = parse_timestamps(series)
    failures = int((~is_blank(series) & parsed.isna()).sum())
    ok = parsed.dropna()
    zones = int(series.str.contains(r"(?:Z|[+-]\d{2}:?\d{2})$", regex=True).sum())
    shared = int(ok.duplicated(keep=False).sum()) if len(ok) else 0
    return {
        "blank": blank,
        "parsed": int(parsed.notna().sum()),
        "failed": failures,
        "min": stamp(ok.min()) if len(ok) else "",
        "max": stamp(ok.max()) if len(ok) else "",
        "zones": zones,
        "rows_sharing_a_timestamp": shared,
        "values": parsed,
    }


def numeric_report(series: pd.Series) -> dict:
    """Distribution of a parsed numeric column."""
    parsed = numeric(series)
    present = parsed.dropna()
    blank = int(is_blank(series).sum())
    failed = int((~is_blank(series) & parsed.isna()).sum())
    if present.empty:
        return {"blank": blank, "failed": failed, "count": 0}
    quantiles = present.quantile([0.25, 0.5, 0.75]).tolist()
    return {
        "blank": blank,
        "failed": failed,
        "count": int(present.shape[0]),
        "min": float(present.min()),
        "max": float(present.max()),
        "mean": float(present.mean()),
        "median": float(quantiles[1]),
        "std": float(present.std(ddof=1)) if len(present) > 1 else 0.0,
        "p25": float(quantiles[0]),
        "p75": float(quantiles[2]),
        "zeros": int((present == 0).sum()),
        "negatives": int((present < 0).sum()),
        "distinct": int(present.nunique()),
    }


def decimal_place_counts(series: pd.Series) -> dict[int, int]:
    """How many fractional digits the original text uses."""
    present = series[~is_blank(series)]
    places = present.map(lambda value: len(value.split(".", 1)[1]) if "." in value else 0)
    return {int(place): int(count) for place, count in sorted(places.value_counts().items())}


def delay_report(event_ts: pd.Series, ingest_ts: pd.Series) -> dict:
    """ingest_ts - event_ts in seconds, plus calendar-day crossings."""
    both = event_ts.notna() & ingest_ts.notna()
    seconds = (ingest_ts[both] - event_ts[both]).dt.total_seconds()
    event_day = event_ts[both].dt.strftime("%Y-%m-%d")
    ingest_day = ingest_ts[both].dt.strftime("%Y-%m-%d")
    buckets = {
        "negative": int((seconds < 0).sum()),
        "gt_1m": int((seconds > 60).sum()),
        "gt_5m": int((seconds > 300).sum()),
        "gt_15m": int((seconds > 900).sum()),
        "gt_1h": int((seconds > 3600).sum()),
        "gt_6h": int((seconds > 6 * 3600).sum()),
        "gt_24h": int((seconds > 86400).sum()),
        "gt_48h": int((seconds > 2 * 86400).sum()),
    }
    quantiles = seconds.quantile([0.5, 0.9, 0.95, 0.99]).tolist() if len(seconds) else [None] * 4
    return {
        "comparable": int(both.sum()),
        "buckets": buckets,
        "min": None if seconds.empty else float(seconds.min()),
        "max": None if seconds.empty else float(seconds.max()),
        "mean": None if seconds.empty else float(seconds.mean()),
        "p50": None if seconds.empty else float(quantiles[0]),
        "p90": None if seconds.empty else float(quantiles[1]),
        "p95": None if seconds.empty else float(quantiles[2]),
        "p99": None if seconds.empty else float(quantiles[3]),
        "cross_day": int((event_day != ingest_day).sum()),
        "seconds": seconds,
        "event_day": event_day,
        "ingest_day": ingest_day,
    }


def chain_buckets(frame: pd.DataFrame, keys: list[str], earlier: str, later: str) -> dict:
    """Compare earliest timestamps of two event names on one grain.

    Same-timestamp pairs are not counted as strictly prior. That case is separate
    because the file has no sub-second order.
    """
    first = (
        frame.groupby(keys + ["event_name"], sort=False)["event_ts"].min().unstack("event_name")
    )
    if later not in first.columns:
        return {"pairs": 0, "no_earlier": 0, "same_timestamp": 0, "earlier_after": 0, "earlier_before": 0}
    later_ts = first[later].dropna().sort_index()
    if earlier in first.columns:
        earlier_ts = first[earlier].reindex(later_ts.index)
    else:
        earlier_ts = pd.Series(pd.NaT, index=later_ts.index)
    no_earlier = earlier_ts.isna()
    same = earlier_ts.notna() & (earlier_ts == later_ts)
    after = earlier_ts.notna() & (earlier_ts > later_ts)
    before = earlier_ts.notna() & (earlier_ts < later_ts)
    return {
        "pairs": int(len(later_ts)),
        "no_earlier": int(no_earlier.sum()),
        "same_timestamp": int(same.sum()),
        "earlier_after": int(after.sum()),
        "earlier_before": int(before.sum()),
        "examples": _chain_examples(later_ts, earlier_ts, no_earlier | after),
    }


def _chain_examples(later_ts: pd.Series, earlier_ts: pd.Series, mask: pd.Series) -> list[tuple]:
    """Up to three sorted pairs where the earlier step is missing or later."""
    chosen = later_ts.index[mask.reindex(later_ts.index).fillna(False)]
    rows = []
    for key in list(chosen)[:3]:
        user = key[0] if isinstance(key, tuple) else key
        offer = key[1] if isinstance(key, tuple) else ""
        rows.append((user, offer, stamp(later_ts.loc[key]), stamp(earlier_ts.loc[key])))
    return rows


def multiplicity(frame: pd.DataFrame, keys: list[str], event_name: str) -> dict:
    """Pairs whose event name occurs on more than one row or more than one event_id."""
    subset = frame.loc[frame["event_name"] == event_name]
    if subset.empty:
        return {"row_pairs": 0, "id_pairs": 0, "replay_only_pairs": 0, "examples": []}
    grouped = subset.groupby(keys, sort=True).agg(
        rows=("event_id", "size"),
        ids=("event_id", "nunique"),
    )
    row_pairs = grouped[grouped["rows"] > 1]
    id_pairs = grouped[grouped["ids"] > 1]
    replay_only = grouped[(grouped["rows"] > 1) & (grouped["ids"] == 1)]
    examples = []
    for key, row in id_pairs.head(3).iterrows():
        user = key[0] if isinstance(key, tuple) else key
        offer = key[1] if isinstance(key, tuple) else ""
        examples.append((user, offer, int(row["rows"]), int(row["ids"])))
    return {
        "row_pairs": int(len(row_pairs)),
        "id_pairs": int(len(id_pairs)),
        "replay_only_pairs": int(len(replay_only)),
        "examples": examples,
    }


def percentile_row(series: pd.Series) -> dict:
    """Min, max, mean, and the requested upper percentiles."""
    if series.empty:
        return {}
    quantiles = series.quantile([0.5, 0.9, 0.95, 0.99]).tolist()
    return {
        "min": float(series.min()),
        "p50": float(quantiles[0]),
        "p90": float(quantiles[1]),
        "p95": float(quantiles[2]),
        "p99": float(quantiles[3]),
        "max": float(series.max()),
        "mean": float(series.mean()),
    }


def render_missing(rows: list[dict]) -> str:
    """Markdown table of missingness."""
    table = md_table(
        ["Column", "Blank", "Blank %", "Null tokens", "Distinct"],
        [
            (row["column"], comma(row["blank"]), row["blank_pct"], comma(row["null_tokens"]), comma(row["distinct"]))
            for row in rows
        ],
    )
    return (
        "Blank means empty or whitespace-only. Null tokens are the literal strings "
        "nan, null, none, n/a, and na. Nothing was coerced to a real null.\n\n" + table
    )


def render_overview(info: dict) -> str:
    """File-level bullets and the schema table."""
    schema = md_table(
        ["Column", "Inferred type"],
        [(name, info["types"][name]) for name in info["columns"]],
    )
    lines = [
        f"- File: `{info['name']}`",
        f"- Rows: {comma(info['rows'])}",
        f"- Columns: {len(info['columns'])}",
        f"- Size: {comma(info['bytes'])} bytes",
        "- Storage: every field was read as text.",
        "",
        schema,
    ]
    return "\n".join(lines)


def render_distribution(series: pd.Series, full_limit: int = 25) -> str:
    """Full distribution when small, otherwise the top 10."""
    distinct = int(series.nunique(dropna=False))
    if distinct <= full_limit:
        rows = value_counts(series)
        title = f"All {distinct} values."
    else:
        rows = value_counts(series, limit=10)
        title = f"{distinct} distinct values. Top 10."
    leading, trailing = whitespace_counts(series)
    variants = string_variants(series)
    parts = [
        title,
        "",
        md_table(["Value", "Count", "Share of rows"], rows),
        "",
        f"Leading whitespace on non-blank values: {comma(leading)}. "
        f"Trailing whitespace: {comma(trailing)}.",
    ]
    if variants:
        shown = ", ".join(
            f"{key!r} appears as {' and '.join(repr(raw) for raw in raws)}" for key, raws in variants
        )
        parts.append("Values that collapse together after trim and lower-casing: " + shown + ".")
    else:
        parts.append("No trim/case variants: each normalized value comes from one raw spelling.")
    return "\n".join(parts)


def render_numeric(stats: dict) -> str:
    """One numeric distribution."""
    if stats.get("count", 0) == 0:
        return f"No parsed numbers. Blank {stats['blank']:,}, unparsed {stats['failed']:,}."
    return md_table(
        ["Metric", "Value"],
        [
            ("Parsed count", comma(stats["count"])),
            ("Blank", comma(stats["blank"])),
            ("Unparsed", comma(stats["failed"])),
            ("Min", f"{stats['min']:.4f}"),
            ("Max", f"{stats['max']:.4f}"),
            ("Mean", f"{stats['mean']:.4f}"),
            ("Median", f"{stats['median']:.4f}"),
            ("Sample std (ddof=1)", f"{stats['std']:.4f}"),
            ("P25", f"{stats['p25']:.4f}"),
            ("P75", f"{stats['p75']:.4f}"),
            ("Zeros", comma(stats["zeros"])),
            ("Negatives", comma(stats["negatives"])),
            ("Distinct", comma(stats["distinct"])),
        ],
    )


def render_delay(delay: dict) -> str:
    """Delay distribution. Seconds are differences of civil times, not zoned instants."""
    buckets = delay["buckets"]
    comparable = delay["comparable"]
    lines = [
        "Delay is `ingest_ts - event_ts` in seconds. Both columns are civil times with no zone, "
        "so this is not a timezone-corrected duration.",
        "",
        md_table(
            ["Metric", "Value"],
            [
                ("Rows with both timestamps parsed", comma(comparable)),
                ("ingest_ts < event_ts", comma(buckets["negative"])),
                ("Min delay (seconds)", f"{delay['min']:.0f}" if delay["min"] is not None else "n/a"),
                ("Max delay (seconds)", f"{delay['max']:.0f}" if delay["max"] is not None else "n/a"),
                ("Max delay (days)", f"{delay['max'] / 86400:.2f}" if delay["max"] is not None else "n/a"),
                ("Mean (seconds)", f"{delay['mean']:.1f}" if delay["mean"] is not None else "n/a"),
                ("Median (seconds)", f"{delay['p50']:.0f}" if delay["p50"] is not None else "n/a"),
                ("P90 (seconds)", f"{delay['p90']:.0f}" if delay["p90"] is not None else "n/a"),
                ("P95 (seconds)", f"{delay['p95']:.0f}" if delay["p95"] is not None else "n/a"),
                ("P99 (seconds)", f"{delay['p99']:.0f}" if delay["p99"] is not None else "n/a"),
                ("> 1 minute", f"{comma(buckets['gt_1m'])} ({percent(buckets['gt_1m'], comparable)})"),
                ("> 5 minutes", f"{comma(buckets['gt_5m'])} ({percent(buckets['gt_5m'], comparable)})"),
                ("> 15 minutes", f"{comma(buckets['gt_15m'])} ({percent(buckets['gt_15m'], comparable)})"),
                ("> 1 hour", f"{comma(buckets['gt_1h'])} ({percent(buckets['gt_1h'], comparable)})"),
                ("> 6 hours", f"{comma(buckets['gt_6h'])} ({percent(buckets['gt_6h'], comparable)})"),
                ("> 24 hours", f"{comma(buckets['gt_24h'])} ({percent(buckets['gt_24h'], comparable)})"),
                ("> 48 hours", f"{comma(buckets['gt_48h'])} ({percent(buckets['gt_48h'], comparable)})"),
                (
                    "Calendar date of ingest_ts differs from event_ts",
                    f"{comma(delay['cross_day'])} ({percent(delay['cross_day'], comparable)})",
                ),
            ],
        ),
    ]
    return "\n".join(lines)


def render_chain(title: str, result: dict, denominator_label: str) -> str:
    """Four-way split of whether an earlier step exists at a strictly earlier time."""
    pairs = result["pairs"]
    without = result["no_earlier"] + result["earlier_after"]
    lines = [
        f"**{title}** ({comma(pairs)} {denominator_label})",
        "",
        md_table(
            ["Situation", "Pairs", "Share"],
            [
                ("Earlier step exists at a strictly earlier timestamp", comma(result["earlier_before"]), percent(result["earlier_before"], pairs)),
                ("No earlier step on this grain", comma(result["no_earlier"]), percent(result["no_earlier"], pairs)),
                ("Earlier step exists only at a later timestamp", comma(result["earlier_after"]), percent(result["earlier_after"], pairs)),
                ("Earliest timestamps are equal (order not determined)", comma(result["same_timestamp"]), percent(result["same_timestamp"], pairs)),
                ("No strictly-earlier step (first two problem rows combined)", comma(without), percent(without, pairs)),
            ],
        ),
    ]
    if result.get("examples"):
        lines.extend(
            [
                "",
                "Examples of missing or later steps, sorted by key:",
                "",
                md_table(
                    ["user_id", "offer_id", "Later step timestamp", "Earlier step timestamp"],
                    result["examples"],
                ),
            ]
        )
    return "\n".join(lines)


def observations(groups: dict[str, list[str]]) -> str:
    """The four required observation categories. Empty categories stay explicit."""
    order = (
        "Confirmed issue",
        "Suspicious observation",
        "Likely-valid edge case",
        "Unknown / requires business clarification",
    )
    parts = []
    for name in order:
        items = groups.get(name) or ["None identified from the checks in this report."]
        bullets = "\n".join(f"- {item}" for item in items)
        parts.append(f"**{name}**\n\n{bullets}")
    return "\n\n".join(parts)


def analyze(frames: dict[str, pd.DataFrame]) -> dict:
    """All measurements used by the report. No source frame is written back."""
    installs = frames["installs.csv"].copy()
    events = frames["events.csv"].copy()
    offers = frames["offers.csv"].copy()
    profiles = frames["user_profile.csv"].copy()

    installs["install_ts_parsed"] = parse_timestamps(installs["install_ts"])
    events["event_ts_parsed"] = parse_timestamps(events["event_ts"])
    events["ingest_ts_parsed"] = parse_timestamps(events["ingest_ts"])
    profiles["last_seen_parsed"] = parse_timestamps(profiles["last_seen_ts"])
    profiles["events_lifetime_num"] = numeric(profiles["events_lifetime"])
    profiles["revenue_num"] = numeric(profiles["revenue_30d_eur"])
    offers["payout_num"] = numeric(offers["payout_eur"])

    delay = delay_report(events["event_ts_parsed"], events["ingest_ts_parsed"])
    events = events.join(delay["seconds"].rename("delay_seconds"))
    events["event_day"] = events["event_ts_parsed"].dt.strftime("%Y-%m-%d")
    events["ingest_day"] = events["ingest_ts_parsed"].dt.strftime("%Y-%m-%d")
    installs["install_day"] = installs["install_ts_parsed"].dt.strftime("%Y-%m-%d")

    offer_ids = set(offers["offer_id"])
    install_ids = set(installs["user_id"])
    profile_ids = set(profiles["user_id"])
    event_users = set(events["user_id"])

    events["offer_blank"] = is_blank(events["offer_id"])
    events["offer_known"] = events["offer_id"].isin(offer_ids) & ~events["offer_blank"]

    reward = events.loc[events["event_name"] == "reward_paid"].copy()
    reward = reward.merge(
        offers[["offer_id", "offer_category", "payout_type", "payout_eur", "payout_num"]],
        on="offer_id",
        how="left",
    )
    reward = reward.merge(
        installs[["user_id", "country", "platform"]],
        on="user_id",
        how="left",
    )
    reward["payout_resolved"] = reward["payout_num"].notna() & (reward["payout_num"] >= 0)
    resolved = reward.loc[reward["payout_resolved"]].copy()
    resolved_one = (
        resolved.sort_values(["event_id", "ingest_ts", "user_id"], kind="mergesort")
        .drop_duplicates("event_id", keep="first")
    )

    return {
        "frames": frames,
        "installs": installs,
        "events": events,
        "offers": offers,
        "profiles": profiles,
        "delay": delay,
        "offer_ids": offer_ids,
        "install_ids": install_ids,
        "profile_ids": profile_ids,
        "event_users": event_users,
        "reward": reward,
        "resolved": resolved,
        "resolved_one": resolved_one,
    }


def build_report(paths: dict[str, Path], ctx: dict) -> str:
    """Assemble REPORT.md from measured tables."""
    frames = ctx["frames"]
    sections = [
        "# Dataset Profiling Report",
        "",
        "Produced by `python scripts/profile_data.py`. "
        "Source CSVs were read as text (`keep_default_na=False`) and were not modified. "
        "Timestamp differences subtract the civil times as written. No timezone offset is present "
        "to convert.",
        "",
        "## Executive Summary",
        "",
        executive_summary(ctx),
        "",
        "## installs.csv",
        "",
        installs_section(paths["installs.csv"], frames["installs.csv"], ctx),
        "",
        "## events.csv",
        "",
        events_section(paths["events.csv"], frames["events.csv"], ctx),
        "",
        "## offers.csv",
        "",
        offers_section(paths["offers.csv"], frames["offers.csv"], ctx),
        "",
        "## user_profile.csv",
        "",
        profile_section(paths["user_profile.csv"], frames["user_profile.csv"], ctx),
        "",
        "## Cross-File Referential Integrity",
        "",
        referential_section(ctx),
        "",
        "## Reward Cost Analysis",
        "",
        reward_section(ctx),
        "",
        "## Late Arrival Analysis",
        "",
        late_section(ctx),
        "",
        "## Key Findings Before Pipeline Design",
        "",
        findings_section(ctx),
        "",
        "## Questions This Data Raises for the Pipeline",
        "",
        questions_section(ctx),
        "",
    ]
    return "\n".join(sections)


def executive_summary(ctx: dict) -> str:
    """Short headlines. Every number is recomputed here from the frames."""
    events = ctx["events"]
    installs = ctx["installs"]
    profiles = ctx["profiles"]
    delay = ctx["delay"]
    dup_extra = int(events["event_id"].duplicated().sum())
    varied = varying_columns(ctx["frames"]["events.csv"], "event_id")
    cross = delay["cross_day"]
    comparable = delay["comparable"]
    unknown_offer = int((~events["offer_known"]).sum())
    before = int((events["event_ts_parsed"] < events["user_id"].map(
        installs.drop_duplicates("user_id").set_index("user_id")["install_ts_parsed"]
    )).sum())
    raw_cost = sum_decimal(ctx["resolved"]["payout_eur"])
    one_cost = sum_decimal(ctx["resolved_one"]["payout_eur"])
    countries = string_variants(installs["country"])
    lifetime = profiles.set_index("user_id")["events_lifetime_num"]
    row_counts = events.groupby("user_id").size()
    aligned = lifetime.to_frame("profile").join(row_counts.rename("rows"), how="inner")
    exact = int((aligned["profile"] == aligned["rows"]).sum())
    lines = [
        f"Four files: installs {comma(len(installs))} rows, events {comma(len(events))} rows, "
        f"offers {comma(len(ctx['offers']))} rows, user_profile {comma(len(profiles))} rows.",
        "",
        f"- `event_id` has {comma(dup_extra)} extra rows. Inside those groups the columns that "
        f"vary are: {', '.join(varied) if varied else 'none'}.",
        f"- {comma(cross)} of {comma(comparable)} events "
        f"({percent(cross, comparable)}) have an ingest calendar date different from the event date. "
        f"Max delay is {delay['max'] / 86400:.2f} days. "
        f"Rows with ingest_ts before event_ts: {comma(delay['buckets']['negative'])}.",
        f"- Country has {len(countries)} normalized values that are stored as more than one raw spelling.",
        f"- {comma(unknown_offer)} event rows have an offer_id that is not in offers.csv. "
        "The breakdown by event_name is in the referential section. reward_paid is called out there separately.",
        f"- {comma(before)} event rows have event_ts earlier than the matching install_ts.",
        f"- Summing offer payout on every resolved reward_paid row gives {money(raw_cost)} EUR. "
        f"Keeping one row per event_id (earliest ingest_ts) gives {money(one_cost)} EUR. "
        "The second figure is a sensitivity, not a decision that event_id should be deduped.",
        f"- user_profile.events_lifetime equals the raw event-row count for {comma(exact)} of "
        f"{comma(len(aligned))} matched users. The profile has no day, country, or platform column.",
    ]
    return "\n".join(lines)


def installs_section(path: Path, raw: pd.DataFrame, ctx: dict) -> str:
    """installs.csv chapter."""
    info = file_overview(path, raw)
    frame = ctx["installs"]
    user_dup = duplicate_keys(raw, ["user_id"])
    full_dup = int(raw.duplicated().sum())
    campaign_blank = is_blank(raw["campaign_id"])
    organic = raw["media_source"].str.strip().str.lower().eq("organic")
    blank_and_organic = int((campaign_blank & organic).sum())
    organic_rows = int(organic.sum())
    blank_rows = int(campaign_blank.sum())
    before_users = int(
        ctx["events"]
        .loc[ctx["events"]["event_ts_parsed"] < ctx["events"]["user_id"].map(
            frame.drop_duplicates("user_id").set_index("user_id")["install_ts_parsed"]
        ), "user_id"]
        .nunique()
    )
    day_counts = frame.groupby("install_day").size().rename("installs").sort_index()
    day_table = md_table(
        ["install date", "installs"],
        [(day, comma(int(count))) for day, count in day_counts.items() if isinstance(day, str)],
    )
    ts = datetime_report(raw["install_ts"])
    grain_ok = user_dup["extra_rows"] == 0 and int(is_blank(raw["user_id"]).sum()) == 0
    obs = {
        "Confirmed issue": [],
        "Suspicious observation": [],
        "Likely-valid edge case": [],
        "Unknown / requires business clarification": [
            "Timestamps have no zone. It is not known whether install_ts, event_ts, and ingest_ts share one clock.",
        ],
    }
    if not grain_ok:
        obs["Confirmed issue"].append(
            f"user_id is not a unique non-blank key (extra rows {user_dup['extra_rows']})."
        )
    else:
        obs["Likely-valid edge case"].append(
            "user_id is unique and non-blank, so the stated one-row-per-user grain holds in this file."
        )
    if string_variants(raw["country"]):
        obs["Suspicious observation"].append(
            "country contains spellings that differ only by case and trailing space. "
            "They may be the same country codes, but the file stores them as different strings."
        )
    if blank_rows and blank_and_organic == blank_rows and blank_rows == organic_rows:
        obs["Likely-valid edge case"].append(
            f"All {comma(blank_rows)} blank campaign_id values are media_source 'organic', "
            f"and every organic row has a blank campaign_id."
        )
        obs["Unknown / requires business clarification"].append(
            "Is a blank campaign_id the expected encoding of organic, or a missing attribute?"
        )
    elif blank_rows:
        obs["Suspicious observation"].append(
            f"campaign_id is blank on {comma(blank_rows)} rows "
            f"({comma(blank_and_organic)} of those are organic; organic rows: {comma(organic_rows)})."
        )
    obs["Unknown / requires business clarification"].append(
        f"{comma(before_users)} users have at least one event_ts before install_ts. "
        "Whether that is clock skew, a late install record, or a real pre-install event is not determined by the files."
    )
    parts = [
        "### Overview",
        "",
        render_overview(info),
        "",
        "### Schema",
        "",
        "Column names and inferred types are in the overview table. "
        "Inference used a 99% parse threshold and did not change the file.",
        "",
        "### Uniqueness and Duplicates",
        "",
        f"Stated grain: one row per user. `user_id` distinct values: {comma(raw['user_id'].nunique())} "
        f"out of {comma(len(raw))} rows. Extra rows beyond the first user_id: {comma(user_dup['extra_rows'])}. "
        f"Fully identical duplicate rows: {comma(full_dup)}.",
        "",
        "The stated grain "
        + ("holds: user_id is unique and non-blank." if grain_ok else "does not hold."),
        "",
        "No other single column is close to unique (country, platform, media_source, device_model, "
        "campaign_id, and install_ts all repeat). install_ts is a time, not a key.",
        "",
        "### Missing Values",
        "",
        render_missing(missing_report(raw)),
        "",
        "### Categorical Distributions",
        "",
        "**country**",
        "",
        render_distribution(raw["country"]),
        "",
        "**platform**",
        "",
        render_distribution(raw["platform"]),
        "",
        "**media_source**",
        "",
        render_distribution(raw["media_source"]),
        "",
        "**device_model**",
        "",
        render_distribution(raw["device_model"]),
        "",
        "**campaign_id**",
        "",
        render_distribution(raw["campaign_id"]),
        "",
        "campaign_id blank vs organic:",
        "",
        md_table(
            ["", "organic", "not organic"],
            [
                (
                    "campaign blank",
                    comma(blank_and_organic),
                    comma(blank_rows - blank_and_organic),
                ),
                (
                    "campaign present",
                    comma(organic_rows - blank_and_organic),
                    comma(len(raw) - organic_rows - (blank_rows - blank_and_organic)),
                ),
            ],
        ),
        "",
        "### Date Analysis",
        "",
        f"install_ts parsed {comma(ts['parsed'])}, failed {comma(ts['failed'])}, blank {comma(ts['blank'])}. "
        f"Range {ts['min']} to {ts['max']}. Timezone offsets found: {comma(ts['zones'])}. "
        f"Rows sharing a timestamp with another row: {comma(ts['rows_sharing_a_timestamp'])}.",
        "",
        f"Distinct install dates: {comma(day_counts.shape[0])}.",
        "",
        day_table,
        "",
        "### Data Quality Observations",
        "",
        observations(obs),
    ]
    return "\n".join(parts)


def events_section(path: Path, raw: pd.DataFrame, ctx: dict) -> str:
    """events.csv chapter, including lifecycle on two grains."""
    info = file_overview(path, raw)
    frame = ctx["events"]
    key_dup = duplicate_keys(raw, ["event_id"])
    full_dup = int(raw.duplicated().sum())
    varied = varying_columns(raw, "event_id")
    sample_ids = example_duplicate_ids(raw, "event_id", 2)
    example_rows = raw.loc[raw["event_id"].isin(sample_ids)].sort_values(
        ["event_id", "ingest_ts", "user_id"], kind="mergesort"
    )
    example_table = md_table(
        list(raw.columns),
        [tuple(show(value) for value in row) for row in example_rows.itertuples(index=False, name=None)],
    )
    max_copies = (
        int(raw.loc[raw["event_id"].duplicated(keep=False)].groupby("event_id").size().max())
        if key_dup["extra_rows"]
        else 1
    )
    composite = ["user_id", "event_ts", "event_name", "offer_id"]
    composite_extra = int(raw.duplicated(composite).sum())
    ts_event = datetime_report(raw["event_ts"])
    ts_ingest = datetime_report(raw["ingest_ts"])
    by_name = (
        frame.groupby("event_name").size().rename("rows").to_frame()
        .assign(share=lambda data: data["rows"].map(lambda count: percent(int(count), len(frame))))
        .sort_values("rows", ascending=False)
    )
    activity = user_activity(ctx)
    chain_offer = {
        (later, earlier): chain_buckets(frame, ["user_id", "offer_id"], earlier, later)
        for later, earlier in EVENT_CHAIN
    }
    chain_user = {
        (later, earlier): chain_buckets(frame, ["user_id"], earlier, later)
        for later, earlier in EVENT_CHAIN
    }
    multi_offer = {
        name: multiplicity(frame, ["user_id", "offer_id"], name)
        for name in ("reward_paid", "goal_reached", "offer_start", "offer_view", "app_open")
    }
    obs = {
        "Confirmed issue": [
            f"`event_id` is not unique: {comma(key_dup['groups'])} ids account for "
            f"{comma(key_dup['extra_rows'])} extra rows (max copies of one id: {max_copies}). "
            "If event_id is the event identity, the stated one-row-per-event grain does not hold.",
        ],
        "Suspicious observation": [],
        "Likely-valid edge case": [],
        "Unknown / requires business clarification": [
            "The duplicate rows are not enough, by themselves, to decide which ingest_ts is the one a metric should keep.",
            "Lifecycle gaps below are counts, not a judgment that the sequence is illegal.",
        ],
    }
    if varied == {"ingest_ts": 2} or list(varied) == ["ingest_ts"]:
        obs["Suspicious observation"].append(
            "Within duplicate event_id groups, the only column that takes more than one value is ingest_ts. "
            "That is what a replay of the same event would look like. It is still an inference."
        )
    elif varied:
        obs["Confirmed issue"].append(
            "Duplicate event_id groups also differ in: " + ", ".join(f"{name} (up to {n} values)" for name, n in sorted(varied.items())) + "."
        )
    if full_dup == 0:
        obs["Suspicious observation"].append("There are no fully identical duplicate rows. The extra event_id rows are not byte-identical copies.")
    parts = [
        "### Overview",
        "",
        render_overview(info),
        "",
        "### Schema",
        "",
        "Types in the overview are inferred. event_name is the event type column in this file "
        "(there is no column named event_type).",
        "",
        "### Uniqueness and Duplicates",
        "",
        f"`event_id` distinct: {comma(raw['event_id'].nunique())} of {comma(len(raw))} rows. "
        f"Extra rows: {comma(key_dup['extra_rows'])}. Duplicate groups: {comma(key_dup['groups'])}. "
        f"Fully identical rows: {comma(full_dup)}. "
        f"Extra rows on (user_id, event_ts, event_name, offer_id): {comma(composite_extra)}.",
        "",
        "Columns that vary inside a duplicated event_id: "
        + (", ".join(f"{name} (max distinct {n})" for name, n in sorted(varied.items())) if varied else "none")
        + ".",
        "",
        "The stated grain is one row per event. Under event_id, that grain does not hold. "
        "No other column is a plausible key (user_id, offer_id, and both timestamps all repeat heavily).",
        "",
        "Two duplicated ids, all of their rows:",
        "",
        example_table,
        "",
        "### Missing Values",
        "",
        render_missing(missing_report(raw)),
        "",
        "### Event Type Distribution",
        "",
        md_table(
            ["event_name", "Rows", "Share"],
            [(show(name), comma(int(row.rows)), row.share) for name, row in by_name.iterrows()],
        ),
        "",
        "### Event Time Analysis",
        "",
        f"event_ts parsed {comma(ts_event['parsed'])}, failed {comma(ts_event['failed'])}, "
        f"blank {comma(ts_event['blank'])}. Range {ts_event['min']} to {ts_event['max']}. "
        f"Timezone offsets: {comma(ts_event['zones'])}. "
        f"Rows sharing an event_ts value: {comma(ts_event['rows_sharing_a_timestamp'])}.",
        "",
        "### Ingest Time Analysis",
        "",
        f"ingest_ts parsed {comma(ts_ingest['parsed'])}, failed {comma(ts_ingest['failed'])}, "
        f"blank {comma(ts_ingest['blank'])}. Range {ts_ingest['min']} to {ts_ingest['max']}. "
        f"Timezone offsets: {comma(ts_ingest['zones'])}. "
        f"Rows sharing an ingest_ts value: {comma(ts_ingest['rows_sharing_a_timestamp'])}.",
        "",
        "Per-day ingest counts and the event-date comparison are in Late Arrival Analysis.",
        "",
        "### Event vs Ingest Delay",
        "",
        render_delay(ctx["delay"]),
        "",
        "### Event Lifecycle Checks",
        "",
        "These counts use the earliest event_ts of each event_name. "
        "Repeated event_id rows with the same event_ts do not create a second step. "
        "A same-timestamp pair has no sub-second order in this file, so it is not treated as 'prior'.",
        "",
        "Grain: (user_id, offer_id). This does not look across offers.",
        "",
        "\n\n".join(
            render_chain(
                f"{later} vs earlier {earlier}",
                chain_offer[(later, earlier)],
                "pairs with at least one " + later,
            )
            for later, earlier in EVENT_CHAIN
        ),
        "",
        "The same three checks ignoring offer_id (user grain only):",
        "",
        "\n\n".join(
            render_chain(
                f"{later} vs earlier {earlier}, any offer",
                chain_user[(later, earlier)],
                "users with at least one " + later,
            )
            for later, earlier in EVENT_CHAIN
        ),
        "",
        "Multiple events of the same name on one (user_id, offer_id). "
        "`replay_only` means several rows but a single event_id.",
        "",
        md_table(
            ["event_name", "Pairs with >1 row", "Pairs with >1 event_id", "Replay-only pairs"],
            [
                (
                    name,
                    comma(multi_offer[name]["row_pairs"]),
                    comma(multi_offer[name]["id_pairs"]),
                    comma(multi_offer[name]["replay_only_pairs"]),
                )
                for name in ("app_open", "offer_view", "offer_start", "goal_reached", "reward_paid")
            ],
        ),
        "",
        activity,
        "",
        "### Data Quality Observations",
        "",
        observations(obs),
    ]
    return "\n".join(parts)


def user_activity(ctx: dict) -> str:
    """Distributions of activity per install user, including users with no events."""
    events = ctx["events"]
    installs = ctx["installs"]
    resolved_one = ctx["resolved_one"]
    per_user = events.groupby("user_id").agg(
        rows=("event_id", "size"),
        distinct_ids=("event_id", "nunique"),
        offers=("offer_id", "nunique"),
    )
    rewards = (
        events.loc[events["event_name"] == "reward_paid"]
        .groupby("user_id")
        .agg(reward_rows=("event_id", "size"), reward_ids=("event_id", "nunique"))
    )
    cost = resolved_one.groupby("user_id")["payout_eur"].agg(lambda values: sum_decimal(values))
    population = installs[["user_id"]].drop_duplicates().set_index("user_id")
    population = population.join(per_user, how="left").join(rewards, how="left")
    population["rows"] = population["rows"].fillna(0)
    population["distinct_ids"] = population["distinct_ids"].fillna(0)
    population["offers"] = population["offers"].fillna(0)
    population["reward_rows"] = population["reward_rows"].fillna(0)
    population["reward_ids"] = population["reward_ids"].fillna(0)
    population = population.join(cost.rename("cost"), how="left")
    zero_events = int((population["rows"] == 0).sum())
    zero_in_events_file = int(len(set(installs["user_id"]) - ctx["event_users"]))

    def pct_table(series: pd.Series, label: str) -> str:
        stats = percentile_row(series.astype(float))
        return md_table(
            ["Population", "Min", "P50", "P90", "P95", "P99", "Max", "Mean"],
            [(
                label,
                f"{stats['min']:.0f}",
                f"{stats['p50']:.0f}",
                f"{stats['p90']:.0f}",
                f"{stats['p95']:.0f}",
                f"{stats['p99']:.0f}",
                f"{stats['max']:.0f}",
                f"{stats['mean']:.2f}",
            )],
        )

    cost_filled = population["cost"].map(lambda value: Decimal("0") if pd.isna(value) else value)
    cost_stats = percentile_row(pd.Series([float(value) for value in cost_filled]))
    top = population.sort_values(["rows", "user_id"], ascending=[False, True]).head(10)
    top_rows = []
    for user_id, row in top.iterrows():
        top_rows.append(
            (
                user_id,
                comma(int(row.rows)),
                comma(int(row.distinct_ids)),
                comma(int(row.offers)),
                comma(int(row.reward_ids)),
                money(row.cost) if not pd.isna(row.cost) else "0.00",
            )
        )
    above_p99 = int((population["rows"] > population["rows"].quantile(0.99)).sum())
    return "\n".join(
        [
            "### User Activity",
            "",
            "Populations are install users, so users with no event rows are included as zero. "
            f"Install users with no event row: {comma(zero_events)} "
            f"(set difference against events.user_id: {comma(zero_in_events_file)}).",
            "",
            pct_table(population["rows"], "Event rows"),
            "",
            pct_table(population["distinct_ids"], "Distinct event_id"),
            "",
            pct_table(population["offers"], "Distinct offer_id on events"),
            "",
            pct_table(population["reward_ids"], "Distinct reward_paid event_id"),
            "",
            "Reward cost per install user, EUR, counting one resolved row per reward event_id "
            "and zero when the user has none. This is a description of the join, not a billing rule.",
            "",
            md_table(
                ["Min", "P50", "P90", "P95", "P99", "Max", "Mean"],
                [(
                    f"{cost_stats['min']:.2f}",
                    f"{cost_stats['p50']:.2f}",
                    f"{cost_stats['p90']:.2f}",
                    f"{cost_stats['p95']:.2f}",
                    f"{cost_stats['p99']:.2f}",
                    f"{cost_stats['max']:.2f}",
                    f"{cost_stats['mean']:.2f}",
                )],
            ),
            "",
            f"Users above the P99 of event rows ({population['rows'].quantile(0.99):.0f}): {comma(above_p99)}. "
            "That cut is descriptive. It is not evidence those users are invalid.",
            "",
            "Top 10 install users by event rows. Cost uses one row per resolved reward event_id.",
            "",
            md_table(
                ["user_id", "Event rows", "Distinct event_id", "Distinct offer_id", "Distinct reward ids", "Cost EUR"],
                top_rows,
            ),
        ]
    )


def offers_section(path: Path, raw: pd.DataFrame, ctx: dict) -> str:
    """offers.csv chapter."""
    info = file_overview(path, raw)
    places = decimal_place_counts(raw["payout_eur"])
    stats = numeric_report(raw["payout_eur"])
    extra = int(raw.duplicated(["offer_id"]).sum())
    full_dup = int(raw.duplicated().sum())
    referenced = ctx["events"].loc[ctx["events"]["offer_known"], "offer_id"].nunique()
    never = sorted(set(raw["offer_id"]) - set(ctx["events"].loc[~is_blank(ctx["events"]["offer_id"]), "offer_id"]))
    paid_ids = set(ctx["reward"].loc[ctx["reward"]["payout_resolved"], "offer_id"])
    never_paid = sorted(set(raw["offer_id"]) - paid_ids)

    def grouped(column: str) -> str:
        rows = []
        for key, part in raw.groupby(column, sort=True):
            parsed = numeric(part["payout_eur"]).dropna()
            rows.append(
                (
                    show(key),
                    comma(len(part)),
                    f"{parsed.min():.2f}" if len(parsed) else "n/a",
                    f"{parsed.median():.2f}" if len(parsed) else "n/a",
                    f"{parsed.max():.2f}" if len(parsed) else "n/a",
                    f"{parsed.mean():.2f}" if len(parsed) else "n/a",
                )
            )
        return md_table(["Value", "Offers", "Min EUR", "Median", "Max", "Mean"], rows)

    obs = {
        "Confirmed issue": [],
        "Suspicious observation": [],
        "Likely-valid edge case": [
            "offer_id is unique and non-blank, and every payout_eur parses as a non-negative number. "
            "The stated one-row-per-offer grain holds in this file.",
        ],
        "Unknown / requires business clarification": [
            "It is not known whether payout_eur is a current attribute that can change later. "
            "This file is a single extract, so history cannot be observed.",
            "Whether every event_name should resolve to one of these offer ids is not stated by the files. "
            "See the referential breakdown.",
        ],
    }
    if extra or stats.get("negatives") or stats.get("failed"):
        obs["Confirmed issue"].append(
            f"offer_id extra rows {extra}, negative payouts {stats.get('negatives', 0)}, "
            f"unparsed payouts {stats.get('failed', 0)}."
        )
        obs["Likely-valid edge case"] = []
    parts = [
        "### Overview",
        "",
        render_overview(info),
        "",
        "### Schema",
        "",
        "payout_eur is decimal text. Other columns are strings. No timestamp column is present.",
        "",
        "### Uniqueness and Duplicates",
        "",
        f"`offer_id` distinct {comma(raw['offer_id'].nunique())} of {comma(len(raw))}. "
        f"Extra rows: {comma(extra)}. Fully identical rows: {comma(full_dup)}.",
        "",
        "The stated one-row-per-offer grain holds." if extra == 0 else "The stated grain does not hold.",
        "",
        "### Missing Values",
        "",
        render_missing(missing_report(raw)),
        "",
        "### Payout Analysis",
        "",
        render_numeric(stats),
        "",
        "Fractional digits in the original payout text:",
        "",
        md_table(
            ["Decimal places", "Offers"],
            [(str(place), comma(count)) for place, count in places.items()],
        ),
        "",
        f"Zeros: {comma(stats.get('zeros', 0))}. Negatives: {comma(stats.get('negatives', 0))}. "
        f"Unparsed: {comma(stats.get('failed', 0))}.",
        "",
        "### Category / Payout Type Distribution",
        "",
        "**offer_category**",
        "",
        render_distribution(raw["offer_category"]),
        "",
        grouped("offer_category"),
        "",
        "**payout_type**",
        "",
        render_distribution(raw["payout_type"]),
        "",
        grouped("payout_type"),
        "",
        f"Distinct offer_id values referenced by at least one event: {comma(referenced)} of {comma(len(raw))}. "
        f"Offer ids never present on an event row: {comma(len(never))}. "
        f"Offer ids with no resolved reward_paid row: {comma(len(never_paid))}.",
        "",
        "### Data Quality Observations",
        "",
        observations(obs),
    ]
    return "\n".join(parts)


def profile_section(path: Path, raw: pd.DataFrame, ctx: dict) -> str:
    """user_profile.csv chapter and the reconciliation."""
    info = file_overview(path, raw)
    extra = int(raw.duplicated(["user_id"]).sum())
    full_dup = int(raw.duplicated().sum())
    ts = datetime_report(raw["last_seen_ts"])
    recon = reconcile(ctx)
    obs = {
        "Confirmed issue": [],
        "Suspicious observation": [],
        "Likely-valid edge case": [],
        "Unknown / requires business clarification": [
            "events_lifetime, last_seen_ts, revenue_30d_eur, and is_payer are names, not definitions. "
            "Match rates below test specific readings. A low match rate rejects that reading. "
            "It does not by itself say which reading is correct.",
            "is_payer is the strings 'True' and 'False'. The file does not say whether that means the user paid, "
            "or that a reward was paid to the user.",
        ],
    }
    if extra == 0 and int(is_blank(raw["user_id"]).sum()) == 0:
        obs["Likely-valid edge case"].append(
            "user_id is unique and non-blank. The stated one-row-per-user grain holds in this file."
        )
    else:
        obs["Confirmed issue"].append(f"user_id extra rows: {extra}.")
    exact_rows = recon["lifetime_exact"]["rows"]
    if exact_rows < len(raw):
        obs["Suspicious observation"].append(
            f"events_lifetime equals the raw event-row count for {comma(exact_rows)} of {comma(len(raw))} users. "
            "It is not a straight count of events.csv rows."
        )
    parts = [
        "### Overview",
        "",
        render_overview(info),
        "",
        "### Schema",
        "",
        "events_lifetime parses as an integer, revenue_30d_eur as a decimal, last_seen_ts as a timestamp, "
        "is_payer as a string.",
        "",
        "### Uniqueness and Duplicates",
        "",
        f"`user_id` distinct {comma(raw['user_id'].nunique())} of {comma(len(raw))}. "
        f"Extra rows: {comma(extra)}. Fully identical rows: {comma(full_dup)}.",
        "",
        "### Missing Values",
        "",
        render_missing(missing_report(raw)),
        "",
        "### Lifetime Metric Analysis",
        "",
        "**events_lifetime**",
        "",
        render_numeric(numeric_report(raw["events_lifetime"])),
        "",
        "**revenue_30d_eur**",
        "",
        render_numeric(numeric_report(raw["revenue_30d_eur"])),
        "",
        "Decimal places in revenue_30d_eur text:",
        "",
        md_table(
            ["Decimal places", "Rows"],
            [(str(place), comma(count)) for place, count in decimal_place_counts(raw["revenue_30d_eur"]).items()],
        ),
        "",
        "**is_payer**",
        "",
        render_distribution(raw["is_payer"]),
        "",
        "**last_seen_ts**",
        "",
        f"Parsed {comma(ts['parsed'])}, failed {comma(ts['failed'])}, blank {comma(ts['blank'])}. "
        f"Range {ts['min']} to {ts['max']}. Timezone offsets: {comma(ts['zones'])}.",
        "",
        "### Reconciliation With Events",
        "",
        recon["markdown"],
        "",
        "### Data Quality Observations",
        "",
        observations(obs),
    ]
    return "\n".join(parts)


def reconcile(ctx: dict) -> dict:
    """Compare profile columns only under readings that are stated as readings."""
    profiles = ctx["profiles"].set_index("user_id")
    events = ctx["events"]
    counts = events.groupby("user_id").agg(
        rows=("event_id", "size"),
        distinct_ids=("event_id", "nunique"),
    )
    without_open = events.loc[events["event_name"] != "app_open"].groupby("user_id").size()
    without_open_ids = (
        events.loc[events["event_name"] != "app_open"].groupby("user_id")["event_id"].nunique()
    )
    max_event = events.groupby("user_id")["event_ts_parsed"].max()
    max_ingest = events.groupby("user_id")["ingest_ts_parsed"].max()
    max_open = (
        events.loc[events["event_name"] == "app_open"].groupby("user_id")["event_ts_parsed"].max()
    )
    base = profiles.join(counts, how="left").join(without_open.rename("rows_no_open"), how="left")
    base = base.join(without_open_ids.rename("ids_no_open"), how="left")
    base = base.join(max_event.rename("max_event"), how="left")
    base = base.join(max_ingest.rename("max_ingest"), how="left")
    base = base.join(max_open.rename("max_open"), how="left")

    def exact_numeric(column: str) -> int:
        left = base["events_lifetime_num"]
        right = base[column]
        return int((left.notna() & right.notna() & (left == right)).sum())

    lifetime_rows = [
        ("Raw event rows", exact_numeric("rows")),
        ("Distinct event_id", exact_numeric("distinct_ids")),
        ("Rows excluding app_open", exact_numeric("rows_no_open")),
        ("Distinct event_id excluding app_open", exact_numeric("ids_no_open")),
    ]
    diff = base["events_lifetime_num"] - base["rows"]
    examples = (
        base.assign(diff=diff)
        .sort_values("diff", key=lambda series: series.abs(), ascending=False)
        .head(5)
    )
    example_table = md_table(
        ["user_id", "events_lifetime", "Event rows", "Difference"],
        [
            (user, f"{row.events_lifetime_num:.0f}", comma(int(row.rows)), f"{row['diff']:.0f}")
            for user, row in examples.iterrows()
        ],
    )

    def time_match(column: str) -> tuple[int, float]:
        delta = (base["last_seen_parsed"] - base[column]).dt.total_seconds()
        exact = int((delta == 0).sum())
        median = float(delta.median()) if delta.notna().any() else float("nan")
        return exact, median

    time_rows = []
    for label, column in (
        ("max event_ts", "max_event"),
        ("max ingest_ts", "max_ingest"),
        ("max app_open event_ts", "max_open"),
    ):
        exact, median = time_match(column)
        time_rows.append((label, comma(exact), f"{median:.0f}"))

    cost = ctx["resolved_one"].groupby("user_id")["payout_eur"].agg(lambda values: sum_decimal(values))
    revenue = profiles["revenue_30d_eur"].map(lambda value: Decimal(value) if str(value).strip() else None)
    compared = revenue.to_frame("revenue").join(cost.rename("cost"), how="left")
    compared["cost"] = compared["cost"].map(lambda value: Decimal("0") if pd.isna(value) else value)
    lifetime_money_match = int(sum(left == right for left, right in zip(compared["revenue"], compared["cost"])))

    has_reward = set(ctx["events"].loc[ctx["events"]["event_name"] == "reward_paid", "user_id"])
    payer = profiles["is_payer"]
    revenue_pos = profiles["revenue_num"] > 0
    cross_rows = []
    for flag in sorted(payer.unique(), key=repr):
        mask = payer == flag
        users = payer.index[mask]
        cross_rows.append(
            (
                show(flag),
                comma(int(mask.sum())),
                comma(int((mask & revenue_pos).sum())),
                comma(int(mask.sum() - (mask & revenue_pos).sum())),
                comma(len(set(users) & has_reward)),
                comma(int(mask.sum()) - len(set(users) & has_reward)),
            )
        )

    with_events = int(base["rows"].notna().sum())
    markdown = "\n".join(
        [
            f"Profile users: {comma(len(base))}. "
            f"Of those, {comma(with_events)} appear in events.csv and "
            f"{comma(len(base) - with_events)} have no event row. "
            "A user with no event row is not counted as equal in the table below, "
            "because there is no derived count to compare. Zeros were not filled in.",
            "",
            "events_lifetime versus four counts derived from events.csv. "
            "These are candidate readings of the column name, not known definitions. "
            f"The denominator is all {comma(len(base))} profile users.",
            "",
            md_table(
                ["Reading", "Users equal"],
                [
                    (
                        label,
                        f"{comma(count)} / {comma(len(base))} "
                        f"({comma(count)} / {comma(with_events)} among users with events)",
                    )
                    for label, count in lifetime_rows
                ],
            ),
            "",
            "Largest absolute gaps versus raw event rows (profile minus rows):",
            "",
            example_table,
            "",
            "last_seen_ts versus three candidate clocks. Median is last_seen minus that clock, in seconds. "
            "A negative median means last_seen is earlier than the candidate.",
            "",
            md_table(["Candidate", "Users equal", "Median delta seconds"], time_rows),
            "",
            "revenue_30d_eur compared with the sum of resolved reward payouts, one row per reward event_id, "
            f"over all time: exact match for {comma(lifetime_money_match)} of {comma(len(compared))} users. "
            "That reading treats a 30-day revenue column as lifetime reward cost. The name does not say that. "
            "The match rate only shows whether the reading is plausible.",
            "",
            "A 30-day window was not applied. Choosing the window end (last_seen_ts, max event_ts, or a fixed date) "
            "would be a business rule, and none is in the files.",
            "",
            "is_payer against revenue_30d_eur > 0 and against having any reward_paid row:",
            "",
            md_table(
                ["is_payer", "Users", "revenue > 0", "revenue = 0 or blank", "Has reward_paid", "No reward_paid"],
                cross_rows,
            ),
            "",
            "Does user_profile look consistent with the event log? Only in part. "
            f"events_lifetime matches the raw row count for {comma(lifetime_rows[0][1])} users "
            f"and matches distinct event_id for {comma(lifetime_rows[1][1])} users, "
            "so it is not a straight count of this file. "
            f"last_seen_ts equals max event_ts for {time_rows[0][1]} users "
            f"(median delta {time_rows[0][2]} seconds) and equals max ingest_ts for "
            f"{time_rows[1][1]} users (median delta {time_rows[1][2]} seconds). "
            "revenue_30d_eur is not the lifetime reward sum under the reading above.",
            "",
            "Could it be the source of truth for a daily gold table of installs, users by event, and reward cost "
            "by day, country, and platform? No. The file has one row per user and no day, country, or platform. "
            "Those grains live on installs and events. Consistency problems above are additional reasons not to "
            "treat the lifetime numbers as a substitute for the event log, even at user grain.",
        ]
    )
    return {"markdown": markdown, "lifetime_exact": {"rows": lifetime_rows[0][1]}}


def referential_section(ctx: dict) -> str:
    """Shared-id checks."""
    events = ctx["events"]
    installs = ctx["installs"]
    raw_offers = ctx["frames"]["offers.csv"]
    missing_user = int((~events["user_id"].isin(ctx["install_ids"])).sum())
    missing_user_ids = int(events.loc[~events["user_id"].isin(ctx["install_ids"]), "user_id"].nunique())
    installs_without = int((~installs["user_id"].isin(ctx["event_users"])).sum())
    profile_not_install = sorted(ctx["profile_ids"] - ctx["install_ids"])
    install_not_profile = sorted(ctx["install_ids"] - ctx["profile_ids"])
    counts = events.groupby("user_id").size()
    high = percentile_row(counts.astype(float))
    offer_gap = (
        events.loc[~events["offer_known"]]
        .groupby("event_name")
        .size()
        .rename("rows")
        .to_frame()
    )
    name_totals = events.groupby("event_name").size().rename("total")
    offer_gap = offer_gap.join(name_totals, how="right").fillna({"rows": 0})
    offer_gap["rows"] = offer_gap["rows"].astype(int)
    blank_by_name = events.groupby("event_name")["offer_blank"].sum().astype(int)
    known_offers = set(raw_offers["offer_id"])
    event_offer_ids = set(events.loc[~events["offer_blank"], "offer_id"])
    never = sorted(known_offers - event_offer_ids)
    unknown_ids = sorted(event_offer_ids - known_offers)
    unknown_after = [value for value in unknown_ids if value > max(known_offers)]
    unknown_examples = (
        events.loc[~events["offer_known"], ["event_name", "offer_id"]]
        .drop_duplicates()
        .sort_values(["event_name", "offer_id"])
        .groupby("event_name")
        .head(3)
    )
    before = events.merge(
        installs[["user_id", "install_ts_parsed"]],
        on="user_id",
        how="left",
    )
    before = before.loc[before["event_ts_parsed"].notna() & before["install_ts_parsed"].notna()].copy()
    before["seconds_before"] = (before["install_ts_parsed"] - before["event_ts_parsed"]).dt.total_seconds()
    early = before.loc[before["seconds_before"] > 0]
    by_type = []
    for name, part in before.groupby("event_name", sort=True):
        flag = part["seconds_before"] > 0
        by_type.append(
            (
                show(name),
                comma(int(flag.sum())),
                percent(int(flag.sum()), len(part)),
                comma(int(part.loc[flag, "user_id"].nunique())),
                comma(int(part.loc[flag, "event_id"].nunique())),
            )
        )
    examples = early.sort_values(["seconds_before", "user_id"], ascending=[False, True]).head(5)
    example_rows = [
        (
            row.user_id,
            row.event_id,
            row.event_name,
            stamp(row.event_ts_parsed),
            stamp(row.install_ts_parsed),
            f"{row.seconds_before:.0f}",
        )
        for row in examples.itertuples(index=False)
    ]
    parts = [
        "installs.user_id vs events.user_id",
        "",
        md_table(
            ["Check", "Result"],
            [
                ("Event rows whose user_id is not in installs", comma(missing_user)),
                ("Distinct event user_ids missing from installs", comma(missing_user_ids)),
                ("Install rows whose user_id has no event", comma(installs_without)),
                ("Duplicate user_id in installs", comma(int(installs["user_id"].duplicated().sum()))),
                ("Duplicate user_id in user_profile", comma(int(ctx["profiles"]["user_id"].duplicated().sum()))),
                ("user_profile ids missing from installs", comma(len(profile_not_install))),
                ("Install ids missing from user_profile", comma(len(install_not_profile))),
            ],
        ),
        "",
        "Event rows per user (users who appear in events): "
        f"min {high['min']:.0f}, median {high['p50']:.0f}, p99 {high['p99']:.0f}, max {high['max']:.0f}. "
        "Top users are listed in the events user-activity section. High counts are not labeled invalid.",
        "",
        "events.offer_id vs offers.offer_id. Blank offer_id is counted separately and is not called invalid.",
        "",
        md_table(
            ["event_name", "Rows", "Blank offer_id", "offer_id not in offers.csv", "Share not in offers"],
            [
                (
                    show(name),
                    comma(int(offer_gap.loc[name, "total"])),
                    comma(int(blank_by_name.get(name, 0))),
                    comma(int(offer_gap.loc[name, "rows"])),
                    percent(int(offer_gap.loc[name, "rows"]), int(offer_gap.loc[name, "total"])),
                )
                for name in offer_gap.sort_index().index
            ],
        ),
        "",
        f"Offer ids in offers.csv never used on an event: {comma(len(never))}. "
        f"offers.csv offer_id runs from {min(known_offers)!r} to {max(known_offers)!r}. "
        f"Distinct event offer_ids missing from that file: {comma(len(unknown_ids))}"
        + (
            f", from {min(unknown_ids)!r} to {max(unknown_ids)!r}. "
            f"{comma(len(unknown_after))} of those sort after {max(known_offers)!r}."
            if unknown_ids
            else "."
        ),
        "",
        "Example unknown offer ids (up to three per event_name):",
        "",
        md_table(
            ["event_name", "offer_id"],
            [(show(row.event_name), show(row.offer_id)) for row in unknown_examples.itertuples(index=False)],
        ),
        "",
        "event_ts compared with install_ts on the matching user. "
        "Positive seconds means the event is before the install. Users with no install cannot appear here.",
        "",
        md_table(
            ["event_name", "Rows before install", "Share of that event", "Users", "Distinct event_id"],
            by_type,
        ),
        "",
        f"Event rows before the install: {comma(len(early))}. "
        f"Users with at least one: {comma(early['user_id'].nunique())}.",
        "",
        "Largest gaps (install_ts minus event_ts):",
        "",
        md_table(
            ["user_id", "event_id", "event_name", "event_ts", "install_ts", "Seconds before install"],
            example_rows,
        ),
    ]
    return "\n".join(parts)


def reward_section(ctx: dict) -> str:
    """Reward rows joined to offers and installs."""
    reward = ctx["reward"]
    resolved = ctx["resolved"]
    one = ctx["resolved_one"]
    raw_cost = sum_decimal(resolved["payout_eur"])
    one_cost = sum_decimal(one["payout_eur"])
    unresolved = int((~reward["payout_resolved"]).sum())
    no_install = int(reward["country"].isna().sum()) if "country" in reward else 0
    # country can be a real NA only if the merge missed. Our read has no NA; missing install leaves NaN after merge.
    missing_install = int(reward["platform"].isna().sum())

    def grouped(frame: pd.DataFrame, column: str) -> list[tuple]:
        rows = []
        for key, part in frame.groupby(column, dropna=False, sort=True):
            label = "<no install match>" if pd.isna(key) else show(key)
            rows.append((label, comma(len(part)), comma(part["event_id"].nunique()), money(sum_decimal(part["payout_eur"]))))
        return rows

    by_offer = grouped(one, "offer_id")
    parts = [
        f"reward_paid rows: {comma(len(reward))}. "
        f"Distinct users: {comma(reward['user_id'].nunique())}. "
        f"Distinct event_id: {comma(reward['event_id'].nunique())}. "
        f"Distinct offer_id on those rows: {comma(reward['offer_id'].nunique())}.",
        "",
        f"Rows with no usable non-negative payout in offers.csv: {comma(unresolved)}. "
        f"Reward rows whose user_id did not match an install: {comma(missing_install)}.",
        "",
        "Cost if every resolved reward row is summed: "
        f"{money(raw_cost)} EUR on {comma(len(resolved))} rows. "
        "Cost if each resolved event_id is kept once, at its earliest ingest_ts: "
        f"{money(one_cost)} EUR on {comma(len(one))} rows. "
        f"The difference is {money(raw_cost - one_cost)} EUR. "
        "That difference is the inflation from counting duplicate event_id rows. "
        "It is not a recommendation to drop them.",
        "",
        "Groupings below use the one-row-per-event_id sensitivity so the duplicate ids are not summed twice. "
        "The date is the calendar date of event_ts, which is a description of the column, not a decision that it is the reporting day. "
        "Country and platform come from the install.",
        "",
        "By event date: see the daily table in Late Arrival Analysis (reward cost column).",
        "",
        "**By country**",
        "",
        md_table(["country", "Rows", "Distinct event_id", "Cost EUR"], grouped(one, "country")),
        "",
        "**By platform**",
        "",
        md_table(["platform", "Rows", "Distinct event_id", "Cost EUR"], grouped(one, "platform")),
        "",
        f"**By offer_id** ({comma(len(by_offer))} offers that have a resolved reward)",
        "",
        md_table(["offer_id", "Rows", "Distinct event_id", "Cost EUR"], by_offer),
        "",
        f"Install match gaps in the reward join: {comma(no_install)} rows with no country after the join.",
    ]
    return "\n".join(parts)


def late_section(ctx: dict) -> str:
    """Delay, cross-day counts, and event-date versus ingest-date volumes."""
    events = ctx["events"]
    delay = ctx["delay"]
    both = events["event_ts_parsed"].notna() & events["ingest_ts_parsed"].notna()
    usable = events.loc[both].copy()
    usable["cross"] = usable["event_day"] != usable["ingest_day"]
    usable["gt_24h"] = usable["delay_seconds"] > 86400
    by_type = []
    for name, part in usable.groupby("event_name", sort=True):
        by_type.append(
            (
                show(name),
                comma(len(part)),
                comma(int(part["cross"].sum())),
                percent(int(part["cross"].sum()), len(part)),
                f"{part['delay_seconds'].median():.0f}",
                f"{part['delay_seconds'].quantile(0.99):.0f}",
            )
        )
    by_day = []
    for day, part in usable.groupby("event_day", sort=True):
        by_day.append(
            (
                day,
                comma(len(part)),
                comma(int(part["cross"].sum())),
                percent(int(part["cross"].sum()), len(part)),
                comma(int(part["gt_24h"].sum())),
            )
        )
    event_counts = usable.groupby("event_day").size()
    ingest_counts = usable.groupby("ingest_day").size()
    install_counts = ctx["installs"].groupby("install_day").size()
    reward_one = ctx["resolved_one"]
    reward_one = reward_one.loc[reward_one["event_ts_parsed"].notna()].copy()
    reward_one["event_day"] = reward_one["event_ts_parsed"].dt.strftime("%Y-%m-%d")
    reward_rows = reward_one.groupby("event_day").size()
    reward_cost = reward_one.groupby("event_day")["payout_eur"].agg(lambda values: sum_decimal(values))
    active = usable.groupby("event_day")["user_id"].nunique()
    type_counts = usable.pivot_table(
        index="event_day", columns="event_name", values="event_id", aggfunc="size", fill_value=0
    )
    names = [name for name in ("app_open", "offer_view", "offer_start", "goal_reached", "reward_paid") if name in type_counts.columns]
    days = sorted(set(event_counts.index) | set(ingest_counts.index) | set(install_counts.index))
    daily_rows = []
    gaps = []
    for day in days:
        event_n = int(event_counts.get(day, 0))
        ingest_n = int(ingest_counts.get(day, 0))
        gaps.append((day, event_n, ingest_n, event_n - ingest_n))
        daily_rows.append(
            (
                day,
                comma(int(install_counts.get(day, 0))),
                comma(event_n),
                comma(int(active.get(day, 0))),
                *[comma(int(type_counts[name].get(day, 0))) if day in type_counts.index else "0" for name in names],
                comma(int(reward_rows.get(day, 0))),
                money(reward_cost.get(day, Decimal("0"))),
                comma(ingest_n),
            )
        )
    gaps_sorted = sorted(gaps, key=lambda item: abs(item[3]), reverse=True)[:10]
    slow = usable.sort_values(["delay_seconds", "event_id"], ascending=[False, True]).head(8)
    slow_rows = [
        (
            row.event_id,
            row.user_id,
            row.event_name,
            stamp(row.event_ts_parsed),
            stamp(row.ingest_ts_parsed),
            f"{row.delay_seconds:.0f}",
            f"{row.delay_seconds / 86400:.2f}",
        )
        for row in slow.itertuples(index=False)
    ]
    only_event = [day for day, event_n, ingest_n, _ in gaps if event_n and not ingest_n]
    only_ingest = [day for day, event_n, ingest_n, _ in gaps if ingest_n and not event_n]
    parts = [
        render_delay(delay),
        "",
        "By event_name:",
        "",
        md_table(
            ["event_name", "Rows", "Cross calendar day", "Share", "Median delay s", "P99 delay s"],
            by_type,
        ),
        "",
        "By event date. A row is late-arriving for this table when its ingest calendar date differs, "
        "and separately when the delay exceeds 24 hours. Those are not the same cut: a 23:50 event ingested "
        "at 00:10 the next day crosses a date inside one hour.",
        "",
        md_table(
            ["event date", "Events", "Cross calendar day", "Share", "Delay > 24h"],
            by_day,
        ),
        "",
        "Largest absolute gaps between events dated on that day and events ingested on that day. "
        "A positive gap means more events happened that day than were ingested that day.",
        "",
        md_table(
            ["Date", "By event date", "By ingest date", "Event minus ingest"],
            [(day, comma(a), comma(b), comma(c)) for day, a, b, c in gaps_sorted],
        ),
        "",
        "Dates present as an event date and absent as an ingest date: "
        + (", ".join(only_event) if only_event else "none")
        + ". Dates present as an ingest date and absent as an event date: "
        + (", ".join(only_ingest) if only_ingest else "none")
        + ".",
        "",
        "Most delayed events:",
        "",
        md_table(
            ["event_id", "user_id", "event_name", "event_ts", "ingest_ts", "Delay seconds", "Delay days"],
            slow_rows,
        ),
        "",
        "### Daily counts",
        "",
        "Installs use install_ts. Event columns and active users use event_ts. "
        "Reward cost uses one resolved row per reward event_id. Ingested events use ingest_ts. "
        "A zero means that date has no rows in that column, not that the date was dropped.",
        "",
        md_table(
            ["Date", "Installs", "Events", "Active users", *names, "Reward ids", "Reward cost EUR", "Ingested events"],
            daily_rows,
        ),
    ]
    return "\n".join(parts)


def findings_section(ctx: dict) -> str:
    """Cross-dataset findings. Each row is an observation, with confidence labeled."""
    events = ctx["events"]
    delay = ctx["delay"]
    raw_cost = sum_decimal(ctx["resolved"]["payout_eur"])
    one_cost = sum_decimal(ctx["resolved_one"]["payout_eur"])
    unknown = int((~events["offer_known"] & ~events["offer_blank"]).sum())
    reward_unknown = int((ctx["reward"]["event_name"].eq("reward_paid") & ~ctx["reward"]["payout_resolved"]).sum())
    early = ctx["events"].merge(ctx["installs"][["user_id", "install_ts_parsed"]], on="user_id", how="left")
    early_n = int((early["event_ts_parsed"] < early["install_ts_parsed"]).sum())
    countries = string_variants(ctx["installs"]["country"])
    lifetime_match = reconcile(ctx)["lifetime_exact"]["rows"]
    rows = [
        (
            "event_id is not unique",
            f"{comma(int(events['event_id'].duplicated().sum()))} extra rows; only ingest_ts varies inside the groups",
            "Counting rows counts the same event more than once, including reward cost",
            "High",
            "Yes — confirm event_id is the identity, and which ingest_ts to keep",
        ),
        (
            "Ingest often falls on a later calendar day than the event",
            f"{comma(delay['cross_day'])} of {comma(delay['comparable'])} rows; max delay {delay['max'] / 86400:.2f} days; ingest before event: {comma(delay['buckets']['negative'])}",
            "A job that closes a calendar day at 00:15 will miss rows whose event_ts is that day but whose ingest_ts is later",
            "High",
            "Yes — how long a day must stay open",
        ),
        (
            "country spellings differ by case and trailing space",
            f"{len(countries)} normalized codes have more than one raw spelling",
            "A group-by on the raw string splits one country",
            "High",
            "Yes — confirm trim and upper-case is acceptable",
        ),
        (
            "Some event offer_ids are not in offers.csv",
            f"{comma(unknown)} non-blank unknown offer rows; unresolved reward_paid rows: {comma(reward_unknown)}",
            "Depends on event_name. Reward cost cannot be priced when reward_paid does not resolve. Other event types may not need a known offer",
            "High",
            "Yes — which event names must reference offers.csv",
        ),
        (
            "Some events are timestamped before the user's install",
            f"{comma(early_n)} rows with event_ts < install_ts",
            "Dropping them changes user and event counts. Keeping them leaves activity before the install",
            "High",
            "Yes — clock skew versus real pre-install activity",
        ),
        (
            "Duplicate reward rows change the EUR total",
            f"{money(raw_cost)} EUR on all resolved rows vs {money(one_cost)} EUR on one row per event_id",
            "Reward cost moves by the difference if duplicates are counted",
            "High",
            "Yes — same question as the event_id identity",
        ),
        (
            "user_profile is not a projection of the event log",
            f"events_lifetime equals raw event rows for {comma(lifetime_match)} users; no day, country, or platform columns",
            "It cannot build the daily country-platform grain, and the lifetime fields do not reproduce simple event aggregates",
            "High",
            "Yes — what events_lifetime, last_seen_ts, revenue_30d_eur, and is_payer mean",
        ),
        (
            "Lifecycle steps are sometimes missing or out of timestamp order",
            "See the four-way splits in the events section, on both (user, offer) and user grains",
            "Enforcing a strict funnel in silver would drop or quarantine real-looking rows",
            "Medium",
            "Yes — which sequences are allowed",
        ),
        (
            "Timestamps have no timezone",
            "Zero values match a trailing Z or numeric offset",
            "Day boundaries move if the strings are not already in the reporting zone",
            "High",
            "Yes — which clock the strings are in",
        ),
        (
            "Blank campaign_id lines up with organic",
            "Checked as a cross-tab in the installs section",
            "Treating blank campaign as a data error would blank out organic acquisition",
            "Medium",
            "Yes — expected encoding of organic",
        ),
    ]
    return md_table(
        ["Finding", "Evidence", "Potential impact", "Confidence", "Needs business clarification?"],
        rows,
    )


def questions_section(ctx: dict) -> str:
    """Design questions that the measurements actually raise. Not a design."""
    delay = ctx["delay"]
    questions = [
        "Is `event_id` the deduplication key? Duplicate groups differ in `ingest_ts` only, but the files do not define the key.",
        "If one row per `event_id` is kept, which `ingest_ts` should win? The rows disagree, and the metric changes if reward rows are counted twice "
        f"({money(sum_decimal(ctx['resolved']['payout_eur']))} EUR vs {money(sum_decimal(ctx['resolved_one']['payout_eur']))} EUR on the two readings above).",
        "Which timestamp is the reporting day: `event_ts`, `ingest_ts`, or `install_ts`? "
        f"{comma(delay['cross_day'])} events do not have the same calendar date on event_ts and ingest_ts.",
        f"How long does a closed day need to stay correctable? The maximum observed delay is {delay['max'] / 86400:.2f} days, "
        f"and {comma(delay['buckets']['gt_48h'])} rows exceed 48 hours. A one-day window does not cover the observed tail.",
        "Should an offer_id missing from offers.csv be kept, quarantined, or rejected? The answer may differ by event_name, "
        "because unknown ids are not confined to reward_paid. See the referential table before choosing one rule.",
        "What should happen to event_ts values that precede install_ts? The files show the gap and do not say whether it is an error.",
        "Is user_profile a reconciliation source only? It cannot supply day, country, or platform, and its lifetime fields do not match simple event aggregates.",
        "Can offer payout change over time? offers.csv is one row per offer_id with no effective date, so a change would be invisible in this extract.",
        "Which silver checks are safe to enforce? Uniqueness of event_id is not true of the raw file. "
        "A required offer, a required prior funnel step, and event_ts >= install_ts all fail for some observed rows.",
        "Do the timestamp strings share one timezone? None of them carry an offset, so a calendar-day rule is ambiguous until that is known.",
        "Is a blank campaign_id on organic installs intentional? The blank values and the organic rows are the same set in this file.",
    ]
    return "\n".join(f"- {question}" for question in questions)


def main() -> int:
    """Profile every CSV in the data directory and write REPORT.md."""
    found = sorted(path.name for path in DATA_DIR.glob("*.csv"))
    missing = [name for name in EXPECTED if name not in found]
    if missing:
        print("Missing CSVs: " + ", ".join(missing), file=sys.stderr)
        return 1
    paths = {name: DATA_DIR / name for name in found}
    frames = {name: read_csv(path) for name, path in paths.items()}
    unexpected = [name for name in found if name not in EXPECTED]
    if unexpected:
        print("Additional CSVs will be omitted from the chapter list: " + ", ".join(unexpected))
    ctx = analyze({name: frames[name] for name in EXPECTED})
    report = build_report({name: paths[name] for name in EXPECTED}, ctx)
    REPORT_PATH.write_text(report)
    print(f"Wrote {REPORT_PATH}")
    for name in EXPECTED:
        print(f"{name} rows={len(frames[name])} cols={len(frames[name].columns)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Date-window helpers for late-arrival correction."""

from __future__ import annotations

from datetime import date, timedelta


def parse_process_date(value: str | date) -> date:
    """Parse an ISO date string or pass through a date object."""
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def correction_window(
    process_date: date,
    *,
    window_days: int = 7,
) -> tuple[date, date]:
    """Return inclusive [start, end] for the late-arrival correction window.

    Evidence: max observed ingest delay ≈ 5.58 days, so a 7-day window
    (process_date - 6 through process_date) is used for this exercise.
    """
    if window_days < 1:
        raise ValueError("window_days must be >= 1")
    start = process_date - timedelta(days=window_days - 1)
    return start, process_date

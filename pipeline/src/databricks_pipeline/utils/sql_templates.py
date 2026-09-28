"""Simple SQL template rendering (placeholder substitution)."""

from __future__ import annotations

from pathlib import Path


def render_sql_template(template: str, mapping: dict[str, str]) -> str:
    """Replace ``{{key}}`` placeholders with values from ``mapping``."""
    rendered = template
    for key, value in mapping.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def load_and_render_sql(path: str | Path, mapping: dict[str, str]) -> str:
    """Read a SQL file and render ``{{placeholders}}``."""
    text = Path(path).read_text(encoding="utf-8")
    return render_sql_template(text, mapping)

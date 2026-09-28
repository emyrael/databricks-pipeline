"""Reusable helpers shared across Bronze, Silver, and Gold.

Import submodules directly when you need a specific helper, e.g.::

    from databricks_pipeline.utils.io import write_delta_overwrite
    from databricks_pipeline.utils.dates import correction_window
"""

from databricks_pipeline.utils.bootstrap import ensure_package_on_path
from databricks_pipeline.utils.dates import correction_window, parse_process_date
from databricks_pipeline.utils.io import (
    merge_delta,
    read_csv_with_schema,
    table_exists,
    write_delta_overwrite,
)
from databricks_pipeline.utils.paths import resolve_source_csv
from databricks_pipeline.utils.sql_templates import render_sql_template

# catalog.ensure_schemas imports PipelineConfig — keep it lazy to avoid cycles.
def __getattr__(name: str):
    if name == "ensure_schemas":
        from databricks_pipeline.utils.catalog import ensure_schemas

        return ensure_schemas
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "correction_window",
    "ensure_package_on_path",
    "ensure_schemas",
    "merge_delta",
    "parse_process_date",
    "read_csv_with_schema",
    "render_sql_template",
    "resolve_source_csv",
    "table_exists",
    "write_delta_overwrite",
]

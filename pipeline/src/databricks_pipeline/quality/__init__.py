"""Quality check package."""

from databricks_pipeline.quality.checks import CheckResult, run_all_checks

__all__ = ["CheckResult", "run_all_checks"]

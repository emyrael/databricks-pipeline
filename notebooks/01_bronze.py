# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 01 — Bronze ingestion
# MAGIC Batch-read CSVs from `workspace.rewards.landing` into Bronze Delta tables.
# MAGIC Business logic lives in `databricks_pipeline.bronze` — this notebook is a thin driver.
# MAGIC
# MAGIC Landing layout::
# MAGIC
# MAGIC     /Volumes/workspace/rewards/landing/<source>/load_date=YYYY-MM-DD/<source>.csv

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("bronze_schema", "rewards_bronze")
dbutils.widgets.text("data_dir", "/Volumes/workspace/rewards/landing")
dbutils.widgets.text("load_date", "2026-09-28")
dbutils.widgets.text(
    "repo_src",
    "/Workspace/Users/<your-email>/databricks-pipeline/src",
)

# COMMAND ----------

import sys
from pathlib import Path

# Make the repo package importable on Databricks (Repos/Git folders are not on sys.path).
_repo_src = Path(dbutils.widgets.get("repo_src"))
if (_repo_src / "databricks_pipeline").exists() and str(_repo_src) not in sys.path:
    sys.path.insert(0, str(_repo_src))

from databricks_pipeline.bronze import run_bronze
from databricks_pipeline.config import PipelineConfig
from databricks_pipeline.utils import ensure_schemas
from databricks_pipeline.utils.dates import parse_process_date

config = PipelineConfig(
    catalog=dbutils.widgets.get("catalog"),
    bronze_schema=dbutils.widgets.get("bronze_schema"),
    data_dir=Path(dbutils.widgets.get("data_dir")),
    load_date=parse_process_date(dbutils.widgets.get("load_date")),
)

ensure_schemas(spark, config)
counts = run_bronze(spark, config)
display(counts)
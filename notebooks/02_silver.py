# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 02 — Silver transforms
# MAGIC Transform the current Bronze batch and merge it into Silver Delta tables.
# MAGIC Use full_refresh=true for the first load; normal runs are incremental.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("bronze_schema", "rewards_bronze")
dbutils.widgets.text("silver_schema", "rewards_silver")
dbutils.widgets.text("full_refresh", "false")
dbutils.widgets.text(
    "repo_src",
    "/Workspace/Users/emyraeleson@gmail.com/databricks-pipeline_flow/src",
)

# COMMAND ----------

import sys
from pathlib import Path

_repo_src = Path(dbutils.widgets.get("repo_src"))
if (_repo_src / "databricks_pipeline").exists() and str(_repo_src) not in sys.path:
    sys.path.insert(0, str(_repo_src))

from databricks_pipeline.config import PipelineConfig
from databricks_pipeline.pipeline import run_silver
from databricks_pipeline.utils import ensure_schemas

config = PipelineConfig(
    catalog=dbutils.widgets.get("catalog"),
    bronze_schema=dbutils.widgets.get("bronze_schema"),
    silver_schema=dbutils.widgets.get("silver_schema"),
)
full_refresh = dbutils.widgets.get("full_refresh").lower() in {"1", "true", "yes"}

ensure_schemas(spark, config)
counts = run_silver(spark, config, full_refresh=full_refresh)
print(f"Silver mode: {'full refresh' if full_refresh else 'incremental merge'}")
display(counts)

# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 03 — Gold daily metrics
# MAGIC Python runtime driver for the Gold step.
# MAGIC The business metric definition itself lives in `gold/sql/daily_metrics.sql`.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("silver_schema", "rewards_silver")
dbutils.widgets.text("gold_schema", "rewards_gold")
dbutils.widgets.text("process_date", "2026-05-27")
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
from databricks_pipeline.pipeline import run_gold
from databricks_pipeline.utils import ensure_schemas, parse_process_date

config = PipelineConfig(
    catalog=dbutils.widgets.get("catalog"),
    silver_schema=dbutils.widgets.get("silver_schema"),
    gold_schema=dbutils.widgets.get("gold_schema"),
)
process_date = parse_process_date(dbutils.widgets.get("process_date"))
full_refresh = dbutils.widgets.get("full_refresh").lower() in {"1", "true", "yes"}

ensure_schemas(spark, config)
gold_scope = run_gold(spark, config, process_date, full_refresh=full_refresh)

print(f"Gold mode: {'full refresh' if full_refresh else 'correction-window replace'}")
print(f"Gold rows in scope: {gold_scope.count()}")
display(gold_scope.orderBy("metric_date", "country", "platform").limit(50))

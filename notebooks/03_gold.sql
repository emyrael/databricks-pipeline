-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 03 — Gold daily metrics (SQL)
-- MAGIC Recompute `metric_date × country × platform` for the correction window.
-- MAGIC Uses the SQL definition in `gold/sql/daily_metrics.sql` via Python helpers
-- MAGIC so placeholders stay parameterized (no hard-coded dates).

-- COMMAND ----------

-- MAGIC %python
-- MAGIC dbutils.widgets.text("catalog", "workspace")
-- MAGIC dbutils.widgets.text("silver_schema", "rewards_silver")
-- MAGIC dbutils.widgets.text("gold_schema", "rewards_gold")
-- MAGIC dbutils.widgets.text("process_date", "2026-05-27")
-- MAGIC dbutils.widgets.text("full_refresh", "false")

-- COMMAND ----------

-- MAGIC %python
-- MAGIC from databricks_pipeline.config import PipelineConfig
-- MAGIC from databricks_pipeline.pipeline import run_gold
-- MAGIC from databricks_pipeline.utils import ensure_schemas, parse_process_date
-- MAGIC
-- MAGIC config = PipelineConfig(
-- MAGIC     catalog=dbutils.widgets.get("catalog"),
-- MAGIC     silver_schema=dbutils.widgets.get("silver_schema"),
-- MAGIC     gold_schema=dbutils.widgets.get("gold_schema"),
-- MAGIC )
-- MAGIC process_date = parse_process_date(dbutils.widgets.get("process_date"))
-- MAGIC full_refresh = dbutils.widgets.get("full_refresh").lower() in {"1", "true", "yes"}
-- MAGIC
-- MAGIC ensure_schemas(spark, config)
-- MAGIC gold_scope = run_gold(spark, config, process_date, full_refresh=full_refresh)
-- MAGIC print(f"Gold rows in scope: {gold_scope.count()}")
-- MAGIC display(gold_scope.orderBy("metric_date", "country", "platform").limit(50))

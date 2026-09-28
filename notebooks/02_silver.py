# Databricks notebook source
# MAGIC %md
# MAGIC # 02 — Silver transforms
# MAGIC Read Bronze, apply PySpark Silver transforms, write Silver Delta tables.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("bronze_schema", "rewards_bronze")
dbutils.widgets.text("silver_schema", "rewards_silver")

# COMMAND ----------

from databricks_pipeline.config import PipelineConfig
from databricks_pipeline.pipeline import run_silver
from databricks_pipeline.utils import ensure_schemas

config = PipelineConfig(
    catalog=dbutils.widgets.get("catalog"),
    bronze_schema=dbutils.widgets.get("bronze_schema"),
    silver_schema=dbutils.widgets.get("silver_schema"),
)

ensure_schemas(spark, config)
counts = run_silver(spark, config)
display(counts)

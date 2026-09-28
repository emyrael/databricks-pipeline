# Databricks notebook source
# MAGIC %md
# MAGIC # 04 — Quality checks & verification
# MAGIC Run reusable quality checks and print whole-dataset verification totals.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("bronze_schema", "rewards_bronze")
dbutils.widgets.text("silver_schema", "rewards_silver")
dbutils.widgets.text("gold_schema", "rewards_gold")
dbutils.widgets.text(
    "repo_src",
    "/Workspace/Users/emyraeleson@gmail.com/databricks-pipeline_flow/src",
)

# COMMAND ----------

import sys
from pathlib import Path

from pyspark.sql import functions as F

_repo_src = Path(dbutils.widgets.get("repo_src"))
if (_repo_src / "databricks_pipeline").exists() and str(_repo_src) not in sys.path:
    sys.path.insert(0, str(_repo_src))

from databricks_pipeline.config import PipelineConfig
from databricks_pipeline.quality import run_all_checks

config = PipelineConfig(
    catalog=dbutils.widgets.get("catalog"),
    bronze_schema=dbutils.widgets.get("bronze_schema"),
    silver_schema=dbutils.widgets.get("silver_schema"),
    gold_schema=dbutils.widgets.get("gold_schema"),
)

bronze_events = spark.table(config.bronze_events)
silver_events = spark.table(config.silver_events)
silver_installs = spark.table(config.silver_installs)
gold = spark.table(config.gold_daily_metrics)

results = run_all_checks(
    bronze_events=bronze_events,
    silver_installs=silver_installs,
    silver_events=silver_events,
    gold=gold,
)
for r in results:
    status = "PASS" if r.passed else "FAIL"
    print(f"[{status}] {r.name}: {r.detail}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Expected verification numbers (from profiling / spec)

# COMMAND ----------

raw_event_rows = bronze_events.count()
distinct_event_id = bronze_events.select("event_id").distinct().count()
reward_raw = bronze_events.filter(F.col("event_name") == "reward_paid")
reward_raw_rows = reward_raw.count()
distinct_reward_id = reward_raw.select("event_id").distinct().count()

# Raw reward cost (all bronze reward rows resolved to silver offers payout)
offers = spark.table(config.silver_offers).select(
    F.col("offer_id"), F.col("payout_eur").alias("payout")
)
raw_cost = (
    reward_raw.join(offers, "offer_id", "left")
    .agg(F.sum("payout").alias("cost"))
    .collect()[0]["cost"]
)

# Deduped reward cost from Silver
silver_reward = silver_events.filter(F.col("event_name") == "reward_paid")
deduped_cost = silver_reward.agg(F.sum("payout_eur").alias("cost")).collect()[0]["cost"]
gold_cost = gold.agg(F.sum("reward_cost_eur").alias("cost")).collect()[0]["cost"]

verification = {
    "raw_event_rows": raw_event_rows,
    "distinct_event_id": distinct_event_id,
    "reward_paid_raw_rows": reward_raw_rows,
    "distinct_reward_event_id": distinct_reward_id,
    "raw_reward_cost_eur": float(raw_cost) if raw_cost is not None else None,
    "deduped_reward_cost_eur": float(deduped_cost) if deduped_cost is not None else None,
    "duplicate_inflation_eur": float(raw_cost - deduped_cost)
    if raw_cost is not None and deduped_cost is not None
    else None,
    "gold_reward_cost_eur": float(gold_cost) if gold_cost is not None else None,
    "silver_event_rows": silver_events.count(),
}
display(verification)

expected = {
    "raw_event_rows": 435_907,
    "distinct_event_id": 423_186,
    "reward_paid_raw_rows": 10_171,
    "distinct_reward_event_id": 9_860,
    "raw_reward_cost_eur": 27_368.66,
    "deduped_reward_cost_eur": 26_547.41,
    "duplicate_inflation_eur": 821.25,
}

for key, exp in expected.items():
    got = verification[key]
    ok = abs(got - exp) < 0.02 if isinstance(exp, float) else got == exp
    print(f"{'OK' if ok else 'MISMATCH'} {key}: got={got} expected={exp}")

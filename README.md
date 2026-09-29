# Databricks Rewards Pipeline

Medallion-style Databricks pipeline for a rewarded-offer dataset. It lands CSV sources into Unity Catalog, builds trustworthy Silver tables, and publishes daily Gold metrics by country and platform.

## Architecture

```text
CSV landing files
      ↓
Bronze Delta        PySpark — raw source values preserved
      ↓
Silver Delta        PySpark — typing, normalization, event dedupe, quality flags
      ↓
Gold daily metrics  SQL — installs and event aggregates by day × country × platform
      ↓
Verification        quality checks and reconciliation totals
```

Gold grain: `metric_date × country × platform`

Metrics include installs, unique users per event type, reward payouts, and reward cost in EUR.

Design choices for this dataset size:

- batch CSV reads (not Auto Loader / streaming)
- PySpark for Bronze and Silver
- SQL for Gold
- Jobs-style notebook orchestration (not DLT / Lakeflow Declarative Pipelines)
- no physical partitioning of small tables

The pipeline handles replayed events, late arrivals via a correction window, and idempotent reruns.

## Repository layout

```text
gold/sql/                 Gold business SQL
notebooks/                thin Databricks drivers
scripts/                  profiling utility
src/databricks_pipeline/  reusable pipeline code
tests/                    local Spark tests
```

Source CSVs are expected in Unity Catalog Volumes in Databricks (for example `workspace.rewards.landing`). Keep a local `data/` folder for offline use if needed — it is not tracked in git.

## Local tests

Python 3.11+ and Java 17:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

Tests run local Spark and execute the real Gold SQL against temporary views. A Databricks workspace is not required.

## Databricks setup

Default Unity Catalog targets:

```text
workspace.rewards_bronze.*
workspace.rewards_silver.*
workspace.rewards_gold.daily_metrics
```

Run notebooks in order:

```text
01_bronze → 02_silver → 03_gold → 04_verify
```

For an initial full build, run Silver and Gold with `full_refresh=true`. Normal Silver runs MERGE the current Bronze batch into Silver; Gold replaces its seven-day correction window.

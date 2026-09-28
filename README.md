# Databricks Rewards Pipeline

Interview-focused Databricks pipeline for a rewarded-offer dataset.

Architecture:

    CSV landing files
          ↓
    Bronze Delta        PySpark, raw source values
          ↓
    Silver Delta        PySpark, typing + safe normalization + dedupe + quality flags
          ↓
    Gold daily metrics  SQL, business-readable aggregates
          ↓
    Verification        PySpark quality checks + reconciliation

The repo deliberately avoids streaming, Auto Loader, DLT/Lakeflow Declarative Pipelines, and physical partitioning for a dataset this small. The interesting problems here are correctness: replayed events, late arrival, ambiguous records, join fan-out, and idempotent reruns.

## Repository layout

    data/                         exercise CSVs
    gold/sql/                     Gold business SQL
    notebooks/                    thin Databricks drivers
    scripts/                      profiling utility
    src/databricks_pipeline/      reusable pipeline code
    tests/                        local Spark tests
    REPORT.md                     profiling evidence
    SOLUTION.md                   decisions and trade-offs
    databricks_pipeline_specification.md

## Local tests

Use Python 3.11 and Java 17:

    python3.11 -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
    pytest -q

The tests run local Spark and execute the real Gold SQL against temporary views. No Databricks workspace is required.

## Databricks setup

Defaults target Free Edition-friendly Unity Catalog objects:

    workspace.rewards_bronze.*
    workspace.rewards_silver.*
    workspace.rewards_gold.daily_metrics

Run the notebooks in order:

    01_bronze → 02_silver → 03_gold → 04_verify

For the initial complete build, run Gold with full_refresh=true. Normal runs use a seven-day correction window.

See SOLUTION.md for the data-quality decisions, late-arrival strategy, failure modes, and interview talking points.

# Rewards Databricks Pipeline

Idempotent medallion pipeline for the rewarded-offer take-home.

## Layout

```text
pipeline/
├── data/                          # local CSVs for offline tests only
├── gold/
│   └── sql/
│       └── daily_metrics.sql      # Gold business metrics (SQL)
├── notebooks/
│   ├── 01_bronze.py
│   ├── 02_silver.py
│   ├── 03_gold.sql
│   └── 04_verify.py
├── src/databricks_pipeline/
│   ├── bronze/                    # batch CSV → Bronze Delta
│   ├── silver/                    # PySpark transforms
│   ├── gold/                      # SQL loader helpers
│   ├── utils/                     # shared I/O, dates, paths, templates
│   ├── quality/                   # reusable checks
│   ├── config.py
│   └── pipeline.py                # Bronze → Silver → Gold orchestration
├── tests/
├── pyproject.toml
├── REPORT.md
└── databricks_pipeline_specification.md
```

## Unity Catalog (this workspace)

| Layer | Tables |
|---|---|
| Landing CSVs | `/Volumes/workspace/rewards/landing/<source>/load_date=...` |
| Bronze | `workspace.rewards_bronze.*` |
| Silver | `workspace.rewards_silver.*` |
| Gold | `workspace.rewards_gold.daily_metrics` |

## Local tests

```bash
cd pipeline
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

See `SOLUTION.md` for architecture decisions and verification.

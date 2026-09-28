# Solution

## Architecture

    CSV files
       ↓  batch PySpark
    Bronze Delta
       ↓  PySpark
    Silver Delta
       ↓  SQL
    Gold daily metrics
       ↓
    quality checks / reconciliation

Bronze preserves what arrived. Silver performs only evidence-backed interpretation. Gold contains the requested business metrics at metric_date × country × platform.

Gold is SQL on purpose: the metric definitions are aggregation-heavy and easier for reviewers to inspect directly.

## How to run

1. Put the four CSVs in the configured landing directory.
2. Run notebooks/01_bronze.py.
3. Run notebooks/02_silver.py.
4. Run notebooks/03_gold.sql.
5. Run notebooks/04_verify.py.

Use full_refresh=true for the initial whole-dataset build. Normal runs use a seven-day correction window ending on process_date.

## Data-quality decisions

| Observation | Decision | Reason |
|---|---|---|
| 435,907 event rows but 423,186 distinct event_id values | Deduplicate in Silver; earliest ingest_ts wins | Duplicate groups differ only by ingestion time in profiling and otherwise look like replay |
| Country variants such as DE and de-space | UPPER(TRIM(country)) | Prevent false country groups |
| Organic installs have blank campaign IDs | Preserve as null | Missing campaign is consistent with organic acquisition |
| Some non-reward events reference unknown offers | Keep and flag | Event activity is still useful; unresolved dimension membership is not proof the event is invalid |
| All profiled reward events resolve to an offer | Require reward offer resolution before Gold | Missing payout would silently understate cost |
| Some events occur before install time | Keep and flag | Files do not establish whether this is clock skew, attribution timing, or invalid data |
| Funnel history is incomplete | Do not enforce the funnel | Missing predecessor events are not enough to reject later events |
| user_profile aggregates do not reconcile cleanly | Reconciliation only | Wrong grain for requested Gold metrics and semantics are unclear |

Before event enrichment, the Silver runner validates that install and offer keys are unique. It also validates that repeated event_id groups do not contain conflicting business fields. These checks prevent silent join fan-out or unsafe deduplication.

## Event time vs ingestion time

event_ts determines the business/reporting date.

ingest_ts tells us when the platform learned about the event.

Profiling found substantial late arrival, including a maximum observed delay of about 5.58 days. A job that finalizes only the previous calendar day at 00:15 would therefore miss late events while still reporting success.

For the exercise, normal runs recompute a seven-day window. This trades a small amount of repeated compute for simple, explainable correctness. At larger scale I would track an ingestion watermark, identify the distinct historical event_date values affected by new arrivals, and recompute only those dates.

## Idempotency

Gold is fully derived. The metric update set is created in SQL, then the Delta table replaces only the target date range using replaceWhere. Re-running the same process_date replaces the same logical scope instead of appending duplicates.

A full refresh overwrites the complete Gold table.

## Gold metric design

Installs and events are aggregated separately before the final full outer join. This prevents one install from being multiplied by a user's many event rows.

Reward cost uses decimal types rather than floating point.

## Verification targets

    raw event rows                 435,907
    distinct event_id              423,186
    raw reward_paid rows            10,171
    distinct reward event_id         9,860
    raw reward cost EUR          27,368.66
    deduped reward cost EUR      26,547.41
    duplicate inflation EUR         821.25

## Platform choices

Batch ingestion instead of Auto Loader: there are four bounded CSV inputs. Continuous discovery adds complexity without solving a requirement.

PySpark for Bronze and Silver: typing, window-based deduplication, joins, and quality flags are natural DataFrame operations and easy to unit test.

SQL for Gold: business metrics are clearer as SQL aggregations and easy to review.

Jobs/Workflows rather than DLT/Lakeflow Declarative Pipelines: the dependency graph is small and explicit. If the system evolved to many continuous sources and managed streaming tables, I would reconsider declarative pipelines.

No physical partitioning: about 436k event rows is small for Databricks. I would only introduce clustering or partitioning after observing query patterns, scan volume, and file layout.

## How it can fail silently

The important failure modes are event replay, join fan-out from a non-unique dimension, unresolved reward payouts, late events assigned to the wrong day, using ingestion date as business date, and appending Gold on rerun. The implementation either prevents these directly or exposes them through checks.

A future payout change is another concern: if offer payout is mutable, historical rewards must not be revalued with today's payout. That requires a business contract, a versioned offer dimension, or storing payout-at-event-time.

## Scale

If the same shape arrives continuously from many sources, the layer boundaries, Delta tables, event-time semantics, quality contracts, and Unity Catalog governance survive. I would replace static batch file reads and a fixed lookback with continuous ingestion where justified, metadata-driven source configuration, ingestion watermarks, and affected-date recomputation.

## AI usage

AI/Cursor was used for repository inspection, scaffolding repetitive PySpark, SQL review, and candidate tests. Suggestions were rejected when they did not fit the evidence, including unnecessary partitioning, Auto Loader for four bounded files, DLT merely for feature coverage, funnel-based row deletion, and treating user_profile as Gold truth.

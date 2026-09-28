# Solution

## Environment

I used Databricks Free Edition with serverless compute, Unity Catalog and notebooks.

The main Free Edition constraint that affected the design was catalog layout. I used the managed `workspace` catalog and separated layers by schema:

- `workspace.rewards_bronze`
- `workspace.rewards_silver`
- `workspace.rewards_gold`

In a production workspace I would normally use clearer environment/domain boundaries, for example separate dev/staging/prod catalogs or a dedicated rewards catalog, and run the pipeline under a service principal with centrally managed Unity Catalog permissions.

## Architecture

```text
CSV landing files
      ↓  batch PySpark
Bronze Delta
      ↓  PySpark + Delta MERGE
Silver Delta
      ↓  SQL
Gold daily metrics
      ↓
quality checks / reconciliation
```

Bronze preserves what arrived. Silver performs evidence-backed typing, normalization, replay handling and enrichment. Gold exposes the requested business grain:

`metric_date × country × platform`

with installs, unique users per event type, reward payouts and reward cost EUR.

Gold is SQL on purpose: the metric definitions are aggregation-heavy and easier to review directly than equivalent nested DataFrame expressions.

## How to run

1. Put the four source CSVs in the configured Unity Catalog Volume landing path.
2. Run `notebooks/01_bronze.py`.
3. Run `notebooks/02_silver.py`.
4. Run `notebooks/03_gold.sql`.
5. Run `notebooks/04_verify.py`.

For the initial build:

```text
Silver full_refresh = true
Gold   full_refresh = true
```

For normal runs:

```text
Silver full_refresh = false
Gold   full_refresh = false
```

The notebooks are intentionally thin runtime entry points. `dbutils.widgets` provide catalog/schema paths, load date, process date and refresh mode without hard-coding environment-specific values into transformation code. The reusable logic remains in `src/databricks_pipeline` so it can be tested locally.

## Layer boundaries

### Bronze

Bronze uses explicit all-string schemas and keeps the raw source shape, replayed events included. It adds ingestion metadata such as source file and ingestion time.

I keep Bronze minimally interpreted so source evidence is not lost during type conversion or cleaning.

### Silver

Silver converts types, normalizes values, validates assumptions, deduplicates replayed events, enriches events with install and offer dimensions, and records quality flags.

On a normal run Silver processes only the current Bronze landing batch and MERGEs it into accumulated Silver Delta tables:

- installs by `user_id`;
- offers by `offer_id`;
- events by `event_id`;
- user_profile by `user_id`.

This means a single-day load does not require a full Silver rebuild.

### Gold

Gold is fully derived SQL. Installs and events are aggregated separately before a full outer join so one install cannot be multiplied by a user's many event rows.

## Data-quality findings and decisions

| Finding | Decision | Reason |
|---|---|---|
| 435,907 event rows but 423,186 distinct `event_id` values | Deduplicate by `event_id`, keep earliest `ingest_ts` | Duplicate groups otherwise have the same business fields and look like replays |
| Repeated `event_id` could theoretically disagree on business fields | Fail before dedupe if they conflict | Do not silently choose between contradictory events |
| Country variants such as `DE` and `de ` | `UPPER(TRIM(country))` | Prevent false country groups |
| Organic installs have blank campaign IDs | Preserve as null | Missing campaign is consistent with organic acquisition |
| Some non-reward events reference unknown offers | Keep and flag | Activity can still be valid even if a dimension lookup fails |
| All profiled reward events resolve to an offer | Fail if a reward payout cannot resolve | Otherwise reward cost would be silently understated |
| Some events occur before matching install time | Keep and flag | Could be clock skew or attribution timing; source does not prove invalidity |
| Funnel history is incomplete / out of order | Do not enforce a strict funnel | Missing predecessor events are not enough to reject later events |
| `user_profile` does not reconcile cleanly with event history | Reconciliation only, not Gold truth | Wrong grain and unclear semantics for daily country/platform reporting |
| offer_id and user_id dimensions are unique in the source | Assert uniqueness before joins | Prevent silent join fan-out and duplicated money |

Installs and offers are treated as immutable reference data for this exercise. If the same key arrives later with changed business fields, the Silver incremental merge fails rather than rewriting history without an explicit business rule.

If offer payout were actually mutable in production, I would need effective-dated offer history (for example SCD Type 2) or payout-at-event-time stored on the fact.

## Re-runnability and incremental processing

The initial build can be a full refresh.

Normal Silver runs process the current Bronze batch and use Delta MERGE into accumulated history. Existing event IDs are not duplicated; if a replay is seen again across batches, the earlier `ingest_ts` remains the survivor.

Gold is recomputed only for its correction scope and uses Delta `replaceWhere`, so rerunning the same processing scope replaces the same logical rows rather than appending duplicates.

The cost of this approach is extra merge/shuffle work and maintaining stable business keys, but for this dataset it gives simple, explicit rerun semantics.

Bronze is still a bounded landing/staging table for the selected `load_date`. For a continuous production feed I would make Bronze append-only or use Auto Loader rather than overwrite a selected landing batch.

## Tests

The tests are designed to fail on incorrect logic rather than only proving a happy path exists.

Examples:

- repeated event ID must result in one Silver event;
- a duplicate reward must not double payout count or cost;
- multiple `app_open` events from one user must still produce one unique user;
- `DE` and `de ` must normalize to the same country;
- an unknown non-reward offer must survive Silver;
- one install plus many events must still count as one install in Gold;
- a late event must report on `event_ts`, not `ingest_ts`;
- a conflicting existing key in incremental Silver must fail.

Runtime quality checks additionally enforce uniqueness, non-null required keys/timestamps, reward resolvability, Gold key uniqueness and non-negative reward cost.

I rely on Delta/Unity Catalog for storage schema and access controls, but semantic invariants such as event identity and dimension uniqueness are still explicit tests/checks because the platform cannot infer those business rules.

## Verification

The end-to-end run is checked against profiling evidence:

```text
raw event rows                 435,907
distinct event_id              423,186
raw reward_paid rows            10,171
distinct reward event_id         9,860
raw reward cost EUR          27,368.66
deduped reward cost EUR      26,547.41
duplicate inflation EUR         821.25
```

The verification notebook independently recomputes these values from the persisted Bronze/Silver/Gold tables.

## Deeper question: the daily 00:15 job

A job that runs at 00:15 over only the previous calendar day is wrong because many events arrive after their business day.

`event_ts` answers: when did the event happen?

`ingest_ts` answers: when did the platform learn about it?

Profiling found:

- 119,307 events where ingest date differs from event date;
- maximum observed ingestion delay of about 5.58 days.

So a successful previous-day-only job can permanently undercount historical dates without raising an error.

For this exercise Gold recomputes a seven-day correction window, based on the observed delay distribution.

That is an exercise trade-off, not a guaranteed production SLA. In production I would:

1. persist the last successful ingestion watermark;
2. identify newly arrived events from `ingest_ts`;
3. derive the distinct affected `event_date` values;
4. recompute only those Gold dates;
5. monitor p50/p95/p99/max lateness and alert when arrivals exceed the supported SLA.

## Deeper question: platform choices

### Batch ingestion vs Auto Loader

I chose batch CSV ingestion because there are four bounded files. Auto Loader would add discovery/state machinery without solving a requirement.

It stops being the right choice when files arrive continuously or from many sources. At that point I would likely move to append-only Bronze using Auto Loader/streaming ingestion.

### PySpark vs SQL

PySpark is used for Silver because the work is windowing, type conversion, enrichment and reusable data-quality logic.

SQL is used for Gold because the business metrics are grouping, conditional distinct counts and sums, and are easier to audit in SQL.

### Jobs/Workflows vs DLT/Lakeflow Declarative Pipelines

I kept the dependency graph explicit because the pipeline is small.

With many continuous tables, managed expectations and streaming dependencies, I would reconsider Lakeflow Declarative Pipelines.

### Partitioning / clustering

I intentionally did not physically partition these tables. Roughly 436k event rows is too small to justify likely small-file/metadata overhead.

At production scale I would inspect query profiles, scan bytes, file counts and pruning effectiveness before introducing clustering. If most queries filter by date, I would evaluate Liquid Clustering around `event_date` / `metric_date` rather than choosing a layout in advance.

### Unity Catalog governance

I would govern centrally:

- catalog/schema ownership;
- production table ownership;
- service-principal permissions;
- storage credentials and external locations;
- PII/data classifications and descriptions;
- lineage;
- who can write Bronze/Silver/Gold.

For example, analysts should usually read Gold, while production write access should belong to the pipeline identity rather than arbitrary notebook users.

## Deeper question: how it fails silently

The main dangerous cases are failures that still produce a successful Spark job:

1. replayed events inflate counts or reward cost;
2. duplicate dimension keys cause join fan-out;
3. late events make historical Gold incomplete;
4. grouping by `ingest_date` instead of `event_date` moves activity to the wrong business day;
5. unresolved reward offers understate financial cost;
6. blind append duplicates Gold on rerun;
7. mutable offer payouts can revalue historical reward cost incorrectly;
8. invalid timestamp casts can become null and remove rows from date-based calculations;
9. a fixed seven-day lookback can miss events that arrive later than the observed sample maximum.

The implementation prevents or surfaces the first several. The last case is why I would move to ingestion-watermark plus affected-date recomputation in production.

## Deeper question: scale to 50 continuous sources

What survives:

- Bronze/Silver/Gold responsibilities;
- Delta tables;
- stable business keys and idempotency rules;
- event-time vs ingestion-time semantics;
- Silver MERGE pattern;
- Gold business definitions;
- quality contracts;
- Unity Catalog governance.

What changes:

- static CSV reads;
- bounded Bronze overwrite;
- hard-coded source paths;
- manual notebook execution;
- fixed seven-day Gold lookback.

I would replace those with:

- metadata-driven source configuration;
- Auto Loader or other incremental ingestion where appropriate;
- append-only Bronze;
- persisted ingestion watermark;
- exact affected-date recomputation;
- scheduled Databricks Jobs/Workflows;
- centralized observability and alerts.

## AI usage

I used Cursor/AI for repository inspection, scaffolding repetitive PySpark, SQL review, test generation and code-review challenges.

I kept suggestions only when they matched the profiling evidence and requirements. I rejected or corrected suggestions including:

- unnecessary partitioning for a small dataset;
- Auto Loader for four bounded files;
- DLT/Lakeflow just to demonstrate a Databricks feature;
- strict funnel validation that would delete many legitimate-looking rows;
- using `user_profile` as Gold truth;
- silently accepting duplicate dimension keys;
- using a fixed late-arrival window as if it were a guaranteed production contract.

The most useful AI role was generating alternatives and edge cases; the final choices were checked against the profiling report and the actual pipeline outputs.

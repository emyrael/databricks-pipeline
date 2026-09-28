# Databricks Pipeline Specification

## 1. Objective

Build an idempotent Databricks pipeline that ingests the four provided CSV files into Unity Catalog and produces a Gold table at this grain:

```text
event_date × country × platform
```

with:

```text
installs
unique_app_open_users
unique_offer_view_users
unique_offer_start_users
unique_goal_reached_users
unique_reward_paid_users
reward_payouts
reward_cost_eur
```

The design should prioritize correctness, rerunnability, late-arriving data handling, explainable data-quality decisions, and simple Databricks-native patterns rather than scale for its own sake.

The source dataset contains:

- 40,000 installs
- 435,907 event rows
- 180 offers
- 40,000 user profiles

---

## 2. Architecture

Use a simple three-layer Medallion architecture:

```text
data/*.csv
      │
      ▼
┌──────────────────────────────┐
│ BRONZE                       │
│ Raw source representation    │
│ + ingestion metadata         │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ SILVER                       │
│ Types                        │
│ Normalization                │
│ Event deduplication          │
│ Quality flags                │
│ Business-safe transformations│
└──────────────┬───────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
 installs_daily   events_daily
        │             │
        └──────┬──────┘
               ▼
┌──────────────────────────────┐
│ GOLD                         │
│ daily_country_platform       │
└──────────────────────────────┘
```

### Layer responsibilities

- **Bronze:** What exactly arrived?
- **Silver:** What is safe and useful to interpret?
- **Gold:** What does the business want to consume?

Do not clean raw values in Bronze.

---

## 3. Unity Catalog Structure

Use:

```text
Catalog:
rewards_pipeline

Schemas:
rewards_pipeline.bronze
rewards_pipeline.silver
rewards_pipeline.gold
```

Tables:

```text
rewards_pipeline.bronze.installs
rewards_pipeline.bronze.events
rewards_pipeline.bronze.offers
rewards_pipeline.bronze.user_profile

rewards_pipeline.silver.installs
rewards_pipeline.silver.events
rewards_pipeline.silver.offers
rewards_pipeline.silver.user_profile

rewards_pipeline.gold.daily_metrics
```

Do not create separate catalogs for each layer.

---

## 4. Bronze Specification

### 4.1 `bronze.installs`

Source columns:

```text
user_id
install_ts
country
platform
media_source
device_model
campaign_id
```

Add ingestion metadata:

```text
_ingested_at
_source_file
```

Preserve the raw values. Do not normalize country, platform, campaign, or timestamps yet.

### 4.2 `bronze.events`

Preserve all source rows, including repeated `event_id`s.

Columns:

```text
user_id
event_ts
event_name
offer_id
event_id
ingest_ts

_ingested_at
_source_file
```

Do not deduplicate in Bronze.

### 4.3 `bronze.offers`

Preserve:

```text
offer_id
offer_category
payout_type
payout_eur
```

### 4.4 `bronze.user_profile`

Preserve:

```text
user_id
events_lifetime
last_seen_ts
revenue_30d_eur
is_payer
```

---

## 5. Silver Installs Specification

Target:

```text
exmox_pipeline.silver.installs
```

Grain:

```text
one row per user_id
```

Transformations:

```python
from pyspark.sql import functions as F

silver_installs = (
    bronze_installs
    .withColumn("install_ts", F.to_timestamp("install_ts"))
    .withColumn("country", F.upper(F.trim("country")))
    .withColumn("platform", F.lower(F.trim("platform")))
    .withColumn("media_source", F.lower(F.trim("media_source")))
    .withColumn(
        "campaign_id",
        F.when(F.trim("campaign_id") == "", F.lit(None))
         .otherwise(F.trim("campaign_id"))
    )
    .withColumn("install_date", F.to_date("install_ts"))
)
```

### Decisions

- Normalize country with `UPPER(TRIM(country))`.
- Normalize platform and media source to lowercase.
- Convert blank `campaign_id` to null.
- Do not reject organic rows with missing campaign IDs.

---

## 6. Silver Events Specification

Target:

```text
exmox_pipeline.silver.events
```

Grain:

```text
one logical event per event_id
```

### 6.1 Type timestamps

```python
event_ts = timestamp
ingest_ts = timestamp
```

Do not apply timezone conversion because the source timestamps contain no timezone offsets. Document that limitation explicitly.

### 6.2 Deduplicate `event_id`

Observed source behavior:

```text
435,907 rows
423,186 distinct event_id
12,721 repeated rows
```

Within duplicate groups, only `ingest_ts` changes.

Exercise assumption:

```text
event_id = logical event identity
```

Keep the earliest ingestion.

```python
from pyspark.sql import functions as F
from pyspark.sql.window import Window

dedupe_window = (
    Window
    .partitionBy("event_id")
    .orderBy(F.col("ingest_ts").asc())
)

silver_events = (
    bronze_events
    .withColumn("event_ts", F.to_timestamp("event_ts"))
    .withColumn("ingest_ts", F.to_timestamp("ingest_ts"))
    .withColumn("_rn", F.row_number().over(dedupe_window))
    .filter(F.col("_rn") == 1)
    .drop("_rn")
)
```

SQL equivalent:

```sql
WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY event_id
            ORDER BY ingest_ts ASC
        ) AS rn
    FROM exmox_pipeline.bronze.events
)

SELECT * EXCEPT (rn)
FROM ranked
WHERE rn = 1;
```

Document this as an exercise assumption, not a guaranteed upstream contract.

---

## 7. Event Quality Metadata

Add:

```text
event_date
ingest_date
ingest_delay_seconds
ingest_delay_days
cross_day_arrival
event_before_install
offer_resolved
```

Example:

```python
events = (
    silver_events
    .withColumn("event_date", F.to_date("event_ts"))
    .withColumn("ingest_date", F.to_date("ingest_ts"))
    .withColumn(
        "ingest_delay_seconds",
        F.unix_timestamp("ingest_ts") - F.unix_timestamp("event_ts")
    )
    .withColumn(
        "ingest_delay_days",
        F.col("ingest_delay_seconds") / F.lit(86400.0)
    )
    .withColumn(
        "cross_day_arrival",
        F.col("event_date") != F.col("ingest_date")
    )
)
```

Do not use quality flags as automatic row-rejection rules unless explicitly justified.

---

## 8. Events-Before-Install Rule

Join Silver events to Silver installs to derive quality metadata and dimensions.

```python
events_enriched = (
    silver_events.alias("e")
    .join(
        silver_installs.select(
            "user_id",
            "install_ts",
            "country",
            "platform"
        ).alias("i"),
        "user_id",
        "left"
    )
    .withColumn(
        "event_before_install",
        F.col("event_ts") < F.col("install_ts")
    )
)
```

Decision:

```text
retain row
flag anomaly
include in event metrics
document uncertainty
```

Do not automatically drop pre-install events.

---

## 9. Unknown-Offer Rule

Some events reference offer IDs not present in `offers.csv`, but all observed `reward_paid` offer IDs resolve successfully.

### For event-user metrics

Keep unknown-offer rows. For example, an `offer_view` on an unresolved offer still contributes to unique offer-view users.

### For reward cost

Only use reward rows whose payout resolves.

Add:

```text
offer_resolved BOOLEAN
```

Do not reject unknown-offer events by default.

---

## 10. Do Not Enforce the Funnel

Do not require this sequence:

```text
offer_view
→ offer_start
→ goal_reached
→ reward_paid
```

for a row to survive.

Keep events even where predecessor events are missing. Optional diagnostic flags may be added, but they must not drive Gold exclusion without an explicit business rule.

---

## 11. Silver Offers Specification

Target:

```text
exmox_pipeline.silver.offers
```

Grain:

```text
one row per offer_id
```

Transform:

```python
silver_offers = (
    bronze_offers
    .withColumn(
        "payout_eur",
        F.col("payout_eur").cast("decimal(10,2)")
    )
)
```

Use decimal, not double, for monetary values.

No source rows need to be filtered based on current profiling.

---

## 12. Silver User Profile Specification

Target schema:

```text
user_id             STRING
events_lifetime     BIGINT
last_seen_ts        TIMESTAMP
revenue_30d_eur     DECIMAL(10,2)
is_payer            BOOLEAN
```

Do not use `user_profile` to build Gold.

Use it only for:

```text
reconciliation
data-quality reporting
future investigation
```

Reason:

- wrong grain for daily metrics
- no date/country/platform
- aggregate semantics are not fully trustworthy from profiling alone

---

## 13. Gold Architecture

Do not join raw install facts to all event facts before aggregation.

Bad pattern:

```text
installs
    ↓
join events
    ↓
GROUP BY day, country, platform
```

because one install can multiply into many event rows.

Correct pattern:

```text
silver.installs
      ↓
aggregate
      ↓
installs_daily
                    \
                     \
                      → JOIN → gold.daily_metrics
                     /
silver.events      /
      ↓
aggregate
      ↓
events_daily
```

---

## 14. Install Daily Aggregate

Grain:

```text
metric_date
country
platform
```

```python
installs_daily = (
    silver_installs
    .groupBy(
        F.col("install_date").alias("metric_date"),
        "country",
        "platform"
    )
    .agg(
        F.count("*").alias("installs")
    )
)
```

Because Silver installs has one row per user, `count(*)` is valid.

---

## 15. Event Daily Aggregate

Start from deduplicated Silver events enriched with:

```text
country
platform
payout_eur
```

```python
events_daily = (
    events_enriched
    .groupBy(
        F.col("event_date").alias("metric_date"),
        "country",
        "platform"
    )
    .agg(
        F.countDistinct(
            F.when(F.col("event_name") == "app_open", F.col("user_id"))
        ).alias("unique_app_open_users"),

        F.countDistinct(
            F.when(F.col("event_name") == "offer_view", F.col("user_id"))
        ).alias("unique_offer_view_users"),

        F.countDistinct(
            F.when(F.col("event_name") == "offer_start", F.col("user_id"))
        ).alias("unique_offer_start_users"),

        F.countDistinct(
            F.when(F.col("event_name") == "goal_reached", F.col("user_id"))
        ).alias("unique_goal_reached_users"),

        F.countDistinct(
            F.when(F.col("event_name") == "reward_paid", F.col("user_id"))
        ).alias("unique_reward_paid_users"),

        F.sum(
            F.when(F.col("event_name") == "reward_paid", F.lit(1))
             .otherwise(F.lit(0))
        ).alias("reward_payouts"),

        F.sum(
            F.when(
                F.col("event_name") == "reward_paid",
                F.col("payout_eur")
            ).otherwise(F.lit(0).cast("decimal(18,2)"))
        ).alias("reward_cost_eur")
    )
)
```

Expected whole-dataset verification values under the chosen dedupe rule:

```text
reward_paid raw rows: 10,171
distinct reward event_id: 9,860
deduped reward cost: €26,547.41
```

---

## 16. Build Final Gold with a Full Outer Join

Use:

```python
gold = (
    installs_daily.alias("i")
    .join(
        events_daily.alias("e"),
        ["metric_date", "country", "platform"],
        "full_outer"
    )
    .fillna({
        "installs": 0,
        "unique_app_open_users": 0,
        "unique_offer_view_users": 0,
        "unique_offer_start_users": 0,
        "unique_goal_reached_users": 0,
        "unique_reward_paid_users": 0,
        "reward_payouts": 0,
    })
    .withColumn(
        "reward_cost_eur",
        F.coalesce(
            F.col("reward_cost_eur"),
            F.lit(0).cast("decimal(18,2)")
        )
    )
    .withColumn("_updated_at", F.current_timestamp())
)
```

Use a full outer join so date-country-platform combinations with only installs or only events are not lost.

---

## 17. Gold Schema

```text
metric_date                  DATE
country                      STRING
platform                     STRING

installs                     BIGINT

unique_app_open_users        BIGINT
unique_offer_view_users      BIGINT
unique_offer_start_users     BIGINT
unique_goal_reached_users    BIGINT
unique_reward_paid_users     BIGINT

reward_payouts               BIGINT
reward_cost_eur              DECIMAL(18,2)

_updated_at                  TIMESTAMP
```

Logical key:

```text
metric_date
country
platform
```

---

## 18. Incremental Processing Specification

There are two relevant clocks:

```text
event_ts
→ business/reporting date

ingest_ts
→ arrival/change detection
```

Observed source behavior includes significant late arrival, so a job that processes only the previous calendar day is not sufficient.

---

## 19. Exercise Implementation: 7-Day Correction Window

Use a parameter:

```text
process_date
```

and derive:

```text
start_date = process_date - 6 days
end_date   = process_date
```

Recompute all seven event dates.

Example:

```python
from datetime import date, timedelta

process_date = date.fromisoformat(
    dbutils.widgets.get("process_date")
)

start_date = process_date - timedelta(days=6)
```

Filter:

```python
events_scope = silver_events.filter(
    (F.col("event_date") >= F.lit(start_date))
    & (F.col("event_date") <= F.lit(process_date))
)
```

Rationale:

- observed max delay is 5.58 days
- seven days gives a small safety margin
- the dataset is small, so repeated compute is cheap
- behavior is simple and easy to explain

Trade-off:

```text
pro:
simple
idempotent
easy to verify

cost:
recomputes some already-correct dates
assumes late arrival stays within the correction window
```

---

## 20. Production Evolution

At larger scale, replace the fixed lookback with ingestion-driven affected-date recomputation.

Concept:

```text
ingestion watermark
        ↓
identify newly arrived events
        ↓
extract DISTINCT event_date
        ↓
recompute affected dates only
```

Example:

```python
new_events = silver_events.filter(
    F.col("ingest_ts") > last_successful_ingest_ts
)

affected_dates = (
    new_events
    .select("event_date")
    .distinct()
)
```

Then recompute only those historical business dates.

---

## 21. Idempotent Gold Writes

Do not append Gold blindly.

Preferred exercise approach:

```text
recompute full affected dates
replace those dates
```

Example:

```python
(
    gold_updates.write
    .format("delta")
    .mode("overwrite")
    .option(
        "replaceWhere",
        """
        metric_date >= '2026-05-21'
        AND metric_date <= '2026-05-27'
        """
    )
    .saveAsTable(
        "exmox_pipeline.gold.daily_metrics"
    )
)
```

Alternative:

```sql
MERGE INTO exmox_pipeline.gold.daily_metrics AS target
USING updates AS source

ON  target.metric_date = source.metric_date
AND target.country = source.country
AND target.platform = source.platform

WHEN MATCHED THEN
    UPDATE SET *

WHEN NOT MATCHED THEN
    INSERT *;
```

For this exercise, targeted date replacement is preferred because Gold is fully derived and each affected date can be recomputed completely.

---

## 22. Idempotency Invariant

Required behavior:

```text
State after run X
=
State after running X again
```

The second run must not:

- change row count
- duplicate rows
- change metrics
- change monetary totals

except for technical metadata such as `_updated_at` if that field is excluded from equality checks.

---

## 23. Required Tests

### Test 1 — duplicate event replay

Input:

```text
same event_id twice
different ingest_ts
```

Expected:

```text
one Silver event
```

If `reward_paid`:

```text
one payout
one payout amount
```

### Test 2 — Gold counts unique users

Input:

```text
u1 app_open
u1 app_open
u1 app_open
```

Expected:

```text
unique_app_open_users = 1
```

This catches incorrect use of `COUNT(*)`.

### Test 3 — country canonicalization

Input:

```text
DE
de 
```

Expected:

```text
DE
DE
```

### Test 4 — unknown offer preserved

Input:

```text
event_name = offer_view
offer_id = of_missing
```

Expected:

```text
row survives Silver
offer_resolved = false
user still contributes to offer_view metric
```

### Test 5 — fact fan-out protection

Input:

```text
1 install
10 events
```

Expected:

```text
installs = 1
```

not 10.

### Test 6 — late arrival changes historical Gold

First run:

```text
May 1 Gold
```

Then add:

```text
event_ts  = May 1
ingest_ts = May 4
```

Rerun.

Expected:

```text
May 1 Gold changes
May 4 does not receive that event
```

### Test 7 — rerun idempotency

Run twice.

Expected:

```text
same row count
same logical keys
same metric values
same monetary totals
```

---

## 24. Runtime Quality Assertions

### Silver event uniqueness

```python
assert (
    silver_events
    .groupBy("event_id")
    .count()
    .filter("count > 1")
    .count()
    == 0
)
```

### Gold key uniqueness

```python
assert (
    gold
    .groupBy(
        "metric_date",
        "country",
        "platform"
    )
    .count()
    .filter("count > 1")
    .count()
    == 0
)
```

### Reward cost non-negative

```python
assert (
    gold
    .filter(F.col("reward_cost_eur") < 0)
    .count()
    == 0
)
```

Runtime assertions complement tests; they do not replace them.

---

## 25. Pipeline / Job Structure

Recommended code layout:

```text
src/
├── bronze.py
├── silver/
│   ├── installs.py
│   ├── events.py
│   ├── offers.py
│   └── user_profile.py
├── gold/
│   └── daily_metrics.py
├── quality/
│   └── checks.py
└── config.py

tests/
├── test_installs.py
├── test_events.py
├── test_gold.py
└── test_idempotency.py
```

Databricks workflow:

```text
Task 1
bronze_ingestion
       ↓
Task 2
silver_transforms
       ↓
Task 3
gold_daily_metrics
       ↓
Task 4
quality_checks
```

---

## 26. Ingestion Choice

For this exercise:

```python
spark.read.csv(...)
```

is sufficient.

Do not introduce Auto Loader simply to demonstrate platform knowledge.

Rationale:

- four bounded source files
- small dataset
- batch is simpler
- no continuous file-arrival requirement

Production evolution: use Auto Loader when files arrive continuously at scale.

---

## 27. Partitioning / Clustering Choice

Do not physically partition these exercise tables.

Rationale:

- ~436k event rows is small for Databricks
- partitioning could create many tiny files
- there is no measured performance issue requiring it

In production, evaluate clustering based on:

```text
actual query filters
scan volume
table size
file statistics
join patterns
```

Potential future candidate:

```text
CLUSTER BY metric_date, country
```

but only after measurement.

---

## 28. Unity Catalog Responsibilities

Centralize:

```text
schema ownership
table ownership
read/write permissions
production service principals
PII/data classification
table descriptions
lineage
storage locations
```

Suggested access model:

```text
analysts:
read Gold

engineers:
read Bronze/Silver
controlled write access

pipeline service principal:
write Bronze/Silver/Gold
```

Governance should not depend on each pipeline author manually reproducing access rules.

---

## 29. Expected Verification Numbers

Under the chosen `event_id` deduplication assumption:

```text
Raw event rows:
435,907

Distinct event_id:
423,186

Reward-paid raw rows:
10,171

Distinct reward event_id:
9,860

Reward cost raw:
€27,368.66

Reward cost after event-id dedupe:
€26,547.41

Duplicate-induced difference:
€821.25
```

These values should appear in `SOLUTION.md` as whole-dataset verification evidence.

---

## 30. Decision Log

| Observation | Pipeline decision | Reason |
|---|---|---|
| `event_id` repeated with only differing `ingest_ts` | Deduplicate in Silver, earliest ingestion wins | Prevent replayed logical events and monetary inflation |
| Country case/whitespace variants | `UPPER(TRIM(country))` | Prevent false country groups |
| Organic users have blank campaign IDs | Preserve as null | Appears semantically valid |
| Unknown offers on non-reward events | Preserve and flag | Event behavior remains useful |
| All reward events resolve to offers | Join payout for reward cost | Safe for current dataset |
| Events before install | Preserve and flag | Semantics uncertain |
| Incomplete event funnels | Do not enforce sequence | Source does not guarantee full history |
| `user_profile` disagrees with event-derived readings | Reconciliation only | Wrong grain and unclear semantics |
| Significant late arrival | Reprocess a correction window | Yesterday-only reporting is incomplete |
| Max observed delay 5.58 days | Seven-day exercise lookback | Evidence-based simple trade-off |
| Dataset is small | No physical partitioning | Avoid unnecessary optimization |

---

## 31. Interview-Ready Design Summary

> I profiled the data before deciding the pipeline semantics. Bronze preserves what arrived. Silver applies only transformations I can defend from the evidence: explicit typing, country normalization, and logical-event deduplication. Ambiguous conditions such as pre-install events and unresolved offers are retained and flagged rather than silently discarded. Gold aggregates installs and events separately before joining them, preventing fact fan-out. I use event time for business reporting and ingestion time for detecting late changes. Because the data shows a maximum observed ingestion delay of 5.58 days, the exercise implementation recomputes a seven-day correction window and replaces affected Gold dates idempotently. At larger scale, I would evolve this to ingestion-watermark-driven affected-date recomputation.

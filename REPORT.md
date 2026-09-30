# Dataset Profiling Report

Produced by `python scripts/profile_data.py`. Source CSVs were read as text (`keep_default_na=False`) and were not modified. Timestamp differences subtract the civil times as written. No timezone offset is present to convert.

## Executive Summary

Four files: installs 40,000 rows, events 435,907 rows, offers 180 rows, user_profile 40,000 rows.

- `event_id` has 12,721 extra rows. Inside those groups the columns that vary are: ingest_ts.
- 119,307 of 435,907 events (27.37%) have an ingest calendar date different from the event date. Max delay is 5.58 days. Rows with ingest_ts before event_ts: 0.
- Country has 8 normalized values that are stored as more than one raw spelling.
- 13,672 event rows have an offer_id that is not in offers.csv. The breakdown by event_name is in the referential section. reward_paid is called out there separately.
- 3,094 event rows have event_ts earlier than the matching install_ts.
- Summing offer payout on every resolved reward_paid row gives 27368.66 EUR. Keeping one row per event_id (earliest ingest_ts) gives 26547.41 EUR. The second figure is a sensitivity, not a decision that event_id should be deduped.
- user_profile.events_lifetime equals the raw event-row count for 23,785 of 37,695 matched users. The profile has no day, country, or platform column.

## installs.csv

### Overview

- File: `installs.csv`
- Rows: 40,000
- Columns: 7
- Size: 2,319,062 bytes
- Storage: every field was read as text.

| Column | Inferred type |
| --- | --- |
| user_id | string |
| install_ts | timestamp (no offset in the text) |
| country | string |
| platform | string |
| media_source | string |
| device_model | string |
| campaign_id | string |

### Schema

Column names and inferred types are in the overview table. Inference used a 99% parse threshold and did not change the file.

### Uniqueness and Duplicates

Stated grain: one row per user. `user_id` distinct values: 40,000 out of 40,000 rows. Extra rows beyond the first user_id: 0. Fully identical duplicate rows: 0.

The stated grain holds: user_id is unique and non-blank.

No other single column is close to unique (country, platform, media_source, device_model, campaign_id, and install_ts all repeat). install_ts is a time, not a key.

### Missing Values

Blank means empty or whitespace-only. Null tokens are the literal strings nan, null, none, n/a, and na. Nothing was coerced to a real null.

| Column | Blank | Blank % | Null tokens | Distinct |
| --- | --- | --- | --- | --- |
| user_id | 0 | 0.00% | 0 | 40,000 |
| install_ts | 0 | 0.00% | 0 | 39,843 |
| country | 0 | 0.00% | 0 | 16 |
| platform | 0 | 0.00% | 0 | 2 |
| media_source | 0 | 0.00% | 0 | 5 |
| device_model | 0 | 0.00% | 0 | 6 |
| campaign_id | 9,887 | 24.72% | 0 | 41 |

### Categorical Distributions

**country**

All 16 values.

| Value | Count | Share of rows |
| --- | --- | --- |
| 'DE' | 8497 | 21.24% |
| 'US' | 6892 | 17.23% |
| 'BR' | 5370 | 13.43% |
| 'IN' | 4653 | 11.63% |
| 'FR' | 3890 | 9.72% |
| 'GB' | 3849 | 9.62% |
| 'TR' | 3054 | 7.63% |
| 'PL' | 2205 | 5.51% |
| 'de ' | 325 | 0.81% |
| 'us ' | 283 | 0.71% |
| 'br ' | 233 | 0.58% |
| 'in ' | 203 | 0.51% |
| 'fr ' | 174 | 0.43% |
| 'gb ' | 148 | 0.37% |
| 'tr ' | 131 | 0.33% |
| 'pl ' | 93 | 0.23% |

Leading whitespace on non-blank values: 0. Trailing whitespace: 1,590.
Values that collapse together after trim and lower-casing: 'br' appears as 'BR' and 'br ', 'de' appears as 'DE' and 'de ', 'fr' appears as 'FR' and 'fr ', 'gb' appears as 'GB' and 'gb ', 'in' appears as 'IN' and 'in ', 'pl' appears as 'PL' and 'pl ', 'tr' appears as 'TR' and 'tr ', 'us' appears as 'US' and 'us '.

**platform**

All 2 values.

| Value | Count | Share of rows |
| --- | --- | --- |
| 'android' | 23081 | 57.70% |
| 'ios' | 16919 | 42.30% |

Leading whitespace on non-blank values: 0. Trailing whitespace: 0.
No trim/case variants: each normalized value comes from one raw spelling.

**media_source**

All 5 values.

| Value | Count | Share of rows |
| --- | --- | --- |
| 'meta' | 12094 | 30.23% |
| 'organic' | 9887 | 24.72% |
| 'tiktok' | 7970 | 19.93% |
| 'unity' | 6057 | 15.14% |
| 'applovin' | 3992 | 9.98% |

Leading whitespace on non-blank values: 0. Trailing whitespace: 0.
No trim/case variants: each normalized value comes from one raw spelling.

**device_model**

All 6 values.

| Value | Count | Share of rows |
| --- | --- | --- |
| 'pixel7' | 6742 | 16.86% |
| 'redmi9' | 6702 | 16.75% |
| 's22' | 6653 | 16.63% |
| 'iphone15' | 6650 | 16.62% |
| 'a51' | 6638 | 16.59% |
| 'iphone13' | 6615 | 16.54% |

Leading whitespace on non-blank values: 0. Trailing whitespace: 0.
No trim/case variants: each normalized value comes from one raw spelling.

**campaign_id**

41 distinct values. Top 10.

| Value | Count | Share of rows |
| --- | --- | --- |
| '' | 9887 | 24.72% |
| 'cmp_112' | 834 | 2.08% |
| 'cmp_131' | 817 | 2.04% |
| 'cmp_138' | 797 | 1.99% |
| 'cmp_109' | 790 | 1.98% |
| 'cmp_103' | 784 | 1.96% |
| 'cmp_130' | 777 | 1.94% |
| 'cmp_126' | 776 | 1.94% |
| 'cmp_128' | 776 | 1.94% |
| 'cmp_108' | 773 | 1.93% |

Leading whitespace on non-blank values: 0. Trailing whitespace: 0.
No trim/case variants: each normalized value comes from one raw spelling.

campaign_id blank vs organic:

|  | organic | not organic |
| --- | --- | --- |
| campaign blank | 9,887 | 0 |
| campaign present | 0 | 30,113 |

### Date Analysis

install_ts parsed 40,000, failed 0, blank 0. Range 2026-04-01 00:00:28 to 2026-05-30 23:56:06. Timezone offsets found: 0. Rows sharing a timestamp with another row: 313.

Distinct install dates: 60.

| install date | installs |
| --- | --- |
| 2026-04-01 | 634 |
| 2026-04-02 | 718 |
| 2026-04-03 | 631 |
| 2026-04-04 | 656 |
| 2026-04-05 | 678 |
| 2026-04-06 | 681 |
| 2026-04-07 | 689 |
| 2026-04-08 | 717 |
| 2026-04-09 | 689 |
| 2026-04-10 | 704 |
| 2026-04-11 | 603 |
| 2026-04-12 | 635 |
| 2026-04-13 | 676 |
| 2026-04-14 | 672 |
| 2026-04-15 | 679 |
| 2026-04-16 | 666 |
| 2026-04-17 | 664 |
| 2026-04-18 | 682 |
| 2026-04-19 | 702 |
| 2026-04-20 | 656 |
| 2026-04-21 | 707 |
| 2026-04-22 | 685 |
| 2026-04-23 | 655 |
| 2026-04-24 | 665 |
| 2026-04-25 | 678 |
| 2026-04-26 | 650 |
| 2026-04-27 | 651 |
| 2026-04-28 | 672 |
| 2026-04-29 | 661 |
| 2026-04-30 | 621 |
| 2026-05-01 | 684 |
| 2026-05-02 | 645 |
| 2026-05-03 | 648 |
| 2026-05-04 | 685 |
| 2026-05-05 | 643 |
| 2026-05-06 | 659 |
| 2026-05-07 | 697 |
| 2026-05-08 | 704 |
| 2026-05-09 | 639 |
| 2026-05-10 | 655 |
| 2026-05-11 | 671 |
| 2026-05-12 | 644 |
| 2026-05-13 | 656 |
| 2026-05-14 | 672 |
| 2026-05-15 | 675 |
| 2026-05-16 | 614 |
| 2026-05-17 | 677 |
| 2026-05-18 | 693 |
| 2026-05-19 | 599 |
| 2026-05-20 | 703 |
| 2026-05-21 | 672 |
| 2026-05-22 | 654 |
| 2026-05-23 | 671 |
| 2026-05-24 | 699 |
| 2026-05-25 | 646 |
| 2026-05-26 | 691 |
| 2026-05-27 | 665 |
| 2026-05-28 | 682 |
| 2026-05-29 | 616 |
| 2026-05-30 | 664 |

### Data Quality Observations

**Confirmed issue**

- None identified from the checks in this report.

**Suspicious observation**

- country contains spellings that differ only by case and trailing space. They may be the same country codes, but the file stores them as different strings.

**Likely-valid edge case**

- user_id is unique and non-blank, so the stated one-row-per-user grain holds in this file.
- All 9,887 blank campaign_id values are media_source 'organic', and every organic row has a blank campaign_id.

**Unknown / requires business clarification**

- Timestamps have no zone. It is not known whether install_ts, event_ts, and ingest_ts share one clock.
- Is a blank campaign_id the expected encoding of organic, or a missing attribute?
- 2,856 users have at least one event_ts before install_ts. Whether that is clock skew, a late install record, or a real pre-install event is not determined by the files.

## events.csv

### Overview

- File: `events.csv`
- Rows: 435,907
- Columns: 6
- Size: 34,577,948 bytes
- Storage: every field was read as text.

| Column | Inferred type |
| --- | --- |
| user_id | string |
| event_ts | timestamp (no offset in the text) |
| event_name | string |
| offer_id | string |
| event_id | string |
| ingest_ts | timestamp (no offset in the text) |

### Schema

Types in the overview are inferred. event_name is the event type column in this file (there is no column named event_type).

### Uniqueness and Duplicates

`event_id` distinct: 423,186 of 435,907 rows. Extra rows: 12,721. Duplicate groups: 12,721. Fully identical rows: 0. Extra rows on (user_id, event_ts, event_name, offer_id): 12,721.

Columns that vary inside a duplicated event_id: ingest_ts (max distinct 2).

The stated grain is one row per event. Under event_id, that grain does not hold. No other column is a plausible key (user_id, offer_id, and both timestamps all repeat heavily).

Two duplicated ids, all of their rows:

| user_id | event_ts | event_name | offer_id | event_id | ingest_ts |
| --- | --- | --- | --- | --- | --- |
| 'u_000000' | '2026-05-14 19:39:21' | 'offer_view' | 'of_0003' | 'ev_00000006' | '2026-05-14 21:44:03' |
| 'u_000000' | '2026-05-14 19:39:21' | 'offer_view' | 'of_0003' | 'ev_00000006' | '2026-05-14 21:45:33' |
| 'u_000011' | '2026-04-14 05:36:57' | 'offer_view' | 'of_0138' | 'ev_00000123' | '2026-04-14 09:58:50' |
| 'u_000011' | '2026-04-14 05:36:57' | 'offer_view' | 'of_0138' | 'ev_00000123' | '2026-04-14 10:00:20' |

### Missing Values

Blank means empty or whitespace-only. Null tokens are the literal strings nan, null, none, n/a, and na. Nothing was coerced to a real null.

| Column | Blank | Blank % | Null tokens | Distinct |
| --- | --- | --- | --- | --- |
| user_id | 0 | 0.00% | 0 | 37,695 |
| event_ts | 0 | 0.00% | 0 | 405,018 |
| event_name | 0 | 0.00% | 0 | 5 |
| offer_id | 0 | 0.00% | 0 | 186 |
| event_id | 0 | 0.00% | 0 | 423,186 |
| ingest_ts | 0 | 0.00% | 0 | 416,724 |

### Event Type Distribution

| event_name | Rows | Share |
| --- | --- | --- |
| 'app_open' | 212,201 | 48.68% |
| 'offer_view' | 119,541 | 27.42% |
| 'offer_start' | 68,425 | 15.70% |
| 'goal_reached' | 25,569 | 5.87% |
| 'reward_paid' | 10,171 | 2.33% |

### Event Time Analysis

event_ts parsed 435,907, failed 0, blank 0. Range 2026-03-29 02:28:38 to 2026-05-27 23:36:51. Timezone offsets: 0. Rows sharing an event_ts value: 60,199.

### Ingest Time Analysis

ingest_ts parsed 435,907, failed 0, blank 0. Range 2026-04-01 02:42:12 to 2026-05-27 23:59:55. Timezone offsets: 0. Rows sharing an ingest_ts value: 37,792.

Per-day ingest counts and the event-date comparison are in Late Arrival Analysis.

### Event vs Ingest Delay

Delay is `ingest_ts - event_ts` in seconds. Both columns are civil times with no zone, so this is not a timezone-corrected duration.

| Metric | Value |
| --- | --- |
| Rows with both timestamps parsed | 435,907 |
| ingest_ts < event_ts | 0 |
| Min delay (seconds) | 0 |
| Max delay (seconds) | 481913 |
| Max delay (days) | 5.58 |
| Mean (seconds) | 25945.9 |
| Median (seconds) | 17899 |
| P90 (seconds) | 52362 |
| P95 (seconds) | 67821 |
| P99 (seconds) | 259842 |
| > 1 minute | 435,662 (99.94%) |
| > 5 minutes | 434,133 (99.59%) |
| > 15 minutes | 428,591 (98.32%) |
| > 1 hour | 395,079 (90.63%) |
| > 6 hours | 183,934 (42.20%) |
| > 24 hours | 10,923 (2.51%) |
| > 48 hours | 4,475 (1.03%) |
| Calendar date of ingest_ts differs from event_ts | 119,307 (27.37%) |

### Event Lifecycle Checks

These counts use the earliest event_ts of each event_name. Repeated event_id rows with the same event_ts do not create a second step. A same-timestamp pair has no sub-second order in this file, so it is not treated as 'prior'.

Grain: (user_id, offer_id). This does not look across offers.

**offer_start vs earlier offer_view** (66,033 pairs with at least one offer_start)

| Situation | Pairs | Share |
| --- | --- | --- |
| Earlier step exists at a strictly earlier timestamp | 637 | 0.96% |
| No earlier step on this grain | 64,743 | 98.05% |
| Earlier step exists only at a later timestamp | 653 | 0.99% |
| Earliest timestamps are equal (order not determined) | 0 | 0.00% |
| No strictly-earlier step (first two problem rows combined) | 65,396 | 99.04% |

Examples of missing or later steps, sorted by key:

| user_id | offer_id | Later step timestamp | Earlier step timestamp |
| --- | --- | --- | --- |
| u_000000 | of_0004 | 2026-05-21 16:39:04 |  |
| u_000000 | of_0074 | 2026-05-14 07:19:57 |  |
| u_000000 | of_0103 | 2026-05-14 06:03:44 |  |

**goal_reached vs earlier offer_start** (24,778 pairs with at least one goal_reached)

| Situation | Pairs | Share |
| --- | --- | --- |
| Earlier step exists at a strictly earlier timestamp | 134 | 0.54% |
| No earlier step on this grain | 24,496 | 98.86% |
| Earlier step exists only at a later timestamp | 148 | 0.60% |
| Earliest timestamps are equal (order not determined) | 0 | 0.00% |
| No strictly-earlier step (first two problem rows combined) | 24,644 | 99.46% |

Examples of missing or later steps, sorted by key:

| user_id | offer_id | Later step timestamp | Earlier step timestamp |
| --- | --- | --- | --- |
| u_000002 | of_0025 | 2026-05-17 23:07:41 |  |
| u_000002 | of_0132 | 2026-05-17 01:49:27 |  |
| u_000003 | of_0005 | 2026-04-21 11:53:32 |  |

**reward_paid vs earlier goal_reached** (9,860 pairs with at least one reward_paid)

| Situation | Pairs | Share |
| --- | --- | --- |
| Earlier step exists at a strictly earlier timestamp | 32 | 0.32% |
| No earlier step on this grain | 9,812 | 99.51% |
| Earlier step exists only at a later timestamp | 16 | 0.16% |
| Earliest timestamps are equal (order not determined) | 0 | 0.00% |
| No strictly-earlier step (first two problem rows combined) | 9,828 | 99.68% |

Examples of missing or later steps, sorted by key:

| user_id | offer_id | Later step timestamp | Earlier step timestamp |
| --- | --- | --- | --- |
| u_000000 | of_0172 | 2026-05-13 04:25:07 |  |
| u_000001 | of_0066 | 2026-04-15 02:03:08 |  |
| u_000011 | of_0032 | 2026-04-13 23:18:03 |  |

The same three checks ignoring offer_id (user grain only):

**offer_start vs earlier offer_view, any offer** (29,649 users with at least one offer_start)

| Situation | Pairs | Share |
| --- | --- | --- |
| Earlier step exists at a strictly earlier timestamp | 16,356 | 55.17% |
| No earlier step on this grain | 2,132 | 7.19% |
| Earlier step exists only at a later timestamp | 11,161 | 37.64% |
| Earliest timestamps are equal (order not determined) | 0 | 0.00% |
| No strictly-earlier step (first two problem rows combined) | 13,293 | 44.83% |

Examples of missing or later steps, sorted by key:

| user_id | offer_id | Later step timestamp | Earlier step timestamp |
| --- | --- | --- | --- |
| u_000002 |  | 2026-05-16 22:37:38 | 2026-05-17 15:29:59 |
| u_000006 |  | 2026-04-25 13:58:15 | 2026-04-28 16:54:50 |
| u_000012 |  | 2026-05-03 19:52:58 | 2026-05-03 21:51:35 |

**goal_reached vs earlier offer_start, any offer** (17,430 users with at least one goal_reached)

| Situation | Pairs | Share |
| --- | --- | --- |
| Earlier step exists at a strictly earlier timestamp | 8,470 | 48.59% |
| No earlier step on this grain | 3,078 | 17.66% |
| Earlier step exists only at a later timestamp | 5,882 | 33.75% |
| Earliest timestamps are equal (order not determined) | 0 | 0.00% |
| No strictly-earlier step (first two problem rows combined) | 8,960 | 51.41% |

Examples of missing or later steps, sorted by key:

| user_id | offer_id | Later step timestamp | Earlier step timestamp |
| --- | --- | --- | --- |
| u_000003 |  | 2026-04-21 11:53:32 | 2026-04-22 00:41:51 |
| u_000004 |  | 2026-05-05 13:04:49 | 2026-05-06 16:12:40 |
| u_000005 |  | 2026-04-11 02:19:28 | 2026-04-11 21:28:46 |

**reward_paid vs earlier goal_reached, any offer** (9,860 users with at least one reward_paid)

| Situation | Pairs | Share |
| --- | --- | --- |
| Earlier step exists at a strictly earlier timestamp | 4,124 | 41.83% |
| No earlier step on this grain | 4,198 | 42.58% |
| Earlier step exists only at a later timestamp | 1,538 | 15.60% |
| Earliest timestamps are equal (order not determined) | 0 | 0.00% |
| No strictly-earlier step (first two problem rows combined) | 5,736 | 58.17% |

Examples of missing or later steps, sorted by key:

| user_id | offer_id | Later step timestamp | Earlier step timestamp |
| --- | --- | --- | --- |
| u_000000 |  | 2026-05-13 04:25:07 |  |
| u_000001 |  | 2026-04-15 02:03:08 |  |
| u_000011 |  | 2026-04-13 23:18:03 |  |

Multiple events of the same name on one (user_id, offer_id). `replay_only` means several rows but a single event_id.

| event_name | Pairs with >1 row | Pairs with >1 event_id | Replay-only pairs |
| --- | --- | --- | --- |
| app_open | 9,509 | 3,522 | 5,987 |
| offer_view | 4,517 | 1,148 | 3,369 |
| offer_start | 2,370 | 355 | 2,015 |
| goal_reached | 787 | 50 | 737 |
| reward_paid | 311 | 0 | 311 |

### User Activity

Populations are install users, so users with no event rows are included as zero. Install users with no event row: 2,305 (set difference against events.user_id: 2,305).

| Population | Min | P50 | P90 | P95 | P99 | Max | Mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Event rows | 0 | 10 | 20 | 23 | 28 | 43 | 10.90 |

| Population | Min | P50 | P90 | P95 | P99 | Max | Mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Distinct event_id | 0 | 10 | 19 | 22 | 27 | 42 | 10.58 |

| Population | Min | P50 | P90 | P95 | P99 | Max | Mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Distinct offer_id on events | 0 | 10 | 18 | 21 | 26 | 39 | 10.21 |

| Population | Min | P50 | P90 | P95 | P99 | Max | Mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Distinct reward_paid event_id | 0 | 0 | 1 | 1 | 1 | 1 | 0.25 |

Reward cost per install user, EUR, counting one resolved row per reward event_id and zero when the user has none. This is a description of the join, not a billing rule.

| Min | P50 | P90 | P95 | P99 | Max | Mean |
| --- | --- | --- | --- | --- | --- | --- |
| 0.00 | 0.00 | 2.59 | 3.90 | 6.29 | 9.99 | 0.66 |

Users above the P99 of event rows (28): 393. That cut is descriptive. It is not evidence those users are invalid.

Top 10 install users by event rows. Cost uses one row per resolved reward event_id.

| user_id | Event rows | Distinct event_id | Distinct offer_id | Distinct reward ids | Cost EUR |
| --- | --- | --- | --- | --- | --- |
| u_012936 | 43 | 42 | 39 | 1 | 2.67 |
| u_012060 | 42 | 41 | 37 | 1 | 3.44 |
| u_032163 | 40 | 39 | 35 | 1 | 3.47 |
| u_004053 | 39 | 39 | 34 | 1 | 0.45 |
| u_006392 | 39 | 38 | 35 | 1 | 4.82 |
| u_010331 | 39 | 38 | 35 | 1 | 3.80 |
| u_023323 | 39 | 37 | 32 | 1 | 2.34 |
| u_030475 | 39 | 37 | 35 | 0 | 0.00 |
| u_002070 | 38 | 35 | 34 | 1 | 1.43 |
| u_016529 | 38 | 34 | 28 | 1 | 1.62 |

### Data Quality Observations

**Confirmed issue**

- `event_id` is not unique: 12,721 ids account for 12,721 extra rows (max copies of one id: 2). If event_id is the event identity, the stated one-row-per-event grain does not hold.

**Suspicious observation**

- Within duplicate event_id groups, the only column that takes more than one value is ingest_ts. That is what a replay of the same event would look like. It is still an inference.
- There are no fully identical duplicate rows. The extra event_id rows are not byte-identical copies.

**Likely-valid edge case**

- None identified from the checks in this report.

**Unknown / requires business clarification**

- The duplicate rows are not enough, by themselves, to decide which ingest_ts is the one a metric should keep.
- Lifecycle gaps below are counts, not a judgment that the sequence is illegal.

## offers.csv

### Overview

- File: `offers.csv`
- Rows: 180
- Columns: 4
- Size: 4,296 bytes
- Storage: every field was read as text.

| Column | Inferred type |
| --- | --- |
| offer_id | string |
| offer_category | string |
| payout_type | string |
| payout_eur | decimal |

### Schema

payout_eur is decimal text. Other columns are strings. No timestamp column is present.

### Uniqueness and Duplicates

`offer_id` distinct 180 of 180. Extra rows: 0. Fully identical rows: 0.

The stated one-row-per-offer grain holds.

### Missing Values

Blank means empty or whitespace-only. Null tokens are the literal strings nan, null, none, n/a, and na. Nothing was coerced to a real null.

| Column | Blank | Blank % | Null tokens | Distinct |
| --- | --- | --- | --- | --- |
| offer_id | 0 | 0.00% | 0 | 180 |
| offer_category | 0 | 0.00% | 0 | 5 |
| payout_type | 0 | 0.00% | 0 | 3 |
| payout_eur | 0 | 0.00% | 0 | 150 |

### Payout Analysis

| Metric | Value |
| --- | --- |
| Parsed count | 180 |
| Blank | 0 |
| Unparsed | 0 |
| Min | 0.4500 |
| Max | 9.9900 |
| Mean | 2.7000 |
| Median | 2.2850 |
| Sample std (ddof=1) | 1.7199 |
| P25 | 1.4850 |
| P75 | 3.5475 |
| Zeros | 0 |
| Negatives | 0 |
| Distinct | 150 |

Fractional digits in the original payout text:

| Decimal places | Offers |
| --- | --- |
| 1 | 23 |
| 2 | 157 |

Zeros: 0. Negatives: 0. Unparsed: 0.

### Category / Payout Type Distribution

**offer_category**

All 5 values.

| Value | Count | Share of rows |
| --- | --- | --- |
| 'casino' | 39 | 21.67% |
| 'rpg' | 38 | 21.11% |
| 'puzzle' | 37 | 20.56% |
| 'casual' | 33 | 18.33% |
| 'strategy' | 33 | 18.33% |

Leading whitespace on non-blank values: 0. Trailing whitespace: 0.
No trim/case variants: each normalized value comes from one raw spelling.

| Value | Offers | Min EUR | Median | Max | Mean |
| --- | --- | --- | --- | --- | --- |
| 'casino' | 39 | 0.53 | 2.08 | 6.29 | 2.42 |
| 'casual' | 33 | 0.47 | 2.12 | 6.57 | 2.42 |
| 'puzzle' | 37 | 0.49 | 2.64 | 5.89 | 2.84 |
| 'rpg' | 38 | 0.57 | 2.13 | 9.99 | 2.64 |
| 'strategy' | 33 | 0.45 | 2.32 | 9.07 | 3.22 |

**payout_type**

All 3 values.

| Value | Count | Share of rows |
| --- | --- | --- |
| 'cpe' | 84 | 46.67% |
| 'cpi' | 64 | 35.56% |
| 'cpa' | 32 | 17.78% |

Leading whitespace on non-blank values: 0. Trailing whitespace: 0.
No trim/case variants: each normalized value comes from one raw spelling.

| Value | Offers | Min EUR | Median | Max | Mean |
| --- | --- | --- | --- | --- | --- |
| 'cpa' | 32 | 0.70 | 2.66 | 6.57 | 2.93 |
| 'cpe' | 84 | 0.47 | 2.09 | 7.12 | 2.44 |
| 'cpi' | 64 | 0.45 | 2.34 | 9.99 | 2.93 |

Distinct offer_id values referenced by at least one event: 180 of 180. Offer ids never present on an event row: 0. Offer ids with no resolved reward_paid row: 0.

### Data Quality Observations

**Confirmed issue**

- None identified from the checks in this report.

**Suspicious observation**

- None identified from the checks in this report.

**Likely-valid edge case**

- offer_id is unique and non-blank, and every payout_eur parses as a non-negative number. The stated one-row-per-offer grain holds in this file.

**Unknown / requires business clarification**

- It is not known whether payout_eur is a current attribute that can change later. This file is a single extract, so history cannot be observed.
- Whether every event_name should resolve to one of these offer ids is not stated by the files. See the referential breakdown.

## user_profile.csv

### Overview

- File: `user_profile.csv`
- Rows: 40,000
- Columns: 5
- Size: 1,688,457 bytes
- Storage: every field was read as text.

| Column | Inferred type |
| --- | --- |
| user_id | string |
| events_lifetime | integer |
| last_seen_ts | timestamp (no offset in the text) |
| revenue_30d_eur | decimal |
| is_payer | string |

### Schema

events_lifetime parses as an integer, revenue_30d_eur as a decimal, last_seen_ts as a timestamp, is_payer as a string.

### Uniqueness and Duplicates

`user_id` distinct 40,000 of 40,000. Extra rows: 0. Fully identical rows: 0.

### Missing Values

Blank means empty or whitespace-only. Null tokens are the literal strings nan, null, none, n/a, and na. Nothing was coerced to a real null.

| Column | Blank | Blank % | Null tokens | Distinct |
| --- | --- | --- | --- | --- |
| user_id | 0 | 0.00% | 0 | 40,000 |
| events_lifetime | 0 | 0.00% | 0 | 41 |
| last_seen_ts | 0 | 0.00% | 0 | 39,844 |
| revenue_30d_eur | 0 | 0.00% | 0 | 1,098 |
| is_payer | 0 | 0.00% | 0 | 2 |

### Lifetime Metric Analysis

**events_lifetime**

| Metric | Value |
| --- | --- |
| Parsed count | 40,000 |
| Blank | 0 |
| Unparsed | 0 |
| Min | 1.0000 |
| Max | 42.0000 |
| Mean | 11.7214 |
| Median | 11.0000 |
| Sample std (ddof=1) | 5.8048 |
| P25 | 7.0000 |
| P75 | 15.0000 |
| Zeros | 0 |
| Negatives | 0 |
| Distinct | 41 |

**revenue_30d_eur**

| Metric | Value |
| --- | --- |
| Parsed count | 40,000 |
| Blank | 0 |
| Unparsed | 0 |
| Min | 0.0000 |
| Max | 24.9800 |
| Mean | 1.1588 |
| Median | 0.4500 |
| Sample std (ddof=1) | 1.7856 |
| P25 | 0.2200 |
| P75 | 1.1200 |
| Zeros | 30 |
| Negatives | 0 |
| Distinct | 1,098 |

Decimal places in revenue_30d_eur text:

| Decimal places | Rows |
| --- | --- |
| 1 | 4,072 |
| 2 | 35,928 |

**is_payer**

All 2 values.

| Value | Count | Share of rows |
| --- | --- | --- |
| 'False' | 28590 | 71.47% |
| 'True' | 11410 | 28.52% |

Leading whitespace on non-blank values: 0. Trailing whitespace: 0.
No trim/case variants: each normalized value comes from one raw spelling.

**last_seen_ts**

Parsed 40,000, failed 0, blank 0. Range 2026-04-02 18:05:10 to 2026-06-26 19:22:58. Timezone offsets: 0.

### Reconciliation With Events

Profile users: 40,000. Of those, 37,695 appear in events.csv and 2,305 have no event row. A user with no event row is not counted as equal in the table below, because there is no derived count to compare. Zeros were not filled in.

events_lifetime versus four counts derived from events.csv. These are candidate readings of the column name, not known definitions. The denominator is all 40,000 profile users.

| Reading | Users equal |
| --- | --- |
| Raw event rows | 23,785 / 40,000 (23,785 / 37,695 among users with events) |
| Distinct event_id | 32,715 / 40,000 (32,715 / 37,695 among users with events) |
| Rows excluding app_open | 586 / 40,000 (586 / 37,695 among users with events) |
| Distinct event_id excluding app_open | 445 / 40,000 (445 / 37,695 among users with events) |

Largest absolute gaps versus raw event rows (profile minus rows):

| user_id | events_lifetime | Event rows | Difference |
| --- | --- | --- | --- |
| u_017075 | 38 | 1 | 37 |
| u_003113 | 34 | 1 | 33 |
| u_018322 | 33 | 1 | 32 |
| u_006978 | 28 | 1 | 27 |
| u_010967 | 29 | 4 | 25 |

last_seen_ts versus three candidate clocks. Median is last_seen minus that clock, in seconds. A negative median means last_seen is earlier than the candidate.

| Candidate | Users equal | Median delta seconds |
| --- | --- | --- |
| max event_ts | 32,730 | 0 |
| max ingest_ts | 0 | -15573 |
| max app_open event_ts | 15,209 | 82664 |

revenue_30d_eur compared with the sum of resolved reward payouts, one row per reward event_id, over all time: exact match for 41 of 40,000 users. That reading treats a 30-day revenue column as lifetime reward cost. The name does not say that. The match rate only shows whether the reading is plausible.

A 30-day window was not applied. Choosing the window end (last_seen_ts, max event_ts, or a fixed date) would be a business rule, and none is in the files.

is_payer against revenue_30d_eur > 0 and against having any reward_paid row:

| is_payer | Users | revenue > 0 | revenue = 0 or blank | Has reward_paid | No reward_paid |
| --- | --- | --- | --- | --- | --- |
| 'False' | 28,590 | 28,560 | 30 | 0 | 28,590 |
| 'True' | 11,410 | 11,410 | 0 | 9,860 | 1,550 |

Does user_profile look consistent with the event log? Only in part. events_lifetime matches the raw row count for 23,785 users and matches distinct event_id for 32,715 users, so it is not a straight count of this file. last_seen_ts equals max event_ts for 32,730 users (median delta 0 seconds) and equals max ingest_ts for 0 users (median delta -15573 seconds). revenue_30d_eur is not the lifetime reward sum under the reading above.

Could it be the source of truth for a daily gold table of installs, users by event, and reward cost by day, country, and platform? No. The file has one row per user and no day, country, or platform. Those grains live on installs and events. Consistency problems above are additional reasons not to treat the lifetime numbers as a substitute for the event log, even at user grain.

### Data Quality Observations

**Confirmed issue**

- None identified from the checks in this report.

**Suspicious observation**

- events_lifetime equals the raw event-row count for 23,785 of 40,000 users. It is not a straight count of events.csv rows.

**Likely-valid edge case**

- user_id is unique and non-blank. The stated one-row-per-user grain holds in this file.

**Unknown / requires business clarification**

- events_lifetime, last_seen_ts, revenue_30d_eur, and is_payer are names, not definitions. Match rates below test specific readings. A low match rate rejects that reading. It does not by itself say which reading is correct.
- is_payer is the strings 'True' and 'False'. The file does not say whether that means the user paid, or that a reward was paid to the user.

## Cross-File Referential Integrity

installs.user_id vs events.user_id

| Check | Result |
| --- | --- |
| Event rows whose user_id is not in installs | 0 |
| Distinct event user_ids missing from installs | 0 |
| Install rows whose user_id has no event | 2,305 |
| Duplicate user_id in installs | 0 |
| Duplicate user_id in user_profile | 0 |
| user_profile ids missing from installs | 0 |
| Install ids missing from user_profile | 0 |

Event rows per user (users who appear in events): min 1, median 11, p99 29, max 43. Top users are listed in the events user-activity section. High counts are not labeled invalid.

events.offer_id vs offers.offer_id. Blank offer_id is counted separately and is not called invalid.

| event_name | Rows | Blank offer_id | offer_id not in offers.csv | Share not in offers |
| --- | --- | --- | --- | --- |
| 'app_open' | 212,201 | 0 | 6,785 | 3.20% |
| 'goal_reached' | 25,569 | 0 | 767 | 3.00% |
| 'offer_start' | 68,425 | 0 | 2,255 | 3.30% |
| 'offer_view' | 119,541 | 0 | 3,865 | 3.23% |
| 'reward_paid' | 10,171 | 0 | 0 | 0.00% |

Offer ids in offers.csv never used on an event: 0. offers.csv offer_id runs from 'of_0000' to 'of_0179'. Distinct event offer_ids missing from that file: 6, from 'of_0180' to 'of_0185'. 6 of those sort after 'of_0179'.

Example unknown offer ids (up to three per event_name):

| event_name | offer_id |
| --- | --- |
| 'app_open' | 'of_0180' |
| 'app_open' | 'of_0181' |
| 'app_open' | 'of_0182' |
| 'goal_reached' | 'of_0180' |
| 'goal_reached' | 'of_0181' |
| 'goal_reached' | 'of_0182' |
| 'offer_start' | 'of_0180' |
| 'offer_start' | 'of_0181' |
| 'offer_start' | 'of_0182' |
| 'offer_view' | 'of_0180' |
| 'offer_view' | 'of_0181' |
| 'offer_view' | 'of_0182' |

event_ts compared with install_ts on the matching user. Positive seconds means the event is before the install. Users with no install cannot appear here.

| event_name | Rows before install | Share of that event | Users | Distinct event_id |
| --- | --- | --- | --- | --- |
| 'app_open' | 1,527 | 0.72% | 1,441 | 1,480 |
| 'goal_reached' | 198 | 0.77% | 188 | 188 |
| 'offer_start' | 480 | 0.70% | 467 | 467 |
| 'offer_view' | 849 | 0.71% | 817 | 828 |
| 'reward_paid' | 40 | 0.39% | 40 | 40 |

Event rows before the install: 3,094. Users with at least one: 2,856.

Largest gaps (install_ts minus event_ts):

| user_id | event_id | event_name | event_ts | install_ts | Seconds before install |
| --- | --- | --- | --- | --- | --- |
| u_029625 | ev_00346820 | offer_view | 2026-05-11 21:27:38 | 2026-05-14 21:26:20 | 259122 |
| u_026716 | ev_00313185 | goal_reached | 2026-05-05 01:23:24 | 2026-05-08 01:20:57 | 259053 |
| u_008681 | ev_00102453 | app_open | 2026-04-15 18:11:24 | 2026-04-18 18:08:51 | 259047 |
| u_017442 | ev_00205966 | reward_paid | 2026-05-01 18:25:49 | 2026-05-04 18:22:42 | 259013 |
| u_004371 | ev_00051862 | offer_view | 2026-04-07 21:24:00 | 2026-04-10 21:20:10 | 258970 |

## Reward Cost Analysis

reward_paid rows: 10,171. Distinct users: 9,860. Distinct event_id: 9,860. Distinct offer_id on those rows: 180.

Rows with no usable non-negative payout in offers.csv: 0. Reward rows whose user_id did not match an install: 0.

Cost if every resolved reward row is summed: 27368.66 EUR on 10,171 rows. Cost if each resolved event_id is kept once, at its earliest ingest_ts: 26547.41 EUR on 9,860 rows. The difference is 821.25 EUR. That difference is the inflation from counting duplicate event_id rows. It is not a recommendation to drop them.

Groupings below use the one-row-per-event_id sensitivity so the duplicate ids are not summed twice. The date is the calendar date of event_ts, which is a description of the column, not a decision that it is the reporting day. Country and platform come from the install.

By event date: see the daily table in Late Arrival Analysis (reward cost column).

**By country**

| country | Rows | Distinct event_id | Cost EUR |
| --- | --- | --- | --- |
| 'BR' | 1,202 | 1,202 | 3323.56 |
| 'DE' | 2,344 | 2,344 | 6391.82 |
| 'FR' | 828 | 828 | 2214.31 |
| 'GB' | 1,060 | 1,060 | 2913.93 |
| 'IN' | 1,033 | 1,033 | 2766.13 |
| 'PL' | 456 | 456 | 1147.67 |
| 'TR' | 644 | 644 | 1711.77 |
| 'US' | 1,891 | 1,891 | 5001.95 |
| 'br ' | 50 | 50 | 128.16 |
| 'de ' | 92 | 92 | 214.89 |
| 'fr ' | 33 | 33 | 100.24 |
| 'gb ' | 37 | 37 | 89.01 |
| 'in ' | 47 | 47 | 114.48 |
| 'pl ' | 24 | 24 | 64.65 |
| 'tr ' | 37 | 37 | 126.69 |
| 'us ' | 82 | 82 | 238.15 |

**By platform**

| platform | Rows | Distinct event_id | Cost EUR |
| --- | --- | --- | --- |
| 'android' | 5,262 | 5,262 | 14230.47 |
| 'ios' | 4,598 | 4,598 | 12316.94 |

**By offer_id** (180 offers that have a resolved reward)

| offer_id | Rows | Distinct event_id | Cost EUR |
| --- | --- | --- | --- |
| 'of_0000' | 53 | 53 | 284.08 |
| 'of_0001' | 40 | 40 | 160.00 |
| 'of_0002' | 53 | 53 | 87.98 |
| 'of_0003' | 62 | 62 | 35.34 |
| 'of_0004' | 52 | 52 | 87.88 |
| 'of_0005' | 67 | 67 | 70.35 |
| 'of_0006' | 59 | 59 | 63.13 |
| 'of_0007' | 51 | 51 | 134.13 |
| 'of_0008' | 49 | 49 | 88.20 |
| 'of_0009' | 47 | 47 | 194.11 |
| 'of_0010' | 51 | 51 | 279.48 |
| 'of_0011' | 53 | 53 | 140.45 |
| 'of_0012' | 56 | 56 | 118.72 |
| 'of_0013' | 57 | 57 | 229.14 |
| 'of_0014' | 52 | 52 | 218.92 |
| 'of_0015' | 48 | 48 | 213.60 |
| 'of_0016' | 44 | 44 | 111.76 |
| 'of_0017' | 65 | 65 | 120.25 |
| 'of_0018' | 49 | 49 | 153.37 |
| 'of_0019' | 65 | 65 | 159.25 |
| 'of_0020' | 43 | 43 | 56.33 |
| 'of_0021' | 54 | 54 | 57.24 |
| 'of_0022' | 60 | 60 | 129.00 |
| 'of_0023' | 53 | 53 | 102.82 |
| 'of_0024' | 48 | 48 | 104.64 |
| 'of_0025' | 62 | 62 | 106.64 |
| 'of_0026' | 46 | 46 | 24.38 |
| 'of_0027' | 53 | 53 | 166.42 |
| 'of_0028' | 65 | 65 | 61.10 |
| 'of_0029' | 57 | 57 | 110.58 |
| 'of_0030' | 56 | 56 | 145.04 |
| 'of_0031' | 64 | 64 | 112.64 |
| 'of_0032' | 55 | 55 | 141.35 |
| 'of_0033' | 64 | 64 | 402.56 |
| 'of_0034' | 57 | 57 | 197.79 |
| 'of_0035' | 50 | 50 | 133.50 |
| 'of_0036' | 59 | 59 | 155.76 |
| 'of_0037' | 51 | 51 | 123.93 |
| 'of_0038' | 55 | 55 | 39.60 |
| 'of_0039' | 60 | 60 | 28.20 |
| 'of_0040' | 60 | 60 | 139.80 |
| 'of_0041' | 53 | 53 | 74.73 |
| 'of_0042' | 74 | 74 | 221.26 |
| 'of_0043' | 57 | 57 | 182.40 |
| 'of_0044' | 53 | 53 | 102.29 |
| 'of_0045' | 58 | 58 | 63.22 |
| 'of_0046' | 60 | 60 | 125.40 |
| 'of_0047' | 64 | 64 | 91.52 |
| 'of_0048' | 47 | 47 | 178.60 |
| 'of_0049' | 61 | 61 | 74.42 |
| 'of_0050' | 54 | 54 | 26.46 |
| 'of_0051' | 54 | 54 | 80.46 |
| 'of_0052' | 43 | 43 | 117.39 |
| 'of_0053' | 47 | 47 | 181.89 |
| 'of_0054' | 51 | 51 | 363.12 |
| 'of_0055' | 53 | 53 | 90.63 |
| 'of_0056' | 43 | 43 | 164.69 |
| 'of_0057' | 55 | 55 | 190.85 |
| 'of_0058' | 67 | 67 | 92.46 |
| 'of_0059' | 46 | 46 | 34.04 |
| 'of_0060' | 62 | 62 | 91.14 |
| 'of_0061' | 50 | 50 | 124.00 |
| 'of_0062' | 51 | 51 | 114.75 |
| 'of_0063' | 42 | 42 | 72.66 |
| 'of_0064' | 64 | 64 | 67.84 |
| 'of_0065' | 66 | 66 | 130.02 |
| 'of_0066' | 55 | 55 | 153.45 |
| 'of_0067' | 58 | 58 | 128.76 |
| 'of_0068' | 64 | 64 | 221.44 |
| 'of_0069' | 64 | 64 | 83.20 |
| 'of_0070' | 53 | 53 | 202.99 |
| 'of_0071' | 54 | 54 | 127.44 |
| 'of_0072' | 47 | 47 | 33.37 |
| 'of_0073' | 56 | 56 | 162.40 |
| 'of_0074' | 41 | 41 | 133.66 |
| 'of_0075' | 65 | 65 | 154.70 |
| 'of_0076' | 56 | 56 | 131.60 |
| 'of_0077' | 51 | 51 | 186.15 |
| 'of_0078' | 68 | 68 | 218.28 |
| 'of_0079' | 37 | 37 | 121.36 |
| 'of_0080' | 48 | 48 | 187.68 |
| 'of_0081' | 57 | 57 | 38.76 |
| 'of_0082' | 53 | 53 | 195.04 |
| 'of_0083' | 51 | 51 | 88.23 |
| 'of_0084' | 48 | 48 | 43.20 |
| 'of_0085' | 45 | 45 | 211.05 |
| 'of_0086' | 64 | 64 | 258.56 |
| 'of_0087' | 57 | 57 | 189.81 |
| 'of_0088' | 49 | 49 | 48.02 |
| 'of_0089' | 46 | 46 | 95.68 |
| 'of_0090' | 51 | 51 | 51.51 |
| 'of_0091' | 51 | 51 | 54.57 |
| 'of_0092' | 66 | 66 | 68.64 |
| 'of_0093' | 63 | 63 | 371.07 |
| 'of_0094' | 49 | 49 | 44.59 |
| 'of_0095' | 47 | 47 | 167.79 |
| 'of_0096' | 65 | 65 | 144.30 |
| 'of_0097' | 62 | 62 | 122.14 |
| 'of_0098' | 58 | 58 | 120.06 |
| 'of_0099' | 59 | 59 | 201.19 |
| 'of_0100' | 50 | 50 | 328.50 |
| 'of_0101' | 53 | 53 | 93.28 |
| 'of_0102' | 59 | 59 | 362.26 |
| 'of_0103' | 54 | 54 | 43.20 |
| 'of_0104' | 65 | 65 | 220.35 |
| 'of_0105' | 52 | 52 | 109.20 |
| 'of_0106' | 55 | 55 | 139.70 |
| 'of_0107' | 57 | 57 | 245.10 |
| 'of_0108' | 58 | 58 | 298.12 |
| 'of_0109' | 46 | 46 | 124.20 |
| 'of_0110' | 77 | 77 | 34.65 |
| 'of_0111' | 41 | 41 | 29.11 |
| 'of_0112' | 62 | 62 | 148.80 |
| 'of_0113' | 55 | 55 | 227.70 |
| 'of_0114' | 56 | 56 | 255.36 |
| 'of_0115' | 65 | 65 | 346.45 |
| 'of_0116' | 55 | 55 | 100.10 |
| 'of_0117' | 57 | 57 | 150.48 |
| 'of_0118' | 53 | 53 | 356.16 |
| 'of_0119' | 49 | 49 | 171.50 |
| 'of_0120' | 59 | 59 | 41.30 |
| 'of_0121' | 57 | 57 | 516.99 |
| 'of_0122' | 51 | 51 | 56.10 |
| 'of_0123' | 48 | 48 | 92.16 |
| 'of_0124' | 56 | 56 | 145.04 |
| 'of_0125' | 53 | 53 | 99.11 |
| 'of_0126' | 52 | 52 | 63.44 |
| 'of_0127' | 46 | 46 | 113.16 |
| 'of_0128' | 58 | 58 | 579.42 |
| 'of_0129' | 56 | 56 | 185.92 |
| 'of_0130' | 42 | 42 | 163.80 |
| 'of_0131' | 50 | 50 | 88.50 |
| 'of_0132' | 67 | 67 | 376.54 |
| 'of_0133' | 59 | 59 | 68.44 |
| 'of_0134' | 54 | 54 | 55.62 |
| 'of_0135' | 57 | 57 | 267.33 |
| 'of_0136' | 55 | 55 | 165.00 |
| 'of_0137' | 52 | 52 | 41.60 |
| 'of_0138' | 42 | 42 | 251.16 |
| 'of_0139' | 58 | 58 | 32.48 |
| 'of_0140' | 64 | 64 | 308.48 |
| 'of_0141' | 58 | 58 | 76.56 |
| 'of_0142' | 51 | 51 | 68.85 |
| 'of_0143' | 51 | 51 | 77.01 |
| 'of_0144' | 45 | 45 | 171.00 |
| 'of_0145' | 54 | 54 | 57.24 |
| 'of_0146' | 46 | 46 | 68.54 |
| 'of_0147' | 54 | 54 | 109.08 |
| 'of_0148' | 66 | 66 | 107.58 |
| 'of_0149' | 41 | 41 | 66.42 |
| 'of_0150' | 62 | 62 | 106.02 |
| 'of_0151' | 55 | 55 | 76.45 |
| 'of_0152' | 50 | 50 | 253.00 |
| 'of_0153' | 42 | 42 | 116.34 |
| 'of_0154' | 55 | 55 | 114.95 |
| 'of_0155' | 53 | 53 | 60.95 |
| 'of_0156' | 53 | 53 | 426.65 |
| 'of_0157' | 70 | 70 | 72.80 |
| 'of_0158' | 68 | 68 | 157.76 |
| 'of_0159' | 57 | 57 | 53.58 |
| 'of_0160' | 45 | 45 | 73.35 |
| 'of_0161' | 45 | 45 | 212.40 |
| 'of_0162' | 62 | 62 | 334.80 |
| 'of_0163' | 58 | 58 | 205.32 |
| 'of_0164' | 53 | 53 | 94.87 |
| 'of_0165' | 54 | 54 | 121.50 |
| 'of_0166' | 59 | 59 | 202.96 |
| 'of_0167' | 51 | 51 | 270.30 |
| 'of_0168' | 62 | 62 | 117.80 |
| 'of_0169' | 60 | 60 | 101.40 |
| 'of_0170' | 52 | 52 | 229.32 |
| 'of_0171' | 34 | 34 | 34.34 |
| 'of_0172' | 68 | 68 | 104.72 |
| 'of_0173' | 69 | 69 | 298.77 |
| 'of_0174' | 60 | 60 | 139.20 |
| 'of_0175' | 55 | 55 | 128.70 |
| 'of_0176' | 63 | 63 | 442.26 |
| 'of_0177' | 53 | 53 | 91.16 |
| 'of_0178' | 47 | 47 | 84.60 |
| 'of_0179' | 46 | 46 | 216.66 |

Install match gaps in the reward join: 0 rows with no country after the join.

## Late Arrival Analysis

Delay is `ingest_ts - event_ts` in seconds. Both columns are civil times with no zone, so this is not a timezone-corrected duration.

| Metric | Value |
| --- | --- |
| Rows with both timestamps parsed | 435,907 |
| ingest_ts < event_ts | 0 |
| Min delay (seconds) | 0 |
| Max delay (seconds) | 481913 |
| Max delay (days) | 5.58 |
| Mean (seconds) | 25945.9 |
| Median (seconds) | 17899 |
| P90 (seconds) | 52362 |
| P95 (seconds) | 67821 |
| P99 (seconds) | 259842 |
| > 1 minute | 435,662 (99.94%) |
| > 5 minutes | 434,133 (99.59%) |
| > 15 minutes | 428,591 (98.32%) |
| > 1 hour | 395,079 (90.63%) |
| > 6 hours | 183,934 (42.20%) |
| > 24 hours | 10,923 (2.51%) |
| > 48 hours | 4,475 (1.03%) |
| Calendar date of ingest_ts differs from event_ts | 119,307 (27.37%) |

By event_name:

| event_name | Rows | Cross calendar day | Share | Median delay s | P99 delay s |
| --- | --- | --- | --- | --- | --- |
| 'app_open' | 212,201 | 58,102 | 27.38% | 17926 | 260385 |
| 'goal_reached' | 25,569 | 7,052 | 27.58% | 18111 | 260049 |
| 'offer_start' | 68,425 | 18,585 | 27.16% | 17748 | 259546 |
| 'offer_view' | 119,541 | 32,787 | 27.43% | 17912 | 259484 |
| 'reward_paid' | 10,171 | 2,781 | 27.34% | 17688 | 126589 |

By event date. A row is late-arriving for this table when its ingest calendar date differs, and separately when the delay exceeds 24 hours. Those are not the same cut: a 23:50 event ingested at 00:10 the next day crosses a date inside one hour.

| event date | Events | Cross calendar day | Share | Delay > 24h |
| --- | --- | --- | --- | --- |
| 2026-03-29 | 14 | 14 | 100.00% | 14 |
| 2026-03-30 | 46 | 46 | 100.00% | 46 |
| 2026-03-31 | 40 | 40 | 100.00% | 40 |
| 2026-04-01 | 1,340 | 607 | 45.30% | 78 |
| 2026-04-02 | 3,598 | 1,121 | 31.16% | 110 |
| 2026-04-03 | 5,143 | 1,513 | 29.42% | 161 |
| 2026-04-04 | 5,905 | 1,661 | 28.13% | 192 |
| 2026-04-05 | 6,698 | 1,915 | 28.59% | 195 |
| 2026-04-06 | 7,067 | 1,959 | 27.72% | 174 |
| 2026-04-07 | 7,550 | 2,064 | 27.34% | 190 |
| 2026-04-08 | 7,946 | 2,175 | 27.37% | 182 |
| 2026-04-09 | 8,073 | 2,182 | 27.03% | 197 |
| 2026-04-10 | 8,304 | 2,253 | 27.13% | 212 |
| 2026-04-11 | 7,985 | 2,147 | 26.89% | 202 |
| 2026-04-12 | 7,898 | 2,189 | 27.72% | 209 |
| 2026-04-13 | 7,975 | 2,233 | 28.00% | 196 |
| 2026-04-14 | 7,947 | 2,227 | 28.02% | 236 |
| 2026-04-15 | 7,926 | 2,096 | 26.44% | 199 |
| 2026-04-16 | 8,218 | 2,265 | 27.56% | 216 |
| 2026-04-17 | 8,157 | 2,225 | 27.28% | 206 |
| 2026-04-18 | 8,224 | 2,239 | 27.23% | 202 |
| 2026-04-19 | 8,181 | 2,306 | 28.19% | 242 |
| 2026-04-20 | 8,299 | 2,278 | 27.45% | 197 |
| 2026-04-21 | 8,116 | 2,231 | 27.49% | 210 |
| 2026-04-22 | 8,043 | 2,200 | 27.35% | 204 |
| 2026-04-23 | 8,109 | 2,251 | 27.76% | 196 |
| 2026-04-24 | 8,221 | 2,235 | 27.19% | 222 |
| 2026-04-25 | 8,058 | 2,286 | 28.37% | 191 |
| 2026-04-26 | 8,037 | 2,224 | 27.67% | 197 |
| 2026-04-27 | 7,986 | 2,264 | 28.35% | 199 |
| 2026-04-28 | 7,937 | 2,187 | 27.55% | 193 |
| 2026-04-29 | 8,066 | 2,141 | 26.54% | 212 |
| 2026-04-30 | 7,879 | 2,099 | 26.64% | 204 |
| 2026-05-01 | 7,882 | 2,199 | 27.90% | 199 |
| 2026-05-02 | 7,925 | 2,235 | 28.20% | 225 |
| 2026-05-03 | 8,117 | 2,293 | 28.25% | 204 |
| 2026-05-04 | 7,995 | 2,218 | 27.74% | 178 |
| 2026-05-05 | 7,969 | 2,193 | 27.52% | 189 |
| 2026-05-06 | 7,920 | 2,155 | 27.21% | 208 |
| 2026-05-07 | 7,848 | 2,225 | 28.35% | 202 |
| 2026-05-08 | 8,110 | 2,324 | 28.66% | 191 |
| 2026-05-09 | 8,070 | 2,257 | 27.97% | 226 |
| 2026-05-10 | 8,052 | 2,239 | 27.81% | 177 |
| 2026-05-11 | 7,995 | 2,194 | 27.44% | 207 |
| 2026-05-12 | 8,078 | 2,241 | 27.74% | 201 |
| 2026-05-13 | 7,722 | 2,123 | 27.49% | 194 |
| 2026-05-14 | 7,957 | 2,219 | 27.89% | 204 |
| 2026-05-15 | 7,897 | 2,208 | 27.96% | 209 |
| 2026-05-16 | 7,857 | 2,125 | 27.05% | 194 |
| 2026-05-17 | 7,796 | 2,162 | 27.73% | 219 |
| 2026-05-18 | 8,036 | 2,190 | 27.25% | 185 |
| 2026-05-19 | 7,944 | 2,161 | 27.20% | 196 |
| 2026-05-20 | 7,995 | 2,235 | 27.95% | 202 |
| 2026-05-21 | 8,105 | 2,280 | 28.13% | 210 |
| 2026-05-22 | 8,047 | 2,232 | 27.74% | 183 |
| 2026-05-23 | 7,984 | 2,229 | 27.92% | 180 |
| 2026-05-24 | 8,146 | 2,275 | 27.93% | 200 |
| 2026-05-25 | 7,719 | 2,060 | 26.69% | 124 |
| 2026-05-26 | 7,982 | 2,162 | 27.09% | 92 |
| 2026-05-27 | 5,773 | 0 | 0.00% | 0 |

Largest absolute gaps between events dated on that day and events ingested on that day. A positive gap means more events happened that day than were ingested that day.

| Date | By event date | By ingest date | Event minus ingest |
| --- | --- | --- | --- |
| 2026-05-27 | 5,773 | 8,053 | -2,280 |
| 2026-04-01 | 1,340 | 742 | 598 |
| 2026-04-02 | 3,598 | 3,048 | 550 |
| 2026-04-03 | 5,143 | 4,724 | 419 |
| 2026-04-05 | 6,698 | 6,408 | 290 |
| 2026-05-25 | 7,719 | 7,937 | -218 |
| 2026-04-04 | 5,905 | 5,723 | 182 |
| 2026-04-16 | 8,218 | 8,067 | 151 |
| 2026-05-13 | 7,722 | 7,840 | -118 |
| 2026-05-08 | 8,110 | 7,999 | 111 |

Dates present as an event date and absent as an ingest date: 2026-03-29, 2026-03-30, 2026-03-31. Dates present as an ingest date and absent as an event date: none.

Most delayed events:

| event_id | user_id | event_name | event_ts | ingest_ts | Delay seconds | Delay days |
| --- | --- | --- | --- | --- | --- | --- |
| ev_00364826 | u_031127 | offer_view | 2026-05-18 02:41:12 | 2026-05-23 16:33:05 | 481913 | 5.58 |
| ev_00321604 | u_027435 | app_open | 2026-05-20 18:06:56 | 2026-05-25 15:42:27 | 423331 | 4.90 |
| ev_00216475 | u_018356 | app_open | 2026-05-12 07:43:47 | 2026-05-17 04:20:34 | 419807 | 4.86 |
| ev_00398517 | u_034000 | offer_view | 2026-05-04 12:37:26 | 2026-05-08 22:38:55 | 381689 | 4.42 |
| ev_00308706 | u_026322 | offer_view | 2026-04-02 22:05:25 | 2026-04-07 08:06:25 | 381660 | 4.42 |
| ev_00285376 | u_024311 | goal_reached | 2026-04-16 07:21:58 | 2026-04-20 17:21:56 | 381598 | 4.42 |
| ev_00285376 | u_024311 | goal_reached | 2026-04-16 07:21:58 | 2026-04-20 17:20:26 | 381508 | 4.42 |
| ev_00238007 | u_020216 | app_open | 2026-04-28 04:46:28 | 2026-05-02 13:46:57 | 378029 | 4.38 |

### Daily counts

Installs use install_ts. Event columns and active users use event_ts. Reward cost uses one resolved row per reward event_id. Ingested events use ingest_ts. A zero means that date has no rows in that column, not that the date was dropped.

| Date | Installs | Events | Active users | app_open | offer_view | offer_start | goal_reached | reward_paid | Reward ids | Reward cost EUR | Ingested events |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-03-29 | 0 | 14 | 14 | 6 | 6 | 2 | 0 | 0 | 0 | 0.00 | 0 |
| 2026-03-30 | 0 | 46 | 42 | 17 | 18 | 8 | 2 | 1 | 1 | 3.90 | 0 |
| 2026-03-31 | 0 | 40 | 38 | 21 | 10 | 3 | 6 | 0 | 0 | 0.00 | 0 |
| 2026-04-01 | 634 | 1,340 | 517 | 661 | 359 | 220 | 73 | 27 | 27 | 51.65 | 742 |
| 2026-04-02 | 718 | 3,598 | 1,156 | 1,766 | 984 | 598 | 190 | 60 | 59 | 149.51 | 3,048 |
| 2026-04-03 | 631 | 5,143 | 1,715 | 2,552 | 1,452 | 785 | 283 | 71 | 68 | 173.23 | 4,724 |
| 2026-04-04 | 656 | 5,905 | 2,194 | 2,857 | 1,627 | 975 | 358 | 88 | 88 | 214.53 | 5,723 |
| 2026-04-05 | 678 | 6,698 | 2,591 | 3,350 | 1,863 | 1,009 | 399 | 77 | 74 | 216.52 | 6,408 |
| 2026-04-06 | 681 | 7,067 | 2,817 | 3,409 | 2,004 | 1,107 | 420 | 127 | 121 | 336.35 | 6,997 |
| 2026-04-07 | 689 | 7,550 | 3,121 | 3,777 | 2,004 | 1,193 | 443 | 133 | 129 | 338.00 | 7,493 |
| 2026-04-08 | 717 | 7,946 | 3,386 | 3,894 | 2,182 | 1,231 | 495 | 144 | 143 | 400.13 | 7,856 |
| 2026-04-09 | 689 | 8,073 | 3,508 | 3,961 | 2,185 | 1,304 | 457 | 166 | 161 | 404.91 | 8,058 |
| 2026-04-10 | 704 | 8,304 | 3,627 | 3,999 | 2,339 | 1,313 | 465 | 188 | 179 | 518.83 | 8,228 |
| 2026-04-11 | 603 | 7,985 | 3,623 | 3,858 | 2,218 | 1,205 | 487 | 217 | 209 | 567.32 | 8,082 |
| 2026-04-12 | 635 | 7,898 | 3,616 | 3,784 | 2,174 | 1,236 | 477 | 227 | 219 | 592.57 | 7,866 |
| 2026-04-13 | 676 | 7,975 | 3,688 | 3,804 | 2,231 | 1,258 | 464 | 218 | 214 | 575.55 | 7,911 |
| 2026-04-14 | 672 | 7,947 | 3,648 | 3,862 | 2,265 | 1,189 | 432 | 199 | 194 | 531.35 | 7,953 |
| 2026-04-15 | 679 | 7,926 | 3,574 | 3,879 | 2,194 | 1,222 | 458 | 173 | 170 | 464.56 | 8,026 |
| 2026-04-16 | 666 | 8,218 | 3,724 | 4,045 | 2,275 | 1,241 | 484 | 173 | 171 | 444.19 | 8,067 |
| 2026-04-17 | 664 | 8,157 | 3,704 | 4,008 | 2,174 | 1,295 | 467 | 213 | 207 | 545.63 | 8,215 |
| 2026-04-18 | 682 | 8,224 | 3,706 | 3,978 | 2,244 | 1,287 | 513 | 202 | 194 | 512.70 | 8,201 |
| 2026-04-19 | 702 | 8,181 | 3,724 | 3,974 | 2,279 | 1,214 | 518 | 196 | 188 | 484.04 | 8,110 |
| 2026-04-20 | 656 | 8,299 | 3,758 | 4,035 | 2,262 | 1,317 | 470 | 215 | 207 | 605.01 | 8,314 |
| 2026-04-21 | 707 | 8,116 | 3,716 | 3,925 | 2,236 | 1,303 | 497 | 155 | 148 | 398.67 | 8,182 |
| 2026-04-22 | 685 | 8,043 | 3,712 | 3,913 | 2,210 | 1,243 | 492 | 185 | 179 | 519.36 | 8,067 |
| 2026-04-23 | 655 | 8,109 | 3,734 | 3,983 | 2,181 | 1,287 | 460 | 198 | 194 | 552.03 | 8,053 |
| 2026-04-24 | 665 | 8,221 | 3,728 | 3,910 | 2,281 | 1,351 | 477 | 202 | 197 | 530.24 | 8,246 |
| 2026-04-25 | 678 | 8,058 | 3,676 | 3,946 | 2,220 | 1,234 | 441 | 217 | 209 | 526.03 | 8,002 |
| 2026-04-26 | 650 | 8,037 | 3,687 | 3,770 | 2,289 | 1,301 | 481 | 196 | 190 | 499.49 | 8,116 |
| 2026-04-27 | 651 | 7,986 | 3,672 | 3,915 | 2,180 | 1,268 | 427 | 196 | 189 | 466.31 | 7,944 |
| 2026-04-28 | 672 | 7,937 | 3,608 | 3,985 | 2,130 | 1,183 | 442 | 197 | 191 | 535.60 | 8,009 |
| 2026-04-29 | 661 | 8,066 | 3,708 | 3,903 | 2,161 | 1,349 | 447 | 206 | 198 | 551.63 | 8,126 |
| 2026-04-30 | 621 | 7,879 | 3,636 | 3,859 | 2,174 | 1,182 | 469 | 195 | 189 | 529.59 | 7,907 |
| 2026-05-01 | 684 | 7,882 | 3,607 | 3,788 | 2,149 | 1,278 | 491 | 176 | 170 | 476.86 | 7,784 |
| 2026-05-02 | 645 | 7,925 | 3,624 | 3,862 | 2,183 | 1,248 | 447 | 185 | 177 | 480.44 | 7,906 |
| 2026-05-03 | 648 | 8,117 | 3,685 | 3,914 | 2,179 | 1,346 | 479 | 199 | 192 | 485.65 | 8,031 |
| 2026-05-04 | 685 | 7,995 | 3,669 | 3,900 | 2,265 | 1,207 | 444 | 179 | 173 | 473.39 | 8,066 |
| 2026-05-05 | 643 | 7,969 | 3,611 | 3,883 | 2,193 | 1,247 | 465 | 181 | 176 | 468.42 | 8,025 |
| 2026-05-06 | 659 | 7,920 | 3,661 | 3,796 | 2,179 | 1,269 | 470 | 206 | 199 | 550.13 | 7,968 |
| 2026-05-07 | 697 | 7,848 | 3,632 | 3,802 | 2,229 | 1,158 | 468 | 191 | 186 | 516.20 | 7,759 |
| 2026-05-08 | 704 | 8,110 | 3,728 | 3,981 | 2,201 | 1,280 | 467 | 181 | 178 | 477.66 | 7,999 |
| 2026-05-09 | 639 | 8,070 | 3,751 | 3,918 | 2,274 | 1,186 | 500 | 192 | 187 | 486.42 | 8,158 |
| 2026-05-10 | 655 | 8,052 | 3,659 | 3,952 | 2,177 | 1,276 | 464 | 183 | 177 | 498.73 | 8,055 |
| 2026-05-11 | 671 | 7,995 | 3,616 | 3,891 | 2,114 | 1,296 | 498 | 196 | 191 | 523.40 | 8,048 |
| 2026-05-12 | 644 | 8,078 | 3,725 | 3,957 | 2,194 | 1,299 | 434 | 194 | 190 | 509.71 | 8,017 |
| 2026-05-13 | 656 | 7,722 | 3,618 | 3,736 | 2,103 | 1,224 | 467 | 192 | 189 | 475.69 | 7,840 |
| 2026-05-14 | 672 | 7,957 | 3,631 | 3,852 | 2,173 | 1,250 | 498 | 184 | 178 | 487.01 | 7,885 |
| 2026-05-15 | 675 | 7,897 | 3,650 | 3,895 | 2,120 | 1,247 | 429 | 206 | 201 | 541.39 | 7,888 |
| 2026-05-16 | 614 | 7,857 | 3,605 | 3,857 | 2,140 | 1,204 | 477 | 179 | 175 | 483.36 | 7,942 |
| 2026-05-17 | 677 | 7,796 | 3,574 | 3,766 | 2,141 | 1,254 | 432 | 203 | 197 | 488.43 | 7,770 |
| 2026-05-18 | 693 | 8,036 | 3,678 | 3,930 | 2,110 | 1,352 | 434 | 210 | 206 | 570.73 | 7,996 |
| 2026-05-19 | 599 | 7,944 | 3,638 | 3,842 | 2,149 | 1,273 | 491 | 189 | 184 | 471.62 | 7,971 |
| 2026-05-20 | 703 | 7,995 | 3,627 | 3,823 | 2,225 | 1,251 | 492 | 204 | 200 | 480.77 | 7,927 |
| 2026-05-21 | 672 | 8,105 | 3,682 | 3,947 | 2,207 | 1,247 | 504 | 200 | 194 | 554.49 | 8,051 |
| 2026-05-22 | 654 | 8,047 | 3,655 | 3,962 | 2,163 | 1,258 | 503 | 161 | 157 | 433.52 | 8,081 |
| 2026-05-23 | 671 | 7,984 | 3,668 | 3,965 | 2,115 | 1,210 | 485 | 209 | 197 | 546.14 | 7,999 |
| 2026-05-24 | 699 | 8,146 | 3,681 | 3,936 | 2,255 | 1,279 | 481 | 195 | 183 | 486.34 | 8,129 |
| 2026-05-25 | 646 | 7,719 | 3,603 | 3,791 | 2,121 | 1,178 | 434 | 195 | 188 | 537.87 | 7,937 |
| 2026-05-26 | 691 | 7,982 | 3,695 | 3,848 | 2,212 | 1,258 | 455 | 209 | 203 | 551.20 | 7,948 |
| 2026-05-27 | 665 | 5,773 | 3,081 | 2,801 | 1,559 | 937 | 366 | 110 | 105 | 252.41 | 8,053 |
| 2026-05-28 | 682 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 | 0 |
| 2026-05-29 | 616 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 | 0 |
| 2026-05-30 | 664 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 | 0 |

## Key Findings Before Pipeline Design

| Finding | Evidence | Potential impact | Confidence | Needs business clarification? |
| --- | --- | --- | --- | --- |
| event_id is not unique | 12,721 extra rows; only ingest_ts varies inside the groups | Counting rows counts the same event more than once, including reward cost | High | Yes — confirm event_id is the identity, and which ingest_ts to keep |
| Ingest often falls on a later calendar day than the event | 119,307 of 435,907 rows; max delay 5.58 days; ingest before event: 0 | A job that closes a calendar day at 00:15 will miss rows whose event_ts is that day but whose ingest_ts is later | High | Yes — how long a day must stay open |
| country spellings differ by case and trailing space | 8 normalized codes have more than one raw spelling | A group-by on the raw string splits one country | High | Yes — confirm trim and upper-case is acceptable |
| Some event offer_ids are not in offers.csv | 13,672 non-blank unknown offer rows; unresolved reward_paid rows: 0 | Depends on event_name. Reward cost cannot be priced when reward_paid does not resolve. Other event types may not need a known offer | High | Yes — which event names must reference offers.csv |
| Some events are timestamped before the user's install | 3,094 rows with event_ts < install_ts | Dropping them changes user and event counts. Keeping them leaves activity before the install | High | Yes — clock skew versus real pre-install activity |
| Duplicate reward rows change the EUR total | 27368.66 EUR on all resolved rows vs 26547.41 EUR on one row per event_id | Reward cost moves by the difference if duplicates are counted | High | Yes — same question as the event_id identity |
| user_profile is not a projection of the event log | events_lifetime equals raw event rows for 23,785 users; no day, country, or platform columns | It cannot build the daily country-platform grain, and the lifetime fields do not reproduce simple event aggregates | High | Yes — what events_lifetime, last_seen_ts, revenue_30d_eur, and is_payer mean |
| Lifecycle steps are sometimes missing or out of timestamp order | See the four-way splits in the events section, on both (user, offer) and user grains | Enforcing a strict funnel in silver would drop or quarantine real-looking rows | Medium | Yes — which sequences are allowed |
| Timestamps have no timezone | Zero values match a trailing Z or numeric offset | Day boundaries move if the strings are not already in the reporting zone | High | Yes — which clock the strings are in |
| Blank campaign_id lines up with organic | Checked as a cross-tab in the installs section | Treating blank campaign as a data error would blank out organic acquisition | Medium | Yes — expected encoding of organic |

## Questions This Data Raises for the Pipeline

- Is `event_id` the deduplication key? Duplicate groups differ in `ingest_ts` only, but the files do not define the key.
- If one row per `event_id` is kept, which `ingest_ts` should win? The rows disagree, and the metric changes if reward rows are counted twice (27368.66 EUR vs 26547.41 EUR on the two readings above).
- Which timestamp is the reporting day: `event_ts`, `ingest_ts`, or `install_ts`? 119,307 events do not have the same calendar date on event_ts and ingest_ts.
- How long does a closed day need to stay correctable? The maximum observed delay is 5.58 days, and 4,475 rows exceed 48 hours. A one-day window does not cover the observed tail.
- Should an offer_id missing from offers.csv be kept, quarantined, or rejected? The answer may differ by event_name, because unknown ids are not confined to reward_paid. See the referential table before choosing one rule.
- What should happen to event_ts values that precede install_ts? The files show the gap and do not say whether it is an error.
- Is user_profile a reconciliation source only? It cannot supply day, country, or platform, and its lifetime fields do not match simple event aggregates.
- Can offer payout change over time? offers.csv is one row per offer_id with no effective date, so a change would be invisible in this extract.
- Which silver checks are safe to enforce? Uniqueness of event_id is not true of the raw file. A required offer, a required prior funnel step, and event_ts >= install_ts all fail for some observed rows.
- Do the timestamp strings share one timezone? None of them carry an offset, so a calendar-day rule is ambiguous until that is known.
- Is a blank campaign_id on organic installs intentional? The blank values and the organic rows are the same set in this file.

-- Gold daily metrics: metric_date × country × platform
--
-- Intentionally SQL: metric definitions stay readable and reviewable.
-- Aggregate installs and events SEPARATELY, then FULL OUTER JOIN.
-- Never join raw installs to raw events before aggregation (fan-out).
--
-- Placeholders (substituted by notebook / pipeline runner):
--   {{silver_installs}}  e.g. workspace.rewards_silver.installs
--   {{silver_events}}    e.g. workspace.rewards_silver.events
--   {{start_date}}       inclusive YYYY-MM-DD
--   {{end_date}}         inclusive YYYY-MM-DD
--
-- Reporting clock: event_date / install_date (business time), not ingest_ts.

CREATE OR REPLACE TEMP VIEW gold_daily_metrics_updates AS
WITH installs_daily AS (
    SELECT
        install_date AS metric_date,
        country,
        platform,
        COUNT(*) AS installs
    FROM {{silver_installs}}
    WHERE install_date BETWEEN DATE '{{start_date}}' AND DATE '{{end_date}}'
    GROUP BY install_date, country, platform
),
events_daily AS (
    SELECT
        event_date AS metric_date,
        country,
        platform,
        COUNT(DISTINCT CASE WHEN event_name = 'app_open' THEN user_id END)
            AS unique_app_open_users,
        COUNT(DISTINCT CASE WHEN event_name = 'offer_view' THEN user_id END)
            AS unique_offer_view_users,
        COUNT(DISTINCT CASE WHEN event_name = 'offer_start' THEN user_id END)
            AS unique_offer_start_users,
        COUNT(DISTINCT CASE WHEN event_name = 'goal_reached' THEN user_id END)
            AS unique_goal_reached_users,
        COUNT(DISTINCT CASE WHEN event_name = 'reward_paid' THEN user_id END)
            AS unique_reward_paid_users,
        SUM(CASE WHEN event_name = 'reward_paid' THEN 1 ELSE 0 END)
            AS reward_payouts,
        CAST(
            SUM(
                CASE
                    WHEN event_name = 'reward_paid'
                    THEN COALESCE(payout_eur, CAST(0 AS DECIMAL(18, 2)))
                    ELSE CAST(0 AS DECIMAL(18, 2))
                END
            ) AS DECIMAL(18, 2)
        ) AS reward_cost_eur
    FROM {{silver_events}}
    WHERE event_date BETWEEN DATE '{{start_date}}' AND DATE '{{end_date}}'
    GROUP BY event_date, country, platform
)
SELECT
    COALESCE(i.metric_date, e.metric_date) AS metric_date,
    COALESCE(i.country, e.country) AS country,
    COALESCE(i.platform, e.platform) AS platform,
    COALESCE(i.installs, CAST(0 AS BIGINT)) AS installs,
    COALESCE(e.unique_app_open_users, CAST(0 AS BIGINT)) AS unique_app_open_users,
    COALESCE(e.unique_offer_view_users, CAST(0 AS BIGINT)) AS unique_offer_view_users,
    COALESCE(e.unique_offer_start_users, CAST(0 AS BIGINT)) AS unique_offer_start_users,
    COALESCE(e.unique_goal_reached_users, CAST(0 AS BIGINT)) AS unique_goal_reached_users,
    COALESCE(e.unique_reward_paid_users, CAST(0 AS BIGINT)) AS unique_reward_paid_users,
    COALESCE(e.reward_payouts, CAST(0 AS BIGINT)) AS reward_payouts,
    COALESCE(e.reward_cost_eur, CAST(0 AS DECIMAL(18, 2))) AS reward_cost_eur,
    CURRENT_TIMESTAMP() AS _updated_at
FROM installs_daily i
FULL OUTER JOIN events_daily e
    ON i.metric_date = e.metric_date
   AND i.country = e.country
   AND i.platform = e.platform
;

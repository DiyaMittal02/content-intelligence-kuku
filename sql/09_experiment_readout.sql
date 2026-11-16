-- ============================================================================
-- 09_experiment_readout.sql
-- Purpose : Read out the simulated paywall-position A/B test (paywall at ep6
--           vs ep8). Subscribe rate among users whose first paywall was in each
--           group, with absolute lift and a 95% confidence interval.
-- Skills  : group statistics, proportion test, normal-approx CI, readout logic.
-- Planted story #3. SYNTHETIC DATA.
-- ============================================================================

-- Assign each user to the group of their FIRST paywall encounter (first-touch).
WITH first_paywall AS (
    SELECT DISTINCT ON (user_id)
           user_id,
           (props::json ->> 'title_id')::bigint AS title_id
    FROM app_events
    WHERE event_name = 'paywall_view'
    ORDER BY user_id, ts
),
assigned AS (
    SELECT fp.user_id, t.experiment_group
    FROM first_paywall fp
    JOIN titles t ON t.title_id = fp.title_id
    WHERE t.experiment_group IN ('paywall_ep6','paywall_ep8')
),
subs AS (SELECT DISTINCT user_id FROM subscriptions),
group_stats AS (
    SELECT
        a.experiment_group,
        count(*)                                        AS reachers,       -- n
        count(s.user_id)                                AS subscribers,    -- k
        count(s.user_id)::numeric / NULLIF(count(*),0)  AS p               -- subscribe rate
    FROM assigned a
    LEFT JOIN subs s ON s.user_id = a.user_id
    GROUP BY a.experiment_group
)
-- 1. Per-group stats ---------------------------------------------------------
SELECT
    experiment_group,
    reachers,
    subscribers,
    round(100.0 * p, 2) AS subscribe_pct
FROM group_stats
ORDER BY experiment_group;

-- 2. Lift + 95% CI (ep8 minus ep6) -------------------------------------------
WITH first_paywall AS (
    SELECT DISTINCT ON (user_id)
           user_id, (props::json ->> 'title_id')::bigint AS title_id
    FROM app_events WHERE event_name = 'paywall_view'
    ORDER BY user_id, ts
),
assigned AS (
    SELECT fp.user_id, t.experiment_group
    FROM first_paywall fp JOIN titles t ON t.title_id = fp.title_id
    WHERE t.experiment_group IN ('paywall_ep6','paywall_ep8')
),
subs AS (SELECT DISTINCT user_id FROM subscriptions),
gs AS (
    SELECT a.experiment_group,
           count(*)::numeric AS n,
           count(s.user_id)::numeric AS k,
           count(s.user_id)::numeric / NULLIF(count(*),0) AS p
    FROM assigned a LEFT JOIN subs s ON s.user_id = a.user_id
    GROUP BY a.experiment_group
),
ab AS (
    SELECT
        max(n) FILTER (WHERE experiment_group='paywall_ep6') AS n6,
        max(p) FILTER (WHERE experiment_group='paywall_ep6') AS p6,
        max(n) FILTER (WHERE experiment_group='paywall_ep8') AS n8,
        max(p) FILTER (WHERE experiment_group='paywall_ep8') AS p8
    FROM gs
)
SELECT
    round(100.0 * p6, 2)                                       AS ep6_subscribe_pct,
    round(100.0 * p8, 2)                                       AS ep8_subscribe_pct,
    round(100.0 * (p8 - p6), 2)                                AS abs_lift_pp,
    round(100.0 * 1.96 * sqrt(p6*(1-p6)/n6 + p8*(1-p8)/n8), 2) AS ci95_halfwidth_pp,
    CASE
        WHEN (p8 - p6) - 1.96*sqrt(p6*(1-p6)/n6 + p8*(1-p8)/n8) > 0
        THEN 'Significant: ep8 > ep6 at 95%'
        ELSE 'Not significant at 95%'
    END                                                        AS verdict
FROM ab;

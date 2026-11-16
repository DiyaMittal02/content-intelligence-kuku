-- ============================================================================
-- 02_activation_funnel.sql
-- Purpose : The core acquisition-to-monetisation funnel:
--           signup -> first play -> >=3 episodes (activation) ->
--           paywall view -> subscribe.
-- Skills  : CTEs, conditional aggregation, NULLIF-safe step conversion.
-- Business question #1: where do users drop off?
-- SYNTHETIC DATA.
-- ============================================================================

WITH base AS (
    SELECT user_id, signup_ts FROM users
),
first_play AS (
    SELECT user_id, min(ts) AS first_play_ts
    FROM consumption_events
    WHERE seconds_consumed >= 30
    GROUP BY user_id
),
-- activation: >= 3 episodes within 72h of signup
activation AS (
    SELECT ce.user_id
    FROM consumption_events ce
    JOIN base b ON b.user_id = ce.user_id
    WHERE ce.ts <= b.signup_ts + INTERVAL '72 hours'
    GROUP BY ce.user_id
    HAVING count(DISTINCT ce.episode_id) >= 3
),
paywall AS (
    SELECT DISTINCT user_id
    FROM app_events
    WHERE event_name = 'paywall_view'
),
subscribers AS (
    SELECT DISTINCT user_id FROM subscriptions
)
SELECT
    count(*)                                                        AS signups,
    count(fp.user_id)                                               AS reached_first_play,
    count(a.user_id)                                                AS activated_3plus_72h,
    count(pw.user_id)                                               AS saw_paywall,
    count(s.user_id)                                                AS subscribed,
    round(100.0 * count(fp.user_id) / NULLIF(count(*),0), 1)                 AS pct_first_play,
    round(100.0 * count(a.user_id)  / NULLIF(count(fp.user_id),0), 1)        AS pct_firstplay_to_activation,
    round(100.0 * count(pw.user_id) / NULLIF(count(a.user_id),0), 1)         AS pct_activation_to_paywall,
    round(100.0 * count(s.user_id)  / NULLIF(count(pw.user_id),0), 1)        AS pct_paywall_to_subscribe,
    round(100.0 * count(s.user_id)  / NULLIF(count(*),0), 2)                 AS pct_overall_signup_to_sub
FROM base b
LEFT JOIN first_play  fp ON fp.user_id = b.user_id
LEFT JOIN activation  a  ON a.user_id  = b.user_id
LEFT JOIN paywall     pw ON pw.user_id = b.user_id
LEFT JOIN subscribers s  ON s.user_id  = b.user_id;

-- Funnel split by acquisition channel (where to spend marketing) --------------
WITH fp AS (
    SELECT user_id FROM consumption_events WHERE seconds_consumed >= 30 GROUP BY user_id
),
pw AS (SELECT DISTINCT user_id FROM app_events WHERE event_name = 'paywall_view'),
sub AS (SELECT DISTINCT user_id FROM subscriptions)
SELECT
    u.acq_channel,
    count(*)                                                 AS signups,
    round(100.0*count(fp.user_id) /NULLIF(count(*),0),1)     AS pct_first_play,
    round(100.0*count(pw.user_id) /NULLIF(count(*),0),1)     AS pct_paywall,
    round(100.0*count(sub.user_id)/NULLIF(count(*),0),2)     AS pct_subscribe
FROM users u
LEFT JOIN fp  ON fp.user_id  = u.user_id
LEFT JOIN pw  ON pw.user_id  = u.user_id
LEFT JOIN sub ON sub.user_id = u.user_id
GROUP BY u.acq_channel
ORDER BY pct_subscribe DESC;

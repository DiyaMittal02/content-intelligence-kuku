-- ============================================================================
-- 03_engagement.sql
-- Purpose : DAU / WAU / MAU, stickiness (DAU/MAU), minutes per user.
-- Skills  : date_trunc, window functions, rolling distinct-count approximation.
-- SYNTHETIC DATA.
-- ============================================================================

-- A "qualified" consumption event = >= 30 seconds (matches DAU definition).
WITH daily AS (
    SELECT ts::date AS d, user_id
    FROM consumption_events
    WHERE seconds_consumed >= 30
    GROUP BY ts::date, user_id
)
-- 1. Daily active users, with 7-day rolling average via window function -------
SELECT
    d,
    count(*)                                                       AS dau,
    round(avg(count(*)) OVER (ORDER BY d ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 0) AS dau_7day_avg
FROM daily
GROUP BY d
ORDER BY d;

-- 2. Monthly stickiness = avg(DAU in month) / MAU(month) ---------------------
WITH daily AS (
    SELECT ts::date AS d, user_id
    FROM consumption_events
    WHERE seconds_consumed >= 30
    GROUP BY ts::date, user_id
),
dau AS (
    SELECT d, date_trunc('month', d) AS mth, count(*) AS dau
    FROM daily GROUP BY d
),
mau AS (
    SELECT date_trunc('month', ts) AS mth, count(DISTINCT user_id) AS mau
    FROM consumption_events
    WHERE seconds_consumed >= 30
    GROUP BY date_trunc('month', ts)
)
SELECT
    m.mth::date                                   AS month,
    round(avg(dau.dau), 0)                        AS avg_dau,
    m.mau,
    round(100.0 * avg(dau.dau) / NULLIF(m.mau,0), 1) AS stickiness_pct
FROM mau m
JOIN dau ON dau.mth = m.mth
GROUP BY m.mth, m.mau
ORDER BY m.mth;

-- 3. Minutes consumed per active user, per month -----------------------------
SELECT
    date_trunc('month', ts)::date                  AS month,
    count(DISTINCT user_id)                         AS active_users,
    round(sum(seconds_consumed)/60.0, 0)           AS total_minutes,
    round( (sum(seconds_consumed)/60.0)
           / NULLIF(count(DISTINCT user_id),0), 1)  AS minutes_per_user
FROM consumption_events
WHERE seconds_consumed >= 30
GROUP BY date_trunc('month', ts)
ORDER BY month;

-- 4. Format comparison: audio vs micro-drama minutes per user ----------------
SELECT
    t.format,
    count(DISTINCT ce.user_id)                      AS users,
    round(sum(ce.seconds_consumed)/60.0,0)          AS total_minutes,
    round((sum(ce.seconds_consumed)/60.0)/NULLIF(count(DISTINCT ce.user_id),0),1) AS minutes_per_user
FROM consumption_events ce
JOIN episodes e ON e.episode_id = ce.episode_id
JOIN titles   t ON t.title_id   = e.title_id
GROUP BY t.format
ORDER BY minutes_per_user DESC;

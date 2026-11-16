-- ============================================================================
-- 01_data_quality.sql
-- Purpose : Trust the data before analysing it. Row counts, null coverage,
--           duplicate keys, orphan foreign keys (anti-joins), date coverage.
-- Skills  : aggregates, FILTER, LEFT JOIN anti-joins, date range checks.
-- SYNTHETIC DATA.
-- ============================================================================

-- 1. Row counts per table -----------------------------------------------------
SELECT 'users'              AS table_name, count(*) AS rows FROM users
UNION ALL SELECT 'titles',             count(*) FROM titles
UNION ALL SELECT 'episodes',           count(*) FROM episodes
UNION ALL SELECT 'sessions',           count(*) FROM sessions
UNION ALL SELECT 'subscriptions',      count(*) FROM subscriptions
UNION ALL SELECT 'payments',           count(*) FROM payments
UNION ALL SELECT 'consumption_events', count(*) FROM consumption_events
UNION ALL SELECT 'app_events',         count(*) FROM app_events
ORDER BY table_name;

-- 2. Null / blank coverage on key columns ------------------------------------
SELECT
    count(*)                                               AS users_total,
    count(*) FILTER (WHERE signup_ts   IS NULL)            AS null_signup,
    count(*) FILTER (WHERE acq_channel IS NULL OR acq_channel = '') AS null_channel,
    count(*) FILTER (WHERE language    IS NULL OR language = '')     AS null_language,
    count(*) FILTER (WHERE device_tier NOT IN ('low','mid','high')) AS bad_device_tier
FROM users;

-- 3. Duplicate primary keys (should all be zero) -----------------------------
SELECT 'users'              AS table_name, count(*) - count(DISTINCT user_id)    AS dup_pk FROM users
UNION ALL SELECT 'titles',             count(*) - count(DISTINCT title_id)   FROM titles
UNION ALL SELECT 'episodes',           count(*) - count(DISTINCT episode_id)  FROM episodes
UNION ALL SELECT 'consumption_events', count(*) - count(DISTINCT event_id)    FROM consumption_events;

-- 4. Orphan foreign keys via LEFT JOIN anti-join -----------------------------
-- consumption_events whose episode_id is missing from episodes
SELECT count(*) AS orphan_consumption_episodes
FROM consumption_events ce
LEFT JOIN episodes e ON e.episode_id = ce.episode_id
WHERE e.episode_id IS NULL;

-- payments whose sub_id is missing from subscriptions
SELECT count(*) AS orphan_payment_subs
FROM payments p
LEFT JOIN subscriptions s ON s.sub_id = p.sub_id
WHERE s.sub_id IS NULL;

-- 5. Date coverage & future-dated rows ---------------------------------------
SELECT
    min(signup_ts)::date AS first_signup,
    max(signup_ts)::date AS last_signup,
    count(*) FILTER (WHERE signup_ts > TIMESTAMP '2026-11-01') AS signups_after_cutoff
FROM users;

SELECT
    min(ts)::date AS first_event,
    max(ts)::date AS last_event,
    count(*) FILTER (WHERE ts > TIMESTAMP '2026-11-01') AS events_after_cutoff
FROM consumption_events;

-- 6. Logical consistency: episodes marked paid must be at/after paywall ------
SELECT count(*) AS paid_flag_mismatch
FROM episodes e
JOIN titles t ON t.title_id = e.title_id
WHERE e.is_paid <> (e.ep_number >= t.paywall_ep);

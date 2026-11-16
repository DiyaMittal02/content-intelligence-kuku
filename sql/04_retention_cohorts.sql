-- ============================================================================
-- 04_retention_cohorts.sql
-- Purpose : D1 / D7 / D30 retention by weekly signup cohort, and sliced by
--           language, acquisition channel, and GENRE of first watched title.
--           Genre slice surfaces planted story #1 (Thriller: high D1, low D30).
-- Skills  : cohort matrix, generate_series-free day arithmetic, FILTER,
--           activity-day derivation, NULLIF-safe rates.
-- Business question #2. SYNTHETIC DATA.
-- ============================================================================

-- Activity days = distinct (user, day-offset-from-signup) with >=30s play.
-- D-n retention here uses the EXACT day n (state this definition in the report).
WITH activity AS (
    SELECT
        ce.user_id,
        (ce.ts::date - u.signup_ts::date) AS day_offset
    FROM consumption_events ce
    JOIN users u ON u.user_id = ce.user_id
    WHERE ce.seconds_consumed >= 30
    GROUP BY ce.user_id, (ce.ts::date - u.signup_ts::date)
),
cohort AS (
    SELECT
        u.user_id,
        date_trunc('week', u.signup_ts)::date AS cohort_week,
        -- only users mature enough to be observed at day n
        (DATE '2026-11-01' - u.signup_ts::date) AS observable_days
    FROM users u
)
-- 1. Weekly cohort retention matrix ------------------------------------------
SELECT
    c.cohort_week,
    count(*)                                                                   AS cohort_size,
    round(100.0 * count(*) FILTER (WHERE a1.user_id IS NOT NULL)
                 / NULLIF(count(*) FILTER (WHERE c.observable_days >= 1),0), 1) AS d1_pct,
    round(100.0 * count(*) FILTER (WHERE a7.user_id IS NOT NULL)
                 / NULLIF(count(*) FILTER (WHERE c.observable_days >= 7),0), 1) AS d7_pct,
    round(100.0 * count(*) FILTER (WHERE a30.user_id IS NOT NULL)
                 / NULLIF(count(*) FILTER (WHERE c.observable_days >= 30),0),1) AS d30_pct
FROM cohort c
LEFT JOIN activity a1  ON a1.user_id  = c.user_id AND a1.day_offset  = 1
LEFT JOIN activity a7  ON a7.user_id  = c.user_id AND a7.day_offset  = 7
LEFT JOIN activity a30 ON a30.user_id = c.user_id AND a30.day_offset = 30
GROUP BY c.cohort_week
ORDER BY c.cohort_week;

-- 2. Retention by GENRE of first watched title (planted story #1) ------------
WITH activity AS (
    SELECT ce.user_id, (ce.ts::date - u.signup_ts::date) AS day_offset
    FROM consumption_events ce
    JOIN users u ON u.user_id = ce.user_id
    WHERE ce.seconds_consumed >= 30
    GROUP BY ce.user_id, (ce.ts::date - u.signup_ts::date)
),
first_title AS (          -- genre of each user's earliest consumption event
    SELECT DISTINCT ON (ce.user_id)
           ce.user_id, t.genre
    FROM consumption_events ce
    JOIN episodes e ON e.episode_id = ce.episode_id
    JOIN titles   t ON t.title_id   = e.title_id
    ORDER BY ce.user_id, ce.ts
),
mat AS (
    SELECT u.user_id, ft.genre,
           (DATE '2026-11-01' - u.signup_ts::date) AS observable_days
    FROM users u JOIN first_title ft ON ft.user_id = u.user_id
)
SELECT
    m.genre,
    count(*)                                                                    AS users,
    round(100.0*count(*) FILTER (WHERE a1.user_id  IS NOT NULL)
                /NULLIF(count(*) FILTER (WHERE m.observable_days>=1),0),1)       AS d1_pct,
    round(100.0*count(*) FILTER (WHERE a7.user_id  IS NOT NULL)
                /NULLIF(count(*) FILTER (WHERE m.observable_days>=7),0),1)       AS d7_pct,
    round(100.0*count(*) FILTER (WHERE a30.user_id IS NOT NULL)
                /NULLIF(count(*) FILTER (WHERE m.observable_days>=30),0),1)      AS d30_pct
FROM mat m
LEFT JOIN activity a1  ON a1.user_id  = m.user_id AND a1.day_offset  = 1
LEFT JOIN activity a7  ON a7.user_id  = m.user_id AND a7.day_offset  = 7
LEFT JOIN activity a30 ON a30.user_id = m.user_id AND a30.day_offset = 30
GROUP BY m.genre
ORDER BY d1_pct DESC;

-- 3. Retention by acquisition channel (quality of traffic) -------------------
WITH activity AS (
    SELECT ce.user_id, (ce.ts::date - u.signup_ts::date) AS day_offset
    FROM consumption_events ce
    JOIN users u ON u.user_id = ce.user_id
    WHERE ce.seconds_consumed >= 30
    GROUP BY ce.user_id, (ce.ts::date - u.signup_ts::date)
)
SELECT
    u.acq_channel,
    count(*) AS users,
    round(100.0*count(*) FILTER (WHERE a7.user_id IS NOT NULL)
                /NULLIF(count(*) FILTER (WHERE (DATE '2026-11-01'-u.signup_ts::date)>=7),0),1) AS d7_pct
FROM users u
LEFT JOIN activity a7 ON a7.user_id = u.user_id AND a7.day_offset = 7
GROUP BY u.acq_channel
ORDER BY d7_pct DESC;

-- ============================================================================
-- 07_monetisation.sql
-- Purpose : Trial->paid conversion, renewal rate, ARPPU, and payment failure
--           rate by week x method. Surfaces planted story #2 (UPI failure spike
--           in the week of 2026-08-11).
-- Skills  : multi-table joins, NULLIF-safe division, date_trunc, FILTER.
-- Business question #1 (monetisation tail). SYNTHETIC DATA.
-- ============================================================================

-- 1. Overall monetisation headline metrics -----------------------------------
WITH paying AS (                  -- a "paying user" made a real (>= Rs.99) charge
    SELECT DISTINCT s.user_id
    FROM payments p
    JOIN subscriptions s ON s.sub_id = p.sub_id
    WHERE p.status = 'success' AND p.amount >= 99
),
revenue AS (
    SELECT sum(p.amount) AS total_rev
    FROM payments p
    WHERE p.status = 'success' AND p.amount >= 99
)
SELECT
    (SELECT count(*) FROM paying)                                       AS paying_users,
    (SELECT round(total_rev,0) FROM revenue)                           AS total_revenue,
    round( (SELECT total_rev FROM revenue)
           / NULLIF((SELECT count(*) FROM paying),0), 1)               AS arppu
;

-- 2. Trial -> paid conversion ------------------------------------------------
WITH trials AS (
    SELECT DISTINCT user_id, min(start_ts) AS trial_start
    FROM subscriptions WHERE plan = 'trial'
    GROUP BY user_id
),
converted AS (
    SELECT DISTINCT t.user_id
    FROM trials t
    JOIN subscriptions s
      ON s.user_id = t.user_id
     AND s.plan IN ('monthly','annual')
     AND s.start_ts > t.trial_start
)
SELECT
    count(*)                                                       AS trials,
    (SELECT count(*) FROM converted)                               AS converted_to_paid,
    round(100.0 * (SELECT count(*) FROM converted) / NULLIF(count(*),0), 1) AS trial_to_paid_pct
FROM trials;

-- 3. Renewal rate on paid plans ----------------------------------------------
SELECT
    plan,
    count(*)                                                       AS subs,
    count(*) FILTER (WHERE renewed)                                AS renewed,
    round(100.0 * count(*) FILTER (WHERE renewed) / NULLIF(count(*),0), 1) AS renewal_pct
FROM subscriptions
WHERE plan IN ('monthly','annual')
GROUP BY plan
ORDER BY plan;

-- 4. Payment failure rate by ISO week x method (planted story #2) ------------
SELECT
    date_trunc('week', ts)::date                                   AS iso_week,
    method,
    count(*)                                                       AS attempts,
    count(*) FILTER (WHERE status = 'failed')                      AS failures,
    round(100.0 * count(*) FILTER (WHERE status = 'failed') / NULLIF(count(*),0), 1) AS failure_pct
FROM payments
WHERE method = 'upi'
GROUP BY date_trunc('week', ts), method
ORDER BY iso_week;

-- 5. Failure rate by method overall (is the spike UPI-specific?) -------------
SELECT
    method,
    count(*)                                                       AS attempts,
    round(100.0 * count(*) FILTER (WHERE status='failed') / NULLIF(count(*),0),1) AS failure_pct
FROM payments
GROUP BY method
ORDER BY failure_pct DESC;

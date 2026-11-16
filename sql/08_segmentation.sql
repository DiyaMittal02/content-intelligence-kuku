-- ============================================================================
-- 08_segmentation.sql
-- Purpose : Behavioural segmentation (RFM-style) and a format-first comparison
--           (micro-drama-first vs audio-first users) for targeting.
-- Skills  : NTILE quartiles, CASE bucketing, CTE composition, views.
-- Business question #4. SYNTHETIC DATA.
-- ============================================================================

-- 1. RFM scoring on engagement (recency/frequency/volume of consumption) ------
WITH rfm_base AS (
    SELECT
        ce.user_id,
        DATE '2026-11-01' - max(ce.ts)::date       AS recency_days,
        count(*)                                    AS frequency_plays,
        sum(ce.seconds_consumed)/60.0               AS minutes
    FROM consumption_events ce
    WHERE ce.seconds_consumed >= 30
    GROUP BY ce.user_id
),
scored AS (
    SELECT
        user_id, recency_days, frequency_plays, round(minutes,1) AS minutes,
        NTILE(4) OVER (ORDER BY recency_days ASC)   AS r_score,   -- 4 = most recent
        NTILE(4) OVER (ORDER BY frequency_plays DESC) AS f_score,
        NTILE(4) OVER (ORDER BY minutes DESC)       AS m_score
    FROM rfm_base
)
SELECT
    CASE
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Champions'
        WHEN r_score >= 3 AND f_score <  3 THEN 'Promising / New'
        WHEN r_score <  3 AND f_score >= 3 THEN 'At risk (was active)'
        ELSE                                    'Hibernating'
    END                                          AS segment,
    count(*)                                     AS users,
    round(avg(frequency_plays),1)                AS avg_plays,
    round(avg(minutes),1)                        AS avg_minutes,
    round(avg(recency_days),1)                   AS avg_recency_days
FROM scored
GROUP BY 1
ORDER BY users DESC;

-- 2. Format-first comparison: does the first format predict value? -----------
-- Classify each user by the FORMAT of their first watched title, then compare
-- downstream retention breadth and subscribe rate.
WITH first_format AS (
    SELECT DISTINCT ON (ce.user_id)
           ce.user_id, t.format AS first_format
    FROM consumption_events ce
    JOIN episodes e ON e.episode_id = ce.episode_id
    JOIN titles   t ON t.title_id   = e.title_id
    ORDER BY ce.user_id, ce.ts
),
active_days AS (
    SELECT user_id, count(DISTINCT ts::date) AS active_days
    FROM consumption_events WHERE seconds_consumed >= 30
    GROUP BY user_id
),
subs AS (SELECT DISTINCT user_id FROM subscriptions)
SELECT
    ff.first_format,
    count(*)                                                      AS users,
    round(avg(ad.active_days),2)                                  AS avg_active_days,
    round(100.0 * count(s.user_id) / NULLIF(count(*),0), 2)       AS subscribe_pct
FROM first_format ff
LEFT JOIN active_days ad ON ad.user_id = ff.user_id
LEFT JOIN subs s         ON s.user_id  = ff.user_id
GROUP BY ff.first_format
ORDER BY subscribe_pct DESC;

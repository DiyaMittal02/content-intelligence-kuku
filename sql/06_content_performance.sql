-- ============================================================================
-- 06_content_performance.sql
-- Purpose : Rank titles by completion, reach, and revenue so programming can
--           see which shows earn promotion and which drag.
-- Skills  : RANK, PERCENT_RANK, NTILE, multi-CTE joins, NULLIF-safe ratios.
-- SYNTHETIC DATA.
-- ============================================================================

WITH plays AS (                   -- completion rate & reach per title
    SELECT
        e.title_id,
        count(*)                                           AS plays_started,
        count(*) FILTER (WHERE ce.completed)               AS plays_completed,
        count(DISTINCT ce.user_id)                         AS unique_viewers
    FROM consumption_events ce
    JOIN episodes e ON e.episode_id = ce.episode_id
    GROUP BY e.title_id
),
-- revenue attributed to a title = payments from users whose FIRST paywall_view
-- was on that title (simple single-touch attribution; stated as an assumption).
first_paywall AS (
    SELECT DISTINCT ON (user_id)
           user_id,
           (props::json ->> 'title_id')::bigint AS title_id
    FROM app_events
    WHERE event_name = 'paywall_view'
    ORDER BY user_id, ts
),
title_revenue AS (
    SELECT fp.title_id, round(sum(p.amount), 0) AS revenue
    FROM first_paywall fp
    JOIN subscriptions s ON s.user_id = fp.user_id
    JOIN payments p      ON p.sub_id  = s.sub_id AND p.status = 'success'
    GROUP BY fp.title_id
)
SELECT
    t.title_id,
    t.title_name,
    t.genre,
    t.format,
    pl.unique_viewers,
    round(100.0 * pl.plays_completed / NULLIF(pl.plays_started,0), 1) AS completion_pct,
    COALESCE(tr.revenue, 0)                                          AS revenue,
    RANK()         OVER (ORDER BY pl.unique_viewers DESC)            AS reach_rank,
    round(PERCENT_RANK() OVER (ORDER BY
          100.0*pl.plays_completed/NULLIF(pl.plays_started,0))::numeric, 2) AS completion_pctile,
    NTILE(4)       OVER (ORDER BY COALESCE(tr.revenue,0) DESC)       AS revenue_quartile
FROM titles t
JOIN plays pl        ON pl.title_id = t.title_id
LEFT JOIN title_revenue tr ON tr.title_id = t.title_id
ORDER BY pl.unique_viewers DESC
LIMIT 50;

-- Genre-level scorecard: which genres pull their weight -----------------------
WITH plays AS (
    SELECT e.title_id,
           count(*) AS plays_started,
           count(*) FILTER (WHERE ce.completed) AS plays_completed,
           count(DISTINCT ce.user_id) AS viewers
    FROM consumption_events ce JOIN episodes e ON e.episode_id = ce.episode_id
    GROUP BY e.title_id
)
SELECT
    t.genre,
    count(DISTINCT t.title_id)                                   AS titles,
    sum(pl.viewers)                                              AS total_viewers,
    round(100.0*sum(pl.plays_completed)/NULLIF(sum(pl.plays_started),0),1) AS completion_pct
FROM titles t
JOIN plays pl ON pl.title_id = t.title_id
GROUP BY t.genre
ORDER BY total_viewers DESC;

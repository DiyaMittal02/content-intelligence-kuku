-- ============================================================================
-- 05_episode_dropoff.sql
-- Purpose : Per-title episode survival curve and the PAYWALL CLIFF.
--           For each episode position, how many of the title's starters are
--           still watching, as a ratio to episode 1 (LAG for step-to-step drop).
-- Skills  : window functions (LAG, FIRST_VALUE), ratio-to-first, CASE flags.
-- Business question #3: which episodes cause the biggest drop-off, and is it
--           the paywall or the content?  SYNTHETIC DATA.
-- ============================================================================

-- Distinct users who watched each (title, ep_number).
WITH ep_watchers AS (
    SELECT
        e.title_id,
        e.ep_number,
        count(DISTINCT ce.user_id) AS watchers
    FROM consumption_events ce
    JOIN episodes e ON e.episode_id = ce.episode_id
    GROUP BY e.title_id, e.ep_number
),
survival AS (
    SELECT
        ew.title_id,
        ew.ep_number,
        ew.watchers,
        FIRST_VALUE(ew.watchers) OVER (PARTITION BY ew.title_id ORDER BY ew.ep_number) AS ep1_watchers,
        LAG(ew.watchers)         OVER (PARTITION BY ew.title_id ORDER BY ew.ep_number) AS prev_watchers
    FROM ep_watchers ew
)
SELECT
    s.title_id,
    t.title_name,
    t.genre,
    t.format,
    t.paywall_ep,
    s.ep_number,
    s.watchers,
    round(100.0 * s.watchers / NULLIF(s.ep1_watchers,0), 1)                 AS pct_of_ep1,
    round(100.0 * (s.prev_watchers - s.watchers) / NULLIF(s.prev_watchers,0), 1) AS step_drop_pct,
    CASE WHEN s.ep_number = t.paywall_ep THEN 'PAYWALL' ELSE '' END          AS marker
FROM survival s
JOIN titles t ON t.title_id = s.title_id
WHERE s.ep_number <= 15                       -- early episodes matter most
ORDER BY s.title_id, s.ep_number;

-- Aggregate "paywall cliff": average step-drop AT the paywall episode vs the
-- average step-drop at non-paywall early episodes. A big gap = the wall, not
-- the content, is losing users.
WITH ep_watchers AS (
    SELECT e.title_id, e.ep_number, count(DISTINCT ce.user_id) AS watchers
    FROM consumption_events ce
    JOIN episodes e ON e.episode_id = ce.episode_id
    GROUP BY e.title_id, e.ep_number
),
stepped AS (
    SELECT
        ew.title_id, ew.ep_number, ew.watchers,
        LAG(ew.watchers) OVER (PARTITION BY ew.title_id ORDER BY ew.ep_number) AS prev_watchers
    FROM ep_watchers ew
),
drops AS (
    SELECT
        s.title_id, s.ep_number,
        100.0*(s.prev_watchers - s.watchers)/NULLIF(s.prev_watchers,0) AS step_drop_pct,
        (s.ep_number = t.paywall_ep) AS is_paywall_step
    FROM stepped s
    JOIN titles t ON t.title_id = s.title_id
    WHERE s.prev_watchers IS NOT NULL AND s.ep_number BETWEEN 2 AND 12
)
SELECT
    CASE WHEN is_paywall_step THEN 'at_paywall_episode' ELSE 'other_early_episode' END AS step_type,
    count(*)                       AS n_steps,
    round(avg(step_drop_pct), 1)   AS avg_step_drop_pct
FROM drops
GROUP BY is_paywall_step
ORDER BY avg_step_drop_pct DESC;

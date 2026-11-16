"""
Build small, tidy 'marts' (aggregated CSVs) from the synthetic data + the real
review labels. These feed (a) the rendered figures and (b) the Power BI model.
Run after generate_data.py and classify_reviews.py.
"""
import os
import duckdb
import pandas as pd

HERE = os.path.dirname(__file__)
SYN = os.path.join(HERE, "..", "database", "data", "synthetic")
PROC = os.path.join(HERE, "..", "data", "reviews_processed")
OUT = os.path.join(HERE, "..", "dashboard", "data")
CUTOFF = "DATE '2026-11-01'"


def con():
    c = duckdb.connect()
    for t in ["users", "titles", "episodes", "sessions", "subscriptions",
              "payments", "consumption_events", "app_events"]:
        c.execute(f"CREATE VIEW {t} AS SELECT * FROM read_csv_auto('{os.path.join(SYN, t+'.csv')}', header=true)")
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    c = con()

    # 1. Funnel -------------------------------------------------------------
    funnel = c.execute(f"""
        WITH fp AS (SELECT user_id FROM consumption_events WHERE seconds_consumed>=30 GROUP BY user_id),
             act AS (SELECT ce.user_id FROM consumption_events ce JOIN users u ON u.user_id=ce.user_id
                     WHERE ce.ts <= u.signup_ts + INTERVAL '72 hours'
                     GROUP BY ce.user_id HAVING count(DISTINCT ce.episode_id)>=3),
             pw AS (SELECT DISTINCT user_id FROM app_events WHERE event_name='paywall_view'),
             sb AS (SELECT DISTINCT user_id FROM subscriptions)
        SELECT 'Signed up' AS stage, count(*) AS users, 1 AS ord FROM users
        UNION ALL SELECT 'Played an episode', count(*), 2 FROM fp
        UNION ALL SELECT 'Activated (3+ in 72h)', count(*), 3 FROM act
        UNION ALL SELECT 'Hit the paywall', count(*), 4 FROM pw
        UNION ALL SELECT 'Subscribed', count(*), 5 FROM sb
        ORDER BY ord
    """).df()
    funnel["pct_of_signup"] = (funnel["users"] / funnel["users"].iloc[0] * 100).round(1)
    funnel.to_csv(os.path.join(OUT, "mart_funnel.csv"), index=False)

    # 2. Retention by genre of first watched title --------------------------
    genre = c.execute(f"""
        WITH activity AS (
            SELECT ce.user_id, (ce.ts::date - u.signup_ts::date) AS d
            FROM consumption_events ce JOIN users u ON u.user_id=ce.user_id
            WHERE ce.seconds_consumed>=30
            GROUP BY ce.user_id, (ce.ts::date - u.signup_ts::date)),
        ft AS (SELECT DISTINCT ON (ce.user_id) ce.user_id, t.genre
               FROM consumption_events ce JOIN episodes e ON e.episode_id=ce.episode_id
               JOIN titles t ON t.title_id=e.title_id ORDER BY ce.user_id, ce.ts),
        m AS (SELECT u.user_id, ft.genre, ({CUTOFF}-u.signup_ts::date) AS obs
              FROM users u JOIN ft ON ft.user_id=u.user_id)
        SELECT m.genre,
               count(*) AS users,
               round(100.0*count(*) FILTER(WHERE a1.user_id IS NOT NULL)/NULLIF(count(*) FILTER(WHERE obs>=1),0),1) AS d1,
               round(100.0*count(*) FILTER(WHERE a7.user_id IS NOT NULL)/NULLIF(count(*) FILTER(WHERE obs>=7),0),1) AS d7,
               round(100.0*count(*) FILTER(WHERE a30.user_id IS NOT NULL)/NULLIF(count(*) FILTER(WHERE obs>=30),0),1) AS d30
        FROM m
        LEFT JOIN activity a1 ON a1.user_id=m.user_id AND a1.d=1
        LEFT JOIN activity a7 ON a7.user_id=m.user_id AND a7.d=7
        LEFT JOIN activity a30 ON a30.user_id=m.user_id AND a30.d=30
        GROUP BY m.genre ORDER BY d1 DESC
    """).df()
    genre.to_csv(os.path.join(OUT, "mart_retention_genre.csv"), index=False)

    # 3. Episode survival by experiment group (the paywall cliff) -----------
    survival = c.execute("""
        WITH ew AS (SELECT e.title_id, e.ep_number, count(DISTINCT ce.user_id) AS w
                    FROM consumption_events ce JOIN episodes e ON e.episode_id=ce.episode_id
                    GROUP BY e.title_id, e.ep_number),
             s AS (SELECT ew.title_id, ew.ep_number, ew.w,
                          FIRST_VALUE(ew.w) OVER (PARTITION BY ew.title_id ORDER BY ew.ep_number) AS w1
                   FROM ew)
        SELECT t.experiment_group, s.ep_number,
               round(avg(100.0*s.w/NULLIF(s.w1,0)),1) AS pct_of_ep1
        FROM s JOIN titles t ON t.title_id=s.title_id
        WHERE t.experiment_group IN ('paywall_ep6','paywall_ep8') AND s.ep_number<=12
        GROUP BY t.experiment_group, s.ep_number
        ORDER BY t.experiment_group, s.ep_number
    """).df()
    survival.to_csv(os.path.join(OUT, "mart_episode_survival.csv"), index=False)

    # 4. UPI payment failure by week ---------------------------------------
    payweek = c.execute("""
        SELECT date_trunc('week', ts)::date AS week,
               count(*) AS attempts,
               round(100.0*count(*) FILTER(WHERE status='failed')/NULLIF(count(*),0),1) AS failure_pct
        FROM payments WHERE method='upi'
        GROUP BY 1 ORDER BY 1
    """).df()
    payweek.to_csv(os.path.join(OUT, "mart_payment_week.csv"), index=False)

    # 5. Paywall-position experiment ---------------------------------------
    exp = c.execute("""
        WITH fpv AS (SELECT DISTINCT ON (user_id) user_id, (props::json->>'title_id')::bigint AS title_id
                     FROM app_events WHERE event_name='paywall_view' ORDER BY user_id, ts),
             a AS (SELECT fpv.user_id, t.experiment_group FROM fpv JOIN titles t ON t.title_id=fpv.title_id
                   WHERE t.experiment_group IN ('paywall_ep6','paywall_ep8')),
             sb AS (SELECT DISTINCT user_id FROM subscriptions)
        SELECT a.experiment_group AS grp, count(*) AS reachers, count(s.user_id) AS subscribers,
               round(100.0*count(s.user_id)/NULLIF(count(*),0),2) AS subscribe_pct
        FROM a LEFT JOIN sb s ON s.user_id=a.user_id GROUP BY a.experiment_group ORDER BY a.experiment_group
    """).df()
    exp.to_csv(os.path.join(OUT, "mart_experiment.csv"), index=False)

    # 6. Monthly stickiness & minutes --------------------------------------
    monthly = c.execute("""
        WITH daily AS (SELECT ts::date d, user_id FROM consumption_events WHERE seconds_consumed>=30 GROUP BY 1,2),
             dau AS (SELECT d, date_trunc('month',d) m, count(*) dau FROM daily GROUP BY 1,2),
             mau AS (SELECT date_trunc('month',ts) m, count(DISTINCT user_id) mau FROM consumption_events
                     WHERE seconds_consumed>=30 GROUP BY 1),
             mins AS (SELECT date_trunc('month',ts) m, round(sum(seconds_consumed)/60.0/count(DISTINCT user_id),1) mpu
                      FROM consumption_events WHERE seconds_consumed>=30 GROUP BY 1)
        SELECT mau.m::date AS month, mau.mau,
               round(avg(dau.dau),0) AS avg_dau,
               round(100.0*avg(dau.dau)/NULLIF(mau.mau,0),1) AS stickiness_pct,
               max(mins.mpu) AS minutes_per_user
        FROM mau JOIN dau ON dau.m=mau.m JOIN mins ON mins.m=mau.m
        GROUP BY mau.m, mau.mau ORDER BY mau.m
    """).df()
    monthly = monthly[monthly["month"].astype(str) < "2026-11-01"]  # drop partial cutoff month
    monthly.to_csv(os.path.join(OUT, "mart_monthly.csv"), index=False)

    # 6b. Format comparison -------------------------------------------------
    fmt = c.execute("""
        SELECT t.format,
               count(DISTINCT ce.user_id) AS users,
               round(sum(ce.seconds_consumed)/60.0/count(DISTINCT ce.user_id),1) AS minutes_per_user
        FROM consumption_events ce JOIN episodes e ON e.episode_id=ce.episode_id
        JOIN titles t ON t.title_id=e.title_id
        WHERE ce.seconds_consumed>=30 GROUP BY t.format ORDER BY minutes_per_user DESC
    """).df()
    fmt.to_csv(os.path.join(OUT, "mart_format.csv"), index=False)

    # 6c. Title leaderboard (top 20 by reach) -------------------------------
    lead = c.execute("""
        SELECT t.title_name, t.genre, t.format,
               count(DISTINCT ce.user_id) AS viewers,
               round(100.0*count(*) FILTER(WHERE ce.completed)/NULLIF(count(*),0),1) AS completion_pct
        FROM consumption_events ce JOIN episodes e ON e.episode_id=ce.episode_id
        JOIN titles t ON t.title_id=e.title_id
        GROUP BY t.title_name, t.genre, t.format
        ORDER BY viewers DESC LIMIT 20
    """).df()
    lead.to_csv(os.path.join(OUT, "mart_title_leaderboard.csv"), index=False)

    # 7. Review marts (REAL data) ------------------------------------------
    themes = pd.read_csv(os.path.join(PROC, "theme_summary.csv"))
    themes.to_csv(os.path.join(OUT, "mart_review_themes.csv"), index=False)
    labeled = pd.read_csv(os.path.join(PROC, "kuku_reviews_labeled.csv"))
    rating = (labeled.groupby(["app", "rating"]).size().reset_index(name="reviews"))
    rating.to_csv(os.path.join(OUT, "mart_review_rating_dist.csv"), index=False)

    print("Marts written to", OUT)
    for f in sorted(os.listdir(OUT)):
        print("  ", f)


if __name__ == "__main__":
    main()

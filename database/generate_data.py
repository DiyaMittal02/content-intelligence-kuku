"""
Micro-drama & Audio Content Intelligence (Kuku) — synthetic data generator.

SYNTHETIC DATA. Nothing here represents real Kuku FM / Kuku TV data. The point
of this generator is to produce a realistic, *reproducible* dataset with a few
deliberately planted "stories" an analyst should be able to detect:

    1. HIGH-HOOK / LOW-RETENTION GENRE
       Thrillers/Horror over-index on D1 (strong first-episode hook) but decay
       fast, so their D30 retention is poor vs Drama/Romance (sticky genres).

    2. PAYMENT-FAILURE SPIKE
       During one calendar week (PAYMENT_SPIKE_WEEK) a UPI gateway incident
       pushes UPI failure rate from ~7% to ~35%, denting that week's conversions.

    3. PAYWALL POSITION EFFECT (simulated A/B)
       Micro-drama titles are split into paywall-at-ep6 vs paywall-at-ep8 groups.
       The later wall lets users watch 2 more free episodes, so they are more
       "invested" and subscribe at a higher rate — moving the wall later recovers
       subscribers at the cost of 2 free episodes.

Usage:
    python database/generate_data.py --users 50000 --seed 42
Output:
    database/data/synthetic/*.csv  (one file per table in schema.sql)
"""

from __future__ import annotations
import argparse
import csv
import json
import os
from datetime import datetime, timedelta

import numpy as np

# --------------------------------------------------------------------------
# Config / constants
# --------------------------------------------------------------------------
SIM_START = datetime(2026, 5, 1)       # start of the 6-month window
SIM_END   = datetime(2026, 11, 1)      # data cutoff ("now")
HORIZON_DAYS = (SIM_END - SIM_START).days

# Planted story #2: the week a UPI gateway incident spikes failures.
PAYMENT_SPIKE_WEEK_START = datetime(2026, 8, 10)
PAYMENT_SPIKE_WEEK_END   = datetime(2026, 8, 17)

LANGUAGES = ["Hindi", "Tamil", "Telugu", "Marathi", "Bengali", "Kannada", "Malayalam", "Gujarati"]
LANG_W    = [0.45,    0.11,    0.11,     0.08,      0.08,      0.07,      0.05,        0.05]

ACQ_CHANNELS = ["organic", "meta_ads", "google_ads", "youtube", "referral", "influencer"]
ACQ_W        = [0.30,      0.24,       0.18,         0.14,      0.08,       0.06]

STATES = ["Uttar Pradesh", "Maharashtra", "Bihar", "Tamil Nadu", "Telangana",
          "West Bengal", "Karnataka", "Rajasthan", "Gujarat", "Madhya Pradesh", "Kerala", "Delhi"]

DEVICE_TIERS = ["low", "mid", "high"]
DEVICE_W     = [0.30, 0.40, 0.30]       # ~70% low/mid

GENRES = ["Thriller", "Horror", "Romance", "Drama", "Comedy", "Mythology", "CrimeSuspense", "Family"]
GENRE_POP = [0.18, 0.10, 0.22, 0.16, 0.10, 0.08, 0.09, 0.07]   # popularity weights

# Planted story #1 — per-genre retention shape.
# base = roughly the day-1 return probability; tau = decay time-constant (days).
# Thriller/Horror: high base, small tau  -> high D1, low D30.
# Romance/Drama:   lower base, large tau -> lower D1, higher D30 (sticky).
GENRE_RETENTION = {
    "Thriller":      (0.80, 4.0),
    "Horror":        (0.74, 5.0),
    "CrimeSuspense": (0.70, 6.0),
    "Comedy":        (0.56, 10.0),
    "Mythology":     (0.54, 15.0),
    "Family":        (0.52, 17.0),
    "Romance":       (0.52, 20.0),
    "Drama":         (0.50, 23.0),
}

PLAN_PRICE = {"trial": 0.0, "monthly": 99.0, "annual": 599.0}
PAY_METHODS = ["upi", "card", "netbanking", "wallet"]
PAY_METHOD_W = [0.70, 0.12, 0.08, 0.10]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def rand_ts_in_day(rng, day_date):
    """Random timestamp within a day, biased to evening/night peaks."""
    # hour distribution: peaks around 8-11pm and a smaller lunch peak.
    hours = np.arange(24)
    weights = np.array([2,1,1,1,1,2,3,4,5,5,6,7,6,5,5,6,7,8,10,12,13,12,8,4], dtype=float)
    weights /= weights.sum()
    h = int(rng.choice(hours, p=weights))
    m = int(rng.integers(0, 60))
    s = int(rng.integers(0, 60))
    return datetime(day_date.year, day_date.month, day_date.day, h, m, s)


def genre_slug(name):
    return name.lower()


# --------------------------------------------------------------------------
# Main generation
# --------------------------------------------------------------------------
def generate(n_users: int, seed: int, out_dir: str):
    rng = np.random.default_rng(seed)
    os.makedirs(out_dir, exist_ok=True)

    # ---- open CSV writers -------------------------------------------------
    def writer(name, header):
        f = open(os.path.join(out_dir, name), "w", newline="", encoding="utf-8")
        w = csv.writer(f)
        w.writerow(header)
        return f, w

    f_users, w_users = writer("users.csv",
        ["user_id","signup_ts","acq_channel","language","state","device_tier","platform"])
    f_titles, w_titles = writer("titles.csv",
        ["title_id","title_name","format","genre","language","n_episodes","paywall_ep","experiment_group"])
    f_eps, w_eps = writer("episodes.csv",
        ["episode_id","title_id","ep_number","duration_sec","is_paid"])
    f_sess, w_sess = writer("sessions.csv",
        ["session_id","user_id","start_ts","end_ts","platform"])
    f_subs, w_subs = writer("subscriptions.csv",
        ["sub_id","user_id","plan","start_ts","end_ts","price","status","renewed"])
    f_pay, w_pay = writer("payments.csv",
        ["payment_id","sub_id","ts","amount","method","status"])
    f_cons, w_cons = writer("consumption_events.csv",
        ["event_id","user_id","episode_id","ts","seconds_consumed","completed"])
    f_app, w_app = writer("app_events.csv",
        ["event_id","user_id","event_name","ts","props"])

    # ---- 1. TITLES + EPISODES --------------------------------------------
    n_titles = max(200, n_users // 150)
    episode_id = 1
    titles = []  # list of dicts for later lookup
    title_genre_list = []
    title_lang_list = []
    # episode_index[title_id] = (first_episode_id, n_episodes, durations list is implicit)
    title_first_ep = {}
    for tid in range(1, n_titles + 1):
        fmt = "microdrama" if rng.random() < 0.6 else "audio"
        genre = rng.choice(GENRES, p=GENRE_POP)
        lang = rng.choice(LANGUAGES, p=LANG_W)
        if fmt == "microdrama":
            n_ep = int(rng.integers(30, 81))
            # planted A/B: split micro-dramas into ep6 / ep8 paywall groups
            if rng.random() < 0.5:
                paywall = 6; grp = "paywall_ep6"
            else:
                paywall = 8; grp = "paywall_ep8"
        else:
            n_ep = int(rng.integers(20, 61))
            paywall = int(rng.integers(5, 11))
            grp = "control"
        title = {"title_id": tid, "format": fmt, "genre": genre, "language": lang,
                 "n_episodes": n_ep, "paywall_ep": paywall, "experiment_group": grp}
        titles.append(title)
        title_genre_list.append(genre)
        title_lang_list.append(lang)
        w_titles.writerow([tid, f"{genre} {fmt.title()} {tid}", fmt, genre, lang, n_ep, paywall, grp])

        title_first_ep[tid] = episode_id
        for ep_num in range(1, n_ep + 1):
            if fmt == "microdrama":
                dur = int(rng.integers(60, 121))
            else:
                dur = int(rng.integers(480, 901))
            w_eps.writerow([episode_id, tid, ep_num, dur, ep_num >= paywall])
            episode_id += 1

    def episode_pk(title_id, ep_number):
        return title_first_ep[title_id] + (ep_number - 1)

    # title popularity for selection
    title_pop = rng.dirichlet(np.ones(n_titles) * 0.6)
    title_genre_arr = np.array(title_genre_list)
    title_lang_arr = np.array(title_lang_list)

    # ---- 2. USERS + behaviour --------------------------------------------
    session_id = 1
    sub_id = 1
    payment_id = 1
    cons_id = 1
    app_id = 1

    for uid in range(1, n_users + 1):
        # signup date, gently growing volume over the window
        day_offset = int(np.clip(rng.triangular(0, HORIZON_DAYS, HORIZON_DAYS), 0, HORIZON_DAYS))
        signup_date = SIM_START + timedelta(days=day_offset)
        signup_ts = rand_ts_in_day(rng, signup_date)

        language = rng.choice(LANGUAGES, p=LANG_W)
        acq = rng.choice(ACQ_CHANNELS, p=ACQ_W)
        state = rng.choice(STATES)
        tier = rng.choice(DEVICE_TIERS, p=DEVICE_W)
        platform = "iOS" if (tier == "high" and rng.random() < 0.35) else "Android"
        w_users.writerow([uid, signup_ts.isoformat(sep=" "), acq, language, state, tier, platform])

        # latent engagement multiplier
        E = float(rng.beta(2.0, 3.0)) * 1.3 + 0.2     # ~0.2 .. 1.5

        # primary genre drives this user's retention curve (story #1)
        primary_genre = rng.choice(GENRES, p=GENRE_POP)
        base, tau = GENRE_RETENTION[primary_genre]

        # how many days we can still observe this user
        obs_days = (SIM_END - signup_date).days
        if obs_days < 0:
            obs_days = 0

        # ---- active days: defines retention (D1/D7/D30) ----
        active_offsets = [0]  # signup day
        for d in range(1, obs_days + 1):
            p = base * np.exp(-d / tau) * min(E, 1.3)
            p = float(np.clip(p, 0.0, 0.95))
            if rng.random() < p:
                active_offsets.append(d)

        # episodes-per-active-day capacity
        per_day_choices = np.array([1, 2, 3])
        per_day_w = np.array([0.5, 0.35, 0.15])
        slots_per_day = [int(rng.choice(per_day_choices, p=per_day_w)) for _ in active_offsets]
        total_slots = sum(slots_per_day)

        # ---- choose titles this user engages with ----
        # Bias selection toward the user's primary genre (so the genre of titles
        # they watch correlates with their retention curve -> story #1 is
        # detectable by grouping retention on watched-title genre) and language.
        n_titles_started = min(6, 1 + int(rng.poisson(1.3)))
        w_sel = title_pop.copy()
        w_sel = w_sel * np.where(title_genre_arr == primary_genre, 6.0, 1.0)
        w_sel = w_sel * np.where(title_lang_arr == language, 2.5, 1.0)
        w_sel = w_sel / w_sel.sum()
        sel = rng.choice(n_titles, size=min(n_titles_started, n_titles),
                         replace=False, p=w_sel)
        chosen = [titles[i] for i in sel]

        subscribed = False
        user_has_session_day = {}
        # queue of (title) to consume in order
        consume_log = []   # (episode_pk, duration, completed, title) to timestamp later
        paywall_views = []  # (title) markers to timestamp

        slots_left = total_slots
        for t in chosen:
            if slots_left <= 0:
                break
            tid = t["title_id"]; n_ep = t["n_episodes"]; paywall = t["paywall_ep"]
            genre = t["genre"]
            g_base, _ = GENRE_RETENTION[genre]
            ep = 1
            episodes_before_wall = 0
            while ep <= n_ep and slots_left > 0:
                # --- PAYWALL GATE (runs BEFORE the episode is consumed) ---
                # paywall_ep is the first PAID episode. A non-subscriber is
                # blocked here: they see the paywall and either subscribe (and
                # then watch) or drop WITHOUT a consumption event for the paid
                # episode. This creates the real cliff AT paywall_ep.
                if ep >= paywall and not subscribed:
                    paywall_views.append(tid)
                    # story #3: more free episodes watched -> more invested -> higher subscribe
                    tier_bonus = {"low": -0.04, "mid": 0.03, "high": 0.12}[tier]
                    p_sub = np.clip(0.06 + 0.018 * episodes_before_wall + tier_bonus
                                    + 0.10 * (min(E, 1.2) - 0.6), 0.0, 0.6)
                    if rng.random() < p_sub:
                        subscribed = True
                        _sub_plan = rng.choice(["trial", "monthly", "annual"], p=[0.55, 0.32, 0.13])
                        # defer subscription/payment record creation until we have a timestamp
                        consume_log.append(("__SUBSCRIBE__", _sub_plan, tid))
                    else:
                        break  # dropped at the wall, no consumption of the paid episode

                # --- CONSUME episode `ep` (free, or paid & subscribed) ---
                comp_p = np.clip(0.55 + 0.35 * min(E, 1.2) - 0.004 * ep, 0.1, 0.97)
                completed = rng.random() < comp_p
                epk = episode_pk(tid, ep)
                dur = 90 if t["format"] == "microdrama" else 690   # nominal duration
                secs = int(dur * (rng.uniform(0.9, 1.0) if completed else rng.uniform(0.05, 0.85)))
                consume_log.append((epk, secs, completed))
                slots_left -= 1
                if ep < paywall:
                    episodes_before_wall += 1

                # continue to next episode?
                cont_p = np.clip(0.88 * min(E, 1.15) - 0.002 * ep, 0.2, 0.96)
                if rng.random() > cont_p:
                    break
                ep += 1

        # ---- assign timestamps across active days & emit rows ----
        # build the day timeline
        day_dates = [signup_date + timedelta(days=off) for off in active_offsets]
        # emit one session per active day
        day_session_ids = []
        for dd in day_dates:
            st = rand_ts_in_day(rng, dd)
            dur_min = int(rng.integers(3, 45))
            et = st + timedelta(minutes=dur_min)
            if et > SIM_END:
                et = SIM_END
            w_sess.writerow([session_id, uid, st.isoformat(sep=" "), et.isoformat(sep=" "), platform])
            w_app.writerow([app_id, uid, "app_open", st.isoformat(sep=" "), "{}"]); app_id += 1
            day_session_ids.append((session_id, st)); session_id += 1

        # distribute consume_log entries across the active days in order
        # flatten slots: day d gets slots_per_day[d] consumption items
        item_idx = 0
        items = consume_log
        for di, (sid, s_start) in enumerate(day_session_ids):
            n_slots = slots_per_day[di]
            placed = 0
            base_ts = s_start
            while placed < n_slots and item_idx < len(items):
                it = items[item_idx]; item_idx += 1
                ev_ts = base_ts + timedelta(minutes=int(rng.integers(0, 40)))
                if ev_ts > SIM_END:
                    ev_ts = SIM_END
                if it[0] == "__SUBSCRIBE__":
                    plan = it[1]
                    price = PLAN_PRICE[plan]
                    end_ts = None
                    if plan == "monthly":
                        end_ts = ev_ts + timedelta(days=30)
                    elif plan == "annual":
                        end_ts = ev_ts + timedelta(days=365)
                    elif plan == "trial":
                        end_ts = ev_ts + timedelta(days=7)
                    renewed = (plan in ("monthly", "annual")) and (rng.random() < 0.45)
                    status = "active" if (end_ts and end_ts > SIM_END) else "expired"
                    w_subs.writerow([sub_id, uid, plan, ev_ts.isoformat(sep=" "),
                                     end_ts.isoformat(sep=" ") if end_ts else "",
                                     f"{price:.2f}", status, renewed])
                    w_app.writerow([app_id, uid, "subscribe_click", ev_ts.isoformat(sep=" "),
                                    json.dumps({"plan": plan})]); app_id += 1
                    # payment (skip for trial price 0, but record a trial auth attempt)
                    method = rng.choice(PAY_METHODS, p=PAY_METHOD_W)
                    # story #2: UPI failure spike in one week
                    in_spike = PAYMENT_SPIKE_WEEK_START <= ev_ts < PAYMENT_SPIKE_WEEK_END
                    fail_p = 0.06
                    if method == "upi" and in_spike:
                        fail_p = 0.40
                    pstatus = "failed" if rng.random() < fail_p else "success"
                    pay_amount = price if price > 0 else 1.0  # trial = Re.1 auth
                    w_pay.writerow([payment_id, sub_id, ev_ts.isoformat(sep=" "),
                                    f"{pay_amount:.2f}", method, pstatus]); payment_id += 1
                    # trial -> paid conversion (metric), as a follow-on monthly sub
                    if plan == "trial" and pstatus == "success" and rng.random() < 0.40:
                        conv_ts = ev_ts + timedelta(days=7)
                        if conv_ts < SIM_END:
                            w_subs.writerow([sub_id + 100000000, uid, "monthly",
                                             conv_ts.isoformat(sep=" "),
                                             (conv_ts + timedelta(days=30)).isoformat(sep=" "),
                                             f"{PLAN_PRICE['monthly']:.2f}", "active", False])
                            cmethod = rng.choice(PAY_METHODS, p=PAY_METHOD_W)
                            w_pay.writerow([payment_id, sub_id + 100000000,
                                            conv_ts.isoformat(sep=" "),
                                            f"{PLAN_PRICE['monthly']:.2f}", cmethod,
                                            "success" if rng.random() > 0.07 else "failed"])
                            payment_id += 1
                    sub_id += 1
                    # this subscribe marker consumed a slot indirectly; don't count as content
                    continue
                else:
                    epk, secs, completed = it
                    w_cons.writerow([cons_id, uid, epk, ev_ts.isoformat(sep=" "),
                                     secs, completed]); cons_id += 1
                    placed += 1

        # emit paywall_view app_events (timestamp near last session)
        if paywall_views and day_session_ids:
            last_ts = day_session_ids[-1][1]
            for tid in paywall_views:
                w_app.writerow([app_id, uid, "paywall_view",
                                (last_ts + timedelta(minutes=int(rng.integers(0, 30)))).isoformat(sep=" "),
                                json.dumps({"title_id": int(tid)})]); app_id += 1

        # sprinkle some discovery events
        for _ in range(int(rng.integers(0, 4))):
            if day_session_ids:
                sid, st = day_session_ids[int(rng.integers(0, len(day_session_ids)))]
                ev = rng.choice(["search", "browse", "share"], p=[0.4, 0.45, 0.15])
                w_app.writerow([app_id, uid, str(ev),
                                (st + timedelta(minutes=int(rng.integers(0, 30)))).isoformat(sep=" "),
                                "{}"]); app_id += 1

        if uid % 10000 == 0:
            print(f"  ...{uid:,} users generated")

    for f in (f_users, f_titles, f_eps, f_sess, f_subs, f_pay, f_cons, f_app):
        f.close()

    print("\nDone. Rough row counts:")
    print(f"  users={n_users:,}  titles={n_titles:,}  "
          f"consumption_events~{cons_id-1:,}  app_events~{app_id-1:,}  "
          f"subscriptions~{sub_id-1:,}  payments~{payment_id-1:,}  sessions~{session_id-1:,}")
    print(f"  Output dir: {out_dir}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate synthetic Kuku content-intelligence data.")
    ap.add_argument("--users", type=int, default=50000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=str,
                    default=os.path.join(os.path.dirname(__file__), "data", "synthetic"))
    args = ap.parse_args()
    print(f"Generating synthetic data: users={args.users:,} seed={args.seed}")
    generate(args.users, args.seed, args.out)

"""Quick validation that the 3 planted patterns are detectable in the generated CSVs.
Run after generate_data.py. Uses pandas only."""
import os
import pandas as pd

D = os.path.join(os.path.dirname(__file__), "data", "synthetic")
users = pd.read_csv(os.path.join(D, "users.csv"), parse_dates=["signup_ts"])
titles = pd.read_csv(os.path.join(D, "titles.csv"))
episodes = pd.read_csv(os.path.join(D, "episodes.csv"))
cons = pd.read_csv(os.path.join(D, "consumption_events.csv"), parse_dates=["ts"])
pay = pd.read_csv(os.path.join(D, "payments.csv"), parse_dates=["ts"])
subs = pd.read_csv(os.path.join(D, "subscriptions.csv"))

# map episode -> title -> genre
ep2title = episodes.set_index("episode_id")["title_id"]
title2genre = titles.set_index("title_id")["genre"]
cons["title_id"] = cons["episode_id"].map(ep2title)
cons["genre"] = cons["title_id"].map(title2genre)

# ---- Story 1: D1/D7/D30 retention by genre (of user's FIRST watched title) ----
first = cons.sort_values("ts").groupby("user_id").first()
first_genre = first["genre"]
act_days = cons.merge(users[["user_id", "signup_ts"]], on="user_id")
act_days["day"] = (act_days["ts"].dt.normalize() - act_days["signup_ts"].dt.normalize()).dt.days
by_user_days = act_days.groupby("user_id")["day"].apply(set)

def ret(days_set, d):
    return 1 if any(abs(x - d) < 1 for x in days_set) else 0

rows = []
for g in sorted(first_genre.unique()):
    us = first_genre[first_genre == g].index
    us = [u for u in us if u in by_user_days.index]
    if not us:
        continue
    d1 = sum(ret(by_user_days[u], 1) for u in us) / len(us)
    d7 = sum(ret(by_user_days[u], 7) for u in us) / len(us)
    d30 = sum(ret(by_user_days[u], 30) for u in us) / len(us)
    rows.append((g, len(us), round(d1*100,1), round(d7*100,1), round(d30*100,1)))
print("\n=== STORY 1: Retention by genre of first watched title (%) ===")
print(f"{'genre':14} {'n':>6} {'D1':>6} {'D7':>6} {'D30':>6}")
for r in sorted(rows, key=lambda x: -x[2]):
    print(f"{r[0]:14} {r[1]:>6} {r[2]:>6} {r[3]:>6} {r[4]:>6}")
print("  EXPECT: Thriller/Horror top on D1 but near-bottom on D30; Drama/Romance opposite.")

# ---- Story 2: UPI failure rate by week ----
pay["week"] = pay["ts"].dt.to_period("W-MON").apply(lambda p: p.start_time.date())
upi = pay[pay["method"] == "upi"].copy()
wk = upi.groupby("week")["status"].apply(lambda s: (s == "failed").mean()*100).round(1)
print("\n=== STORY 2: UPI payment failure rate by week (%) ===")
print(wk.to_string())
print("  EXPECT: one week (~2026-08-10) spikes to ~35% vs ~7% baseline.")

# ---- Story 3: paywall ep6 vs ep8 subscribe rate ----
# "Reached the wall" = the user hit a paywall_view (blocked users do NOT consume
# the paid episode, so reach must be measured from the paywall_view event).
# First-touch assignment: the group of each user's first paywall_view title.
import json as _json
app = pd.read_csv(os.path.join(D, "app_events.csv"), parse_dates=["ts"])
pv = app[app["event_name"] == "paywall_view"].copy()
pv["title_id"] = pv["props"].apply(lambda s: _json.loads(s).get("title_id") if isinstance(s, str) and s.strip().startswith("{") else None)
pv = pv.dropna(subset=["title_id"]).sort_values("ts")
first_pv = pv.groupby("user_id").first()
first_pv["experiment_group"] = first_pv["title_id"].map(titles.set_index("title_id")["experiment_group"])
subs_users = set(subs["user_id"].unique())
print("\n=== STORY 3: subscribe rate among paywall-reachers (first-touch), by group ===")
for grp in ["paywall_ep6", "paywall_ep8"]:
    ru = set(first_pv[first_pv["experiment_group"] == grp].index)
    if not ru:
        continue
    conv = len(ru & subs_users) / len(ru) * 100
    print(f"  {grp:14} reachers={len(ru):>5}  subscribe_rate={conv:.1f}%")
print("  EXPECT: ep8 >= ep6 (more free episodes -> more invested -> higher subscribe).")

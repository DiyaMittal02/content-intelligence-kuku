"""
Fetch a dated, public sample of Google Play reviews for the Kuku apps.

REAL DATA (not synthetic). Uses Google Play's public review endpoint directly
over HTTP. Honesty / privacy rules applied:
  - User names are NOT stored (unnecessary personal data). We keep an opaque
    review_id, the star rating, the review text, the date, app version, and the
    thumbs-up count only.
  - Collection date, source, locale and sample size are logged.
  - A modest sample at a polite request rate; reviews are self-selected (skewed
    to very happy / very unhappy users) and this is noted in the analysis.

Usage:
    python notebooks/fetch_reviews.py
Output:
    data/reviews_raw/<slug>_reviews_raw.csv
    data/reviews_raw/collection_log.md
"""
from __future__ import annotations
import csv, datetime as dt, hashlib, json, os, time, urllib.parse, urllib.request

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "reviews_raw")
APPS = [
    ("com.vlv.aravali",       "Kuku FM", "kuku_fm"),    # audio series
    ("com.vlv.aravali.reels", "Kuku TV", "kuku_tv"),    # micro-dramas
]
PAGES = 6            # ~100 reviews/page
COUNTRY, LANG = "in", "en"


def _call(app_id, token=None):
    tok = "null" if token is None else '"%s"' % token
    inner = '[null,null,[2,2,[100,null,%s],null,[]],["%s",7]]' % (tok, app_id)
    body = "f.req=" + urllib.parse.quote(json.dumps([[["UsvDTd", inner, None, "generic"]]]))
    url = f"https://play.google.com/_/PlayStoreUi/data/batchexecute?hl={LANG}&gl={COUNTRY}"
    req = urllib.request.Request(
        url, data=body.encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                 "User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    payload = json.loads(json.loads(raw[raw.index("\n") + 1:])[0][2])
    return payload[0], (payload[1][1] if payload[1] else None)


def fetch_app(app_id, app_label, slug):
    rows, token, seen = [], None, set()
    for _ in range(PAGES):
        reviews, token = _call(app_id, token)
        for r in reviews:
            rid = r[0]
            if rid in seen:
                continue
            seen.add(rid)
            ts = r[5][0] if r[5] else None
            date = dt.datetime.fromtimestamp(ts, dt.timezone.utc).date().isoformat() if ts else ""
            rows.append({
                # opaque, non-reversible id; no user name stored
                "review_id": hashlib.sha1(rid.encode()).hexdigest()[:16],
                "app": app_label,
                "rating": r[2],
                "review_date": date,
                "app_version": r[10] if len(r) > 10 and r[10] else "",
                "thumbs_up": r[6] if len(r) > 6 and r[6] else 0,
                "text": (r[4] or "").replace("\r", " ").replace("\n", " ").strip(),
            })
        if not token:
            break
        time.sleep(1.0)   # polite
    return rows


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_rows, per_app = [], []
    for app_id, label, slug in APPS:
        rows = fetch_app(app_id, label, slug)
        all_rows += rows
        per_app.append((label, app_id, len(rows)))
        print(f"{label}: {len(rows)} reviews")

    out_csv = os.path.join(OUT_DIR, "kuku_reviews_raw.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["review_id", "app", "rating", "review_date",
                                          "app_version", "thumbs_up", "text"])
        w.writeheader()
        w.writerows(all_rows)

    dates = [r["review_date"] for r in all_rows if r["review_date"]]
    with open(os.path.join(OUT_DIR, "collection_log.md"), "w", encoding="utf-8") as f:
        f.write("# Review collection log\n\n")
        f.write(f"- Collected (UTC): {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}\n")
        f.write("- Source: Google Play public reviews endpoint (store locale "
                f"gl={COUNTRY}, hl={LANG})\n")
        f.write(f"- Sample size: {len(all_rows)} reviews\n")
        f.write(f"- Date range: {min(dates)} to {max(dates)}\n")
        f.write("- Fields kept: review_id (hashed), app, rating, review_date, "
                "app_version, thumbs_up, text\n")
        f.write("- Fields deliberately dropped: user name / profile (personal data)\n")
        f.write("- Caveat: Play Store reviews are self-selected and skew to very "
                "satisfied or very dissatisfied users.\n\n")
        f.write("| app | package | reviews |\n|---|---|---|\n")
        for label, pkg, n in per_app:
            f.write(f"| {label} | {pkg} | {n} |\n")
    print(f"\nSaved {len(all_rows)} reviews -> {out_csv}")


if __name__ == "__main__":
    main()

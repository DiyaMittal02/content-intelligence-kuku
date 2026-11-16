"""
Rule-based theme tagging for the collected Kuku reviews (REAL data).

Method (stated honestly in the case study):
  - Lowercase the review text; match curated keyword sets per theme.
  - Multi-label: a review can carry several themes (e.g. payments + pricing).
  - Keyword rules are transparent and spot-checkable (not a black-box model).
  - Non-English / very short reviews that match nothing are kept as
    'uncategorised' and that share is reported, not hidden.

Outputs:
  data/reviews_processed/kuku_reviews_labeled.csv
  data/reviews_processed/theme_summary.csv
"""
import os
import pandas as pd

RAW = os.path.join(os.path.dirname(__file__), "..", "data", "reviews_raw", "kuku_reviews_raw.csv")
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "reviews_processed")

# Theme -> keyword set (substring match on lowercased text).
THEMES = {
    "payments_billing": [
        "autopay", "auto pay", "auto-pay", "deduct", "debited", "debit", "refund",
        "charged", "charge", "scam", "fraud", "cheat", "money", "rupee", " rs", "₹",
        "without permission", "without my", "unauthor", "renew", "cancel sub",
        "cancellation", "return my", "paisa", "paise", "payment", "deducation",
    ],
    "pricing": [
        "expensive", "costly", "too high", "price is high", "high price", "afford",
        "overpriced", "discount", "yearly", "too much", "costs", "499", "699", "costly",
    ],
    "content_quality": [
        "story", "stories", "series", "episode", "content", "boring", "repeat",
        "repetitive", "narration", "voice", "audiobook", " book", "incomplete",
        "ending", "drama", "cliffhang", "same story", "quality of",
    ],
    "ads": ["advertisement", "advertis", " ads", " ad ", "too many ad"],
    "playback_tech": [
        "buffer", "loading", "not loading", "offline", "download", "stuck", "lag",
        "not working", "stopped working", "audio quality", "sound quality", "hang",
    ],
    "app_stability": [
        "crash", "crashes", "bug", "error", "log in", "login", "otp", "sign in",
        "won't open", "not opening", "freez", "glitch",
    ],
    "language": [
        "language", "hindi", "tamil", "telugu", "kannada", "marathi", "bengali",
        "gujarati", "malayalam", "punjabi", "regional", "dubbed", "dubbing",
    ],
    "discovery_nav": [
        "search", "find", "recommend", "category", "categories", "filter",
        "interface", " ui ", "navigation", "hard to find",
    ],
    "support": [
        "customer care", "customer service", "support", "no response", "no reply",
        "contact", "help desk", "helpline", "no one responds",
    ],
    "praise": [
        "good app", "nice app", "super", "best app", "love", "awesome", "excellent",
        "amazing", "superb", "wonderful", "very nice", "helpful", "great app", "best",
    ],
}


def tag(text: str):
    t = f" {str(text).lower()} "
    hits = [theme for theme, kws in THEMES.items() if any(k in t for k in kws)]
    return hits


def main():
    os.makedirs(OUT, exist_ok=True)
    df = pd.read_csv(RAW)
    df["text"] = df["text"].fillna("")
    df["themes"] = df["text"].apply(tag)
    df["sentiment"] = pd.cut(df["rating"], bins=[0, 2, 3, 5],
                             labels=["negative", "neutral", "positive"])
    df["uncategorised"] = df["themes"].apply(lambda x: len(x) == 0)

    # explode to one row per (review, theme) for theme-level stats
    ex = df.explode("themes")
    summary = (ex.dropna(subset=["themes"])
                 .groupby("themes")
                 .agg(mentions=("review_id", "count"),
                      avg_rating=("rating", "mean"))
                 .reset_index()
                 .sort_values("mentions", ascending=False))
    summary["share_of_reviews_pct"] = (summary["mentions"] / len(df) * 100).round(1)
    summary["avg_rating"] = summary["avg_rating"].round(2)

    df_out = df.copy()
    df_out["themes"] = df_out["themes"].apply(lambda x: "|".join(x))
    df_out.to_csv(os.path.join(OUT, "kuku_reviews_labeled.csv"), index=False)
    summary.to_csv(os.path.join(OUT, "theme_summary.csv"), index=False)

    print(f"Labeled {len(df)} reviews. Uncategorised: "
          f"{df['uncategorised'].mean()*100:.1f}%")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()

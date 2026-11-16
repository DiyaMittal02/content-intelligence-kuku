"""
Render the case-study / dashboard figures from the marts. Editorial style, no
gradients, no emoji, direct value labels. Outputs PNGs to reports/figures/.
"""
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

import chart_style as cs

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "dashboard", "data")
FIG = os.path.join(HERE, "..", "reports", "figures")
cs.apply()


def _save(fig, name):
    os.makedirs(FIG, exist_ok=True)
    fig.savefig(os.path.join(FIG, name), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("  wrote", name)


def m(f):
    return pd.read_csv(os.path.join(DATA, f))


# 1. Activation funnel ------------------------------------------------------
def fig_funnel():
    d = m("mart_funnel.csv")
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    y = range(len(d))[::-1]
    ax.barh(list(y), d["users"], color=cs.TEAL, height=0.62, zorder=3)
    for yi, (_, r) in zip(y, d.iterrows()):
        ax.text(r["users"] + d["users"].max() * 0.012, yi,
                f"{int(r['users']):,}  ·  {r['pct_of_signup']:.0f}%",
                va="center", ha="left", fontsize=9.5, color=cs.INK)
    ax.set_yticks(list(y))
    ax.set_yticklabels(d["stage"], fontsize=10, color=cs.INK)
    ax.set_xlim(0, d["users"].max() * 1.22)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{int(x/1000)}k"))
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    cs.titled(ax, "Where new users fall out of the funnel",
              "Synthetic data · 50,000 signups over 6 months · share of signups at each step")
    cs.source_note(fig, "Source: synthetic model, sql/02_activation_funnel.sql. Not real Kuku data.")
    _save(fig, "fig_funnel.png")


# 2. Retention by genre: D1 -> D30 dumbbell --------------------------------
def fig_retention_genre():
    d = m("mart_retention_genre.csv").sort_values("d1")
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    y = range(len(d))
    ax.hlines(list(y), d["d30"], d["d1"], color=cs.MUTED, lw=1.4, zorder=2)
    ax.scatter(d["d1"], list(y), color=cs.TEAL, s=55, zorder=3, label="D1 retention")
    ax.scatter(d["d30"], list(y), color=cs.VERMILLION, s=55, zorder=3, label="D30 retention")
    for yi, (_, r) in zip(y, d.iterrows()):
        ax.text(r["d1"] + 0.6, yi, f"{r['d1']:.0f}%", va="center", fontsize=8.5, color=cs.TEAL)
        ax.text(r["d30"] - 0.6, yi, f"{r['d30']:.1f}%", va="center", ha="right",
                fontsize=8.5, color=cs.VERMILLION)
    ax.set_yticks(list(y)); ax.set_yticklabels(d["genre"], fontsize=10, color=cs.INK)
    ax.set_xlim(-2, d["d1"].max() * 1.15)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    ax.legend(loc="center", bbox_to_anchor=(0.5, 0.5), ncol=1)
    cs.titled(ax, "High-hook genres win day 1 but lose the month",
              "Synthetic data · retention by genre of first watched title · Thriller tops D1, bottoms D30")
    cs.source_note(fig, "Source: synthetic model, sql/04_retention_cohorts.sql. Not real Kuku data.")
    _save(fig, "fig_retention_genre.png")


# 3. Paywall cliff: survival curves by experiment group --------------------
def fig_paywall_cliff():
    d = m("mart_episode_survival.csv")
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    styles = {"paywall_ep6": (cs.VERMILLION, "Paywall at episode 6", 6),
              "paywall_ep8": (cs.TEAL, "Paywall at episode 8", 8)}
    for grp, (col, lab, wall) in styles.items():
        g = d[d["experiment_group"] == grp]
        ax.plot(g["ep_number"], g["pct_of_ep1"], color=col, lw=2.2, marker="o",
                markersize=4, label=lab, zorder=3)
        ax.axvline(wall, color=col, lw=1, ls=":", alpha=0.6, zorder=1)
    ax.set_xlabel("Episode number"); ax.set_ylabel("Viewers remaining")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_xticks(range(1, 13))
    ax.legend(loc="upper right")
    cs.titled(ax, "The paywall, not the content, is the cliff",
              "Synthetic data · share of a title's episode-1 viewers still watching, by paywall position")
    cs.source_note(fig, "Source: synthetic model, sql/05_episode_dropoff.sql. Not real Kuku data.")
    _save(fig, "fig_paywall_cliff.png")


# 4. UPI failure spike ------------------------------------------------------
def fig_payment_spike():
    d = m("mart_payment_week.csv")
    d["week"] = pd.to_datetime(d["week"])
    fig, ax = plt.subplots(figsize=(7.4, 3.4))
    ax.plot(d["week"], d["failure_pct"], color=cs.MUTED, lw=1.8, zorder=2)
    spike = d.loc[d["failure_pct"].idxmax()]
    ax.scatter([spike["week"]], [spike["failure_pct"]], color=cs.VERMILLION, s=70, zorder=4)
    ax.annotate(f"Week of {spike['week'].date():%d %b}: {spike['failure_pct']:.0f}%",
                xy=(spike["week"], spike["failure_pct"]),
                xytext=(spike["week"], spike["failure_pct"] + 9),
                fontsize=9.5, color=cs.VERMILLION, ha="center",
                arrowprops=dict(arrowstyle="-", color=cs.VERMILLION, lw=1))
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_ylabel("UPI payment failure rate")
    ax.set_ylim(0, spike["failure_pct"] + 16)
    cs.titled(ax, "A one-week UPI payment incident",
              "Synthetic data · weekly UPI failure rate · a gateway spike dents that week's conversions")
    cs.source_note(fig, "Source: synthetic model, sql/07_monetisation.sql. Not real Kuku data.")
    _save(fig, "fig_payment_spike.png")


# 5. Paywall-position experiment readout -----------------------------------
def fig_experiment():
    d = m("mart_experiment.csv")
    d["half"] = (1.96 * ((d["subscribe_pct"]/100*(1-d["subscribe_pct"]/100))/d["reachers"])**0.5) * 100
    labels = {"paywall_ep6": "Paywall\nat ep 6", "paywall_ep8": "Paywall\nat ep 8"}
    fig, ax = plt.subplots(figsize=(5.0, 3.8))
    x = range(len(d))
    colors = [cs.VERMILLION, cs.TEAL]
    ax.bar(list(x), d["subscribe_pct"], width=0.5, color=colors,
           yerr=d["half"], capsize=5, zorder=3, error_kw=dict(ecolor=cs.SECOND, lw=1.2))
    for xi, (_, r) in zip(x, d.iterrows()):
        ax.text(xi, r["subscribe_pct"] + r["half"] + 0.8, f"{r['subscribe_pct']:.1f}%",
                ha="center", fontsize=10.5, color=cs.INK, fontweight="bold")
    lift = d["subscribe_pct"].iloc[1] - d["subscribe_pct"].iloc[0]
    ax.set_xticks(list(x)); ax.set_xticklabels([labels[g] for g in d["grp"]], fontsize=10)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_ylim(0, d["subscribe_pct"].max() * 1.35)
    ax.set_ylabel("Subscribe rate among wall-reachers")
    cs.titled(ax, f"Later paywall lifts subscribers +{lift:.1f}pp",
              "Synthetic A/B · 95% CI shown · at a cost of 2 free episodes")
    cs.source_note(fig, "Source: synthetic model, sql/09_experiment_readout.sql. Not real Kuku data.")
    _save(fig, "fig_experiment.png")


# 6. Review themes (REAL) ---------------------------------------------------
def fig_review_themes():
    d = m("mart_review_themes.csv")
    d = d[d["themes"] != "praise"].sort_values("mentions").tail(8)
    name = {"payments_billing": "Payments & autopay", "content_quality": "Content quality",
            "pricing": "Pricing", "playback_tech": "Playback / tech", "ads": "Ads",
            "support": "Customer support", "discovery_nav": "Discovery & navigation",
            "app_stability": "App stability", "language": "Language"}
    labels = [name.get(t, t) for t in d["themes"]]
    # colour by avg rating: low rating (a pain) in vermillion, higher in muted teal
    colors = [cs.VERMILLION if r < 2.5 else cs.TEAL for r in d["avg_rating"]]
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    y = range(len(d))
    ax.barh(list(y), d["share_of_reviews_pct"], color=colors, height=0.62, zorder=3)
    for yi, (_, r) in zip(y, d.iterrows()):
        ax.text(r["share_of_reviews_pct"] + 0.2, yi,
                f"{r['share_of_reviews_pct']:.1f}%   (avg {r['avg_rating']:.1f}★)".replace("★", ""),
                va="center", fontsize=9, color=cs.INK)
    ax.set_yticks(list(y)); ax.set_yticklabels(labels, fontsize=10, color=cs.INK)
    ax.set_xlim(0, d["share_of_reviews_pct"].max() * 1.35)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    cs.titled(ax, "What 1,200 real Play Store reviews complain about",
              "Real public reviews (Kuku FM + Kuku TV, Aug–Nov 2026) · red = avg rating below 2.5")
    cs.source_note(fig, "Source: Google Play public reviews, labelled by keyword rules. Real data; see collection_log.md.")
    _save(fig, "fig_review_themes.png")


# 7. Rating distribution by app (REAL) --------------------------------------
def fig_rating_dist():
    d = m("mart_review_rating_dist.csv")
    piv = d.pivot(index="rating", columns="app", values="reviews").fillna(0)
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    x = piv.index.values
    w = 0.38
    ax.bar(x - w/2, piv["Kuku FM"], width=w, color=cs.STEEL, label="Kuku FM (audio)", zorder=3)
    ax.bar(x + w/2, piv["Kuku TV"], width=w, color=cs.GOLD, label="Kuku TV (micro-drama)", zorder=3)
    ax.set_xticks([1, 2, 3, 4, 5]); ax.set_xlabel("Star rating")
    ax.set_ylabel("Reviews in sample")
    ax.legend(loc="upper center")
    cs.titled(ax, "Reviews are strongly polarised",
              "Real public reviews · 600 per app · most are 1-star or 5-star")
    cs.source_note(fig, "Source: Google Play public reviews, India locale. Real data.")
    _save(fig, "fig_rating_dist.png")


if __name__ == "__main__":
    for fn in [fig_funnel, fig_retention_genre, fig_paywall_cliff, fig_payment_spike,
               fig_experiment, fig_review_themes, fig_rating_dist]:
        fn()
    print("All figures rendered to", FIG)

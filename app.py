"""
Kuku Content Intelligence — interactive product teardown + analytics dashboard.
Streamlit + DuckDB + Plotly.

- Product teardown tab: real company facts (sourced), the real Kuku FM / Kuku TV
  app icons and Play/App-Store screenshots, business model, competitive snapshot.
- Analytics tabs: synthetic product metrics queried live from generated CSVs with
  working filters; the Voice-of-customer tab uses REAL Play Store reviews.

Brand chrome uses Kuku's real crimson (sampled from the app icon, #E41824) on a
near-black UI, matching the app. No gradients, no emoji. Real data only.

Run:  streamlit run app.py
"""
import os
import io
import base64
import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SYN = os.path.join(HERE, "database", "data", "synthetic")
PROC = os.path.join(HERE, "data", "reviews_processed")
ASSETS = os.path.join(HERE, "dashboard", "assets")
CUTOFF = "DATE '2026-11-01'"

st.set_page_config(page_title="Kuku Content Intelligence",
                   layout="wide", initial_sidebar_state="expanded")

# --- palette: Kuku brand red + a distinguishable chart set ------------------
KUKU = "#E8222C"      # brand crimson (sampled from the real app icon #E41824)
KUKU_DK = "#B4151C"
TEAL, ROSE, BLUE, AMBER, VIOLET, PINK = (
    "#13b5a6", KUKU, "#4c8dff", "#f6a623", "#9b6cf2", "#f45d9c")

LIGHT = dict(
    bg="#f6f6f8", panel="#ffffff", elev="#ffffff", border="#e5e3e8",
    ink="#15121a", second="#514c58", muted="#8a8594", grid="#eeecf1",
)
DARK = dict(
    bg="#0e0f13", panel="#17191f", elev="#20232c", border="#2a2d36",
    ink="#f2f0f4", second="#aab0bd", grid="#242730", muted="#6d7480",
)


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------
@st.cache_resource
def get_con():
    con = duckdb.connect(database=":memory:")
    for t in ["users", "titles", "episodes", "sessions", "subscriptions",
              "payments", "consumption_events", "app_events"]:
        p = os.path.join(SYN, f"{t}.csv")
        con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv_auto('{p}', header=true)")
    return con


@st.cache_data(show_spinner=False)
def q(sql: str) -> pd.DataFrame:
    return get_con().execute(sql).df()


@st.cache_data(show_spinner=False)
def b64png(path: str, size=None) -> str:
    """Load an image, re-encode to PNG, return a data URI (safe inline)."""
    try:
        im = Image.open(path).convert("RGBA")
        if size:
            im.thumbnail((size, size))
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def asset(name):
    return os.path.join(ASSETS, name)


def synthetic_ready() -> bool:
    return os.path.exists(os.path.join(SYN, "users.csv"))


def where_users(langs, channels, tiers) -> str:
    conds = []
    if langs:
        conds.append("language IN ({})".format(",".join(f"'{x}'" for x in langs)))
    if channels:
        conds.append("acq_channel IN ({})".format(",".join(f"'{x}'" for x in channels)))
    if tiers:
        conds.append("device_tier IN ({})".format(",".join(f"'{x}'" for x in tiers)))
    return ("WHERE " + " AND ".join(conds)) if conds else ""


# ---------------------------------------------------------------------------
# Theme toggle
# ---------------------------------------------------------------------------
if "dark" not in st.session_state:
    st.session_state.dark = True  # Kuku's app is dark; match it

with st.sidebar:
    st.session_state.dark = st.toggle("Dark mode", value=st.session_state.dark)

P = DARK if st.session_state.dark else LIGHT


# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------
st.markdown(f"""
<style>
:root {{
  --bg:{P['bg']}; --panel:{P['panel']}; --elev:{P['elev']}; --border:{P['border']};
  --ink:{P['ink']}; --second:{P['second']}; --muted:{P['muted']};
  --brand:{KUKU}; --brand-dk:{KUKU_DK}; --blue:{BLUE}; --amber:{AMBER};
}}
.stApp {{ background-color: var(--bg); }}
.block-container {{ padding-top: 1.8rem; max-width: 1340px; }}
[data-testid="stHeader"] {{ background: transparent; }}
section[data-testid="stSidebar"] {{ background-color: var(--panel);
  border-right:1px solid var(--border); }}
section[data-testid="stSidebar"] * {{ color: var(--ink); }}
.stApp, .stApp p, .stApp label, .stApp li {{ color: var(--ink); }}

/* rounded, bordered images */
div[data-testid="stImage"] img {{ border-radius:14px; border:1px solid var(--border); }}

/* brand header */
.brandbar {{ display:flex; align-items:center; gap:14px; }}
.brandbar img {{ width:46px; height:46px; border-radius:11px;
  box-shadow:0 2px 10px rgba(228,24,36,.35); }}
.wordmark {{ font-size:1.5rem; font-weight:800; letter-spacing:-.02em;
  color:var(--ink); line-height:1; }}
.wordmark .r {{ color:var(--brand); }}
.submark {{ color:var(--second); font-size:.86rem; margin-top:2px; }}
.badge {{ display:inline-flex; align-items:center; gap:.4rem; font-size:.72rem;
  font-weight:700; color:var(--brand);
  border:1px solid color-mix(in srgb, var(--brand) 40%, var(--border));
  background: color-mix(in srgb, var(--brand) 12%, transparent);
  padding:.3rem .62rem; border-radius:999px; }}
.pulse {{ width:7px;height:7px;border-radius:50%;background:var(--brand);
  display:inline-block;box-shadow:0 0 0 0 rgba(232,34,44,.6);
  animation:pulse 1.8s infinite; }}
@keyframes pulse {{ 0%{{box-shadow:0 0 0 0 rgba(232,34,44,.5)}}
  70%{{box-shadow:0 0 0 7px rgba(232,34,44,0)}} 100%{{box-shadow:0 0 0 0 rgba(232,34,44,0)}} }}

/* hero teardown card */
.hero {{ background:var(--panel); border:1px solid var(--border);
  border-left:5px solid var(--brand); border-radius:16px;
  padding:20px 22px; display:flex; gap:20px; align-items:center; }}
.hero img.app {{ width:92px;height:92px;border-radius:20px;
  box-shadow:0 6px 22px rgba(228,24,36,.35); border:none; }}
.hero h2 {{ margin:0; font-size:1.5rem; font-weight:800; color:var(--ink);
  letter-spacing:-.02em; }}
.hero p {{ margin:.25rem 0 0; color:var(--second); font-size:.95rem; }}

/* stat chips */
.chips {{ display:flex; flex-wrap:wrap; gap:10px; margin:14px 0 2px; }}
.chip {{ background:var(--panel); border:1px solid var(--border);
  border-radius:12px; padding:10px 14px; min-width:120px; }}
.chip b {{ display:block; font-size:1.2rem; font-weight:800; color:var(--brand);
  font-variant-numeric:tabular-nums; letter-spacing:-.01em; }}
.chip span {{ font-size:.72rem; color:var(--muted); }}

/* section heads */
.sec {{ font-size:.78rem; font-weight:700; letter-spacing:.08em;
  text-transform:uppercase; color:var(--muted); margin:1.4rem 0 .5rem; }}

/* model cards */
.mgrid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }}
@media (max-width:1000px){{ .mgrid {{ grid-template-columns:1fr; }} }}
.mbox {{ background:var(--panel); border:1px solid var(--border);
  border-top:3px solid var(--brand); border-radius:14px; padding:16px; }}
.mbox h4 {{ margin:.1rem 0 .4rem; font-size:1rem; color:var(--ink); }}
.mbox p {{ margin:0; color:var(--second); font-size:.86rem; line-height:1.5; }}

/* KPI cards */
.kpi-grid {{ display:grid; grid-template-columns:repeat(5,1fr); gap:14px; }}
@media (max-width:1100px){{ .kpi-grid {{ grid-template-columns:repeat(2,1fr); }} }}
.kpi {{ background:var(--panel); border:1px solid var(--border);
  border-radius:14px; padding:16px; position:relative; overflow:hidden; }}
.kpi::before {{ content:""; position:absolute; left:0; top:0; bottom:0; width:4px;
  background:var(--ac); }}
.kpi .lab {{ font-size:.72rem; font-weight:600; letter-spacing:.03em;
  text-transform:uppercase; color:var(--muted); }}
.kpi .val {{ font-size:1.9rem; font-weight:800; color:var(--ink);
  margin-top:.25rem; font-variant-numeric:tabular-nums; letter-spacing:-.02em; }}
.kpi .sub {{ font-size:.78rem; color:var(--second); margin-top:.15rem; }}

/* insight callout */
.insight {{ background:var(--panel); border:1px solid var(--border);
  border-left:4px solid var(--ac); border-radius:12px; padding:14px 16px;
  margin:.5rem 0 1rem; }}
.insight .k {{ font-size:.7rem; font-weight:700; letter-spacing:.06em;
  text-transform:uppercase; color:var(--ac); }}
.insight .t {{ color:var(--ink); font-size:.98rem; margin-top:.2rem; line-height:1.45; }}
.note {{ color:var(--muted); font-size:.8rem; margin:.2rem 0 .8rem; }}

/* tabs */
.stTabs [data-baseweb="tab-list"] {{ gap:4px; border-bottom:1px solid var(--border); }}
.stTabs [data-baseweb="tab"] {{ color:var(--muted); font-weight:600;
  background:transparent; border-radius:8px 8px 0 0; padding:.35rem .9rem; }}
.stTabs [aria-selected="true"] {{ color:var(--ink);
  border-bottom:2px solid var(--brand); }}

/* custom table */
.ktab {{ width:100%; border-collapse:collapse; font-size:.85rem;
  font-variant-numeric:tabular-nums; }}
.ktab th {{ text-align:left; color:var(--muted); font-weight:600; font-size:.7rem;
  text-transform:uppercase; letter-spacing:.04em; padding:8px 10px;
  border-bottom:1px solid var(--border); }}
.ktab td {{ padding:9px 10px; border-bottom:1px solid var(--border); color:var(--ink); }}
.ktab tr:hover td {{ background:color-mix(in srgb, var(--brand) 8%, transparent); }}
.ktab .num {{ text-align:right; }}
.bar-wrap {{ background:var(--border); border-radius:6px; height:7px; width:90px;
  display:inline-block; vertical-align:middle; overflow:hidden; }}
.bar-fill {{ height:7px; border-radius:6px; background:var(--brand); display:block; }}
.pill {{ font-size:.68rem; font-weight:600; padding:.12rem .5rem; border-radius:999px;
  background:color-mix(in srgb, var(--blue) 16%, transparent); color:var(--ink); }}
blockquote {{ border-left:3px solid var(--brand); color:var(--second);
  padding:.2rem 0 .2rem 1rem; margin:.4rem 0; }}
hr {{ border-color:var(--border); }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def kpi_row(items):
    cells = "".join(
        f'<div class="kpi" style="--ac:{ac}"><div class="lab">{lab}</div>'
        f'<div class="val">{val}</div><div class="sub">{sub}</div></div>'
        for lab, val, sub, ac in items)
    st.markdown(f'<div class="kpi-grid">{cells}</div>', unsafe_allow_html=True)


def insight(kicker, html, accent=KUKU):
    st.markdown(f'<div class="insight" style="--ac:{accent}"><div class="k">{kicker}</div>'
                f'<div class="t">{html}</div></div>', unsafe_allow_html=True)


def note(txt):
    st.markdown(f'<div class="note">{txt}</div>', unsafe_allow_html=True)


def sec(txt):
    st.markdown(f'<div class="sec">{txt}</div>', unsafe_allow_html=True)


def style(fig, title, subtitle="", height=360):
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>" + (
            f"<br><span style='font-size:12px;color:{P['second']}'>{subtitle}</span>"
            if subtitle else ""),
            x=0, xanchor="left", font=dict(size=16, color=P["ink"])),
        font=dict(family="Segoe UI, DejaVu Sans, Arial", size=13, color=P["ink"]),
        paper_bgcolor=P["panel"], plot_bgcolor=P["panel"],
        margin=dict(l=10, r=20, t=66, b=28), height=height,
        hoverlabel=dict(bgcolor=P["elev"], font_color=P["ink"], bordercolor=P["border"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)", font=dict(color=P["second"])),
        xaxis=dict(gridcolor=P["grid"], zeroline=False, linecolor=P["grid"],
                   tickfont=dict(color=P["second"])),
        yaxis=dict(gridcolor=P["grid"], zeroline=False, linecolor=P["grid"],
                   tickfont=dict(color=P["second"])),
    )
    return fig


def fmt(n):
    return f"{int(round(n)):,}"


SYN_NOTE = "Synthetic data for demonstration — a reproducible model, not Kuku's real performance."
FM_ICON = b64png(asset("kuku_fm_icon.png"))
LOGO_IMG = f'<img src="{FM_ICON}">' if FM_ICON else ""
HERO_IMG = f'<img class="app" src="{FM_ICON}">' if FM_ICON else ""


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
hl, hr = st.columns([5, 1])
with hl:
    st.markdown(
        f'<div class="brandbar">{LOGO_IMG}'
        '<div><div class="wordmark">Kuku <span class="r">Content Intelligence</span></div>'
        '<div class="submark">Micro-drama &amp; audio product teardown · '
        'Diya Mittal (ex-Pocket FM)</div></div></div>', unsafe_allow_html=True)
with hr:
    st.markdown('<div style="text-align:right;padding-top:.7rem">'
                '<span class="badge"><span class="pulse"></span>Live model</span></div>',
                unsafe_allow_html=True)

if not synthetic_ready():
    st.warning("Synthetic data not found. Run "
               "`python database/generate_data.py --users 50000 --seed 42` first.")
    st.stop()

langs = q("SELECT DISTINCT language FROM users ORDER BY 1")["language"].tolist()
channels = q("SELECT DISTINCT acq_channel FROM users ORDER BY 1")["acq_channel"].tolist()
tiers = ["low", "mid", "high"]

with st.sidebar:
    st.header("Filters")
    st.caption("Apply to the synthetic product-metric tabs. The teardown and reviews "
               "tabs use real public data and are not filtered.")
    f_lang = st.multiselect("Language", langs, default=[])
    f_chan = st.multiselect("Acquisition channel", channels, default=[])
    f_tier = st.multiselect("Device tier", tiers, default=[])

W = where_users(f_lang, f_chan, f_tier)

tabT, tab1, tab2, tab3, tab4 = st.tabs(
    ["Product teardown", "Overview", "Funnel & retention", "Content",
     "Voice of customer (real reviews)"])


# ---------------------------------------------------------------------------
# Tab 0 — Product teardown (real facts + real imagery)
# ---------------------------------------------------------------------------
with tabT:
    st.markdown(
        f'<div class="hero">{HERO_IMG}'
        '<div><h2>Kuku FM — Product Teardown</h2>'
        '<p>India\'s largest audio &amp; micro-drama subscription platform. '
        'Vernacular-first, freemium, tier-2/3 India. '
        'This is an independent analysis — not affiliated with Kuku FM.</p></div></div>',
        unsafe_allow_html=True)

    st.markdown(
        '<div class="chips">'
        '<div class="chip"><b>2018</b><span>Founded · IIT Jodhpur trio</span></div>'
        '<div class="chip"><b>$550M</b><span>Valuation · Oct 2025</span></div>'
        '<div class="chip"><b>10M+</b><span>Paying subscribers</span></div>'
        '<div class="chip"><b>&#8377;242 Cr</b><span>FY25 revenue · +175% YoY</span></div>'
        '<div class="chip"><b>10+</b><span>Indian languages</span></div>'
        '<div class="chip"><b>150k+</b><span>Hours of content</span></div>'
        '<div class="chip"><b>$156M</b><span>Total funding raised</span></div>'
        '</div>', unsafe_allow_html=True)
    st.caption("Company figures are real and sourced (see Sources, bottom). "
               "Product metrics in the other tabs are synthetic.")

    sec("The product — two apps, one playbook")
    st.markdown("**Kuku FM** — long-form audio: audiobooks, self-help, finance, "
                "history, religion and original audio drama.")
    cfm = st.columns(3)
    for col, f, cap in zip(cfm, ["fm_shot1.png", "fm_shot2.png", "fm_shot3.png"],
                           ["Home & categories", "Series player", "Library / plans"]):
        if os.path.exists(asset(f)):
            col.image(asset(f), caption=cap, width="stretch")

    st.markdown("**Kuku TV** — the micro-drama video spin-off (launched early 2025); "
                "hit #1 on India's App Store within four months.")
    ctv = st.columns(3)
    for col, f, cap in zip(ctv, ["tv_shot1.png", "tv_shot2.png", "tv_shot3.png"],
                           ["Vertical reels feed", "Episode unlock", "Drama catalogue"]):
        if os.path.exists(asset(f)):
            col.image(asset(f), caption=cap, width="stretch")

    sec("How the business works")
    st.markdown(
        '<div class="mgrid">'
        '<div class="mbox"><h4>Freemium → subscription</h4><p>A slice of every series '
        'is free; the rest sits behind a paywall. Full access is &#8377;99/month or '
        '&#8377;899/year, often sold via a &#8377;1 three-day trial. <b>Kuku Coins</b> '
        'let price-sensitive users unlock single episodes without subscribing.</p></div>'
        '<div class="mbox"><h4>Content engine</h4><p>A large originals slate plus '
        'licensed audiobooks across 10+ languages, now scaled with AI-assisted '
        'production. Serialised, cliffhanger-driven storytelling — not Western-style '
        'podcasts — is what made retention work after the 2018 pivot.</p></div>'
        '<div class="mbox"><h4>Growth loop</h4><p>Vernacular-first, aimed at tier-2/3 '
        'India that global players under-serve. Low price, high volume, heavy '
        'performance marketing. Kuku TV extends the same catalogue into short video '
        'to capture the micro-drama wave.</p></div>'
        '</div>', unsafe_allow_html=True)

    sec("What the data in this dashboard shows")
    insight("Strength",
            "Engagement hooks work: high-hook genres pull strong <b>day-1 retention</b>, "
            "and the episode-survival curve shows the <b>content holds attention</b> — "
            "people drop at the paywall, not because the story stalls. "
            "(See Funnel &amp; Content tabs.)", TEAL)
    insight("Risk #1 — monetisation friction",
            "In <b>1,200 real Play Store reviews</b>, <b>payments &amp; autopay</b> is the "
            "single most-complained-about theme and the lowest-rated — the same friction "
            "that caps the signup→paying conversion in the funnel. Billing UX, not "
            "content, is the rating drag. (See Voice-of-customer tab.)", KUKU)
    insight("Risk #2 — the paywall cliff",
            "Episode-survival curves fall sharply <b>exactly at the paywall</b>. Its "
            "placement is a direct lever on the engagement-vs-revenue trade-off. "
            "(See Content tab.)", AMBER)

    sec("Competitive snapshot — App Store ratings (real, iOS India)")
    comp = pd.DataFrame({
        "App": ["Kuku FM", "Kuku TV", "Pocket FM"],
        "Rating": [4.10, 4.23, 4.54],
        "Ratings count": [11936, 37311, 54250],
    })
    cc1, cc2 = st.columns([3, 2])
    figc = go.Figure(go.Bar(
        x=comp["Rating"], y=comp["App"], orientation="h",
        marker_color=[KUKU, "#f05a60", BLUE],
        text=[f"{r:.2f}★ · {n:,} ratings" for r, n in zip(comp["Rating"], comp["Ratings count"])],
        textposition="outside", cliponaxis=False))
    figc.update_traces(textfont_color=P["ink"])
    figc.update_xaxes(range=[3.6, 4.9])
    cc1.plotly_chart(style(figc, "Kuku vs Pocket FM", "Current-version iOS rating",
                           height=300), width="stretch")
    cc2.markdown(
        "<br>".join([
            "<b>Reading it:</b>",
            "Pocket FM (the category pioneer) still leads on satisfaction.",
            "Kuku TV already out-rates Kuku FM — the video product lands cleaner.",
            "Kuku FM's rating is dragged by billing/autopay complaints, not content "
            "— exactly the fix the review analysis points to.",
        ]), unsafe_allow_html=True)

    with st.expander("Sources (company facts)"):
        st.markdown(
            "- Inc42 — Kuku FM company profile (funding, FY25 revenue): "
            "https://inc42.com/company/kuku-fm/\n"
            "- Startup Wired — $85M Series C, $550M valuation (Oct 2025): "
            "https://startupwired.com/2025/10/16/kuku-fm-secures-85-million-in-fresh-funding-eyes-global-expansion/\n"
            "- CEOVine — founders, 2018 pivot, pricing, milestones: "
            "https://www.ceovine.com/kuku-fm-success-story\n"
            "- kukufm.com — languages, catalogue, ₹1 trial\n"
            "- Apple App Store Search API — live iOS ratings for Kuku FM, Kuku TV, Pocket FM\n\n"
            "Kuku FM, Kuku TV and their logos/screenshots are the property of their "
            "owners and are shown here for analysis/commentary only.")


# ---------------------------------------------------------------------------
# Tab 1 — Overview
# ---------------------------------------------------------------------------
with tab1:
    note(SYN_NOTE)
    kpi = q(f"""
        WITH fu AS (SELECT * FROM users {W}),
             sb AS (SELECT DISTINCT user_id FROM subscriptions WHERE user_id IN (SELECT user_id FROM fu)),
             pay AS (SELECT s.user_id, p.amount FROM payments p JOIN subscriptions s ON s.sub_id=p.sub_id
                     WHERE p.status='success' AND p.amount>=99 AND s.user_id IN (SELECT user_id FROM fu))
        SELECT (SELECT count(*) FROM fu) AS signups,
               (SELECT count(*) FROM sb) AS subscribers,
               (SELECT count(DISTINCT user_id) FROM pay) AS paying_users,
               (SELECT round(sum(amount),0) FROM pay) AS revenue
    """).iloc[0]
    subrate = (kpi["subscribers"] / kpi["signups"] * 100) if kpi["signups"] else 0
    arppu = (kpi["revenue"] / kpi["paying_users"]) if kpi["paying_users"] else 0
    payrate = (kpi["paying_users"] / kpi["signups"] * 100) if kpi["signups"] else 0

    kpi_row([
        ("Signups", fmt(kpi["signups"]), "in the modelled window", BLUE),
        ("Subscribers", fmt(kpi["subscribers"]), f"{subrate:.1f}% of signups", KUKU),
        ("Subscribe rate", f"{subrate:.1f}%", "signup → paid start", VIOLET),
        ("Paying users", fmt(kpi["paying_users"]), f"{payrate:.1f}% of signups", AMBER),
        ("ARPPU", f"Rs {arppu:,.0f}", "per paying user", TEAL),
    ])

    insight("What this says",
            f"<b>{subrate:.1f}% of signups subscribe</b>, but only "
            f"<b>{payrate:.1f}% ever pay</b> — the gap between starting and paying is "
            "where the money leaks. The funnel tab shows exactly where.", VIOLET)

    mau = q(f"""
        WITH fu AS (SELECT user_id FROM users {W})
        SELECT date_trunc('month', ce.ts)::date AS month,
               count(DISTINCT ce.user_id) AS mau,
               round(sum(ce.seconds_consumed)/60.0/count(DISTINCT ce.user_id),1) AS minutes_per_user
        FROM consumption_events ce WHERE ce.seconds_consumed>=30
          AND ce.user_id IN (SELECT user_id FROM fu)
        GROUP BY 1 ORDER BY 1
    """)
    mau = mau[mau["month"].astype(str) < "2026-11-01"]
    cc = st.columns(2)
    f = go.Figure(go.Scatter(x=mau["month"], y=mau["mau"], mode="lines+markers",
                             line=dict(color=KUKU, width=3), marker=dict(size=7),
                             fill="tozeroy", fillcolor="rgba(232,34,44,0.10)",
                             hovertemplate="%{x|%b %Y}<br>%{y:,} users<extra></extra>"))
    f.update_yaxes(rangemode="tozero")
    cc[0].plotly_chart(style(f, "Monthly active users",
                             "Distinct users with 30s+ of listening"), width="stretch")
    f2 = go.Figure(go.Scatter(x=mau["month"], y=mau["minutes_per_user"], mode="lines+markers",
                              line=dict(color=BLUE, width=3), marker=dict(size=7),
                              fill="tozeroy", fillcolor="rgba(76,141,255,0.10)",
                              hovertemplate="%{x|%b %Y}<br>%{y} min<extra></extra>"))
    f2.update_yaxes(rangemode="tozero")
    cc[1].plotly_chart(style(f2, "Minutes per active user", "Monthly"), width="stretch")


# ---------------------------------------------------------------------------
# Tab 2 — Funnel & retention
# ---------------------------------------------------------------------------
with tab2:
    note(SYN_NOTE)
    funnel = q(f"""
        WITH fu AS (SELECT user_id, signup_ts FROM users {W}),
             fp AS (SELECT user_id FROM consumption_events WHERE seconds_consumed>=30
                    AND user_id IN (SELECT user_id FROM fu) GROUP BY user_id),
             act AS (SELECT ce.user_id FROM consumption_events ce JOIN fu ON fu.user_id=ce.user_id
                     WHERE ce.ts <= fu.signup_ts + INTERVAL '72 hours'
                     GROUP BY ce.user_id HAVING count(DISTINCT ce.episode_id)>=3),
             pw AS (SELECT DISTINCT user_id FROM app_events WHERE event_name='paywall_view'
                    AND user_id IN (SELECT user_id FROM fu)),
             sb AS (SELECT DISTINCT user_id FROM subscriptions WHERE user_id IN (SELECT user_id FROM fu))
        SELECT 'Signed up' AS stage, (SELECT count(*) FROM fu) AS users, 1 AS ord
        UNION ALL SELECT 'Played an episode', (SELECT count(*) FROM fp), 2
        UNION ALL SELECT 'Activated (3+ in 72h)', (SELECT count(*) FROM act), 3
        UNION ALL SELECT 'Hit the paywall', (SELECT count(*) FROM pw), 4
        UNION ALL SELECT 'Subscribed', (SELECT count(*) FROM sb), 5
        ORDER BY ord
    """)
    funnel["pct"] = (funnel["users"] / funnel["users"].iloc[0] * 100).round(1)
    funnel["step_drop"] = funnel["users"].shift(1) - funnel["users"]
    di = funnel["step_drop"].iloc[1:].astype(float).idxmax()
    worst_from = funnel["stage"].iloc[di - 1]
    worst_to = funnel["stage"].iloc[di]
    worst_pct = 100 * funnel["step_drop"].iloc[di] / funnel["users"].iloc[di - 1]

    shades = ["#4c8dff", "#9b6cf2", "#f05a60", KUKU, KUKU_DK]
    fig = go.Figure(go.Bar(
        x=funnel["users"], y=funnel["stage"], orientation="h",
        marker_color=shades[:len(funnel)],
        text=[f"{u:,} · {p:.0f}%" for u, p in zip(funnel["users"], funnel["pct"])],
        textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>%{x:,} users<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(showgrid=True)
    fig.update_traces(textfont_color=P["ink"])
    st.plotly_chart(style(fig, "Where new users fall out of the funnel",
                          "Signup to subscription · share of (filtered) signups",
                          height=380), width="stretch")

    insight("Biggest leak",
            f"The steepest single drop is <b>{worst_from} → {worst_to}</b>, losing "
            f"<b>{worst_pct:.0f}%</b> of the users who reached that step. Fixing this "
            "stage moves the subscribe rate more than anything upstream.", KUKU)

    ret = q(f"""
        WITH fu AS (SELECT user_id, signup_ts FROM users {W}),
        activity AS (SELECT ce.user_id, (ce.ts::date - fu.signup_ts::date) AS d
                     FROM consumption_events ce JOIN fu ON fu.user_id=ce.user_id
                     WHERE ce.seconds_consumed>=30 GROUP BY 1,2),
        ft AS (SELECT DISTINCT ON (ce.user_id) ce.user_id, t.genre
               FROM consumption_events ce JOIN episodes e ON e.episode_id=ce.episode_id
               JOIN titles t ON t.title_id=e.title_id
               WHERE ce.user_id IN (SELECT user_id FROM fu) ORDER BY ce.user_id, ce.ts),
        m AS (SELECT fu.user_id, ft.genre, ({CUTOFF}-fu.signup_ts::date) AS obs
              FROM fu JOIN ft ON ft.user_id=fu.user_id)
        SELECT m.genre, count(*) AS users,
               round(100.0*count(*) FILTER(WHERE a1.user_id IS NOT NULL)/NULLIF(count(*) FILTER(WHERE obs>=1),0),1) AS d1,
               round(100.0*count(*) FILTER(WHERE a30.user_id IS NOT NULL)/NULLIF(count(*) FILTER(WHERE obs>=30),0),1) AS d30
        FROM m
        LEFT JOIN activity a1 ON a1.user_id=m.user_id AND a1.d=1
        LEFT JOIN activity a30 ON a30.user_id=m.user_id AND a30.d=30
        GROUP BY m.genre ORDER BY d1 DESC
    """)
    fig2 = go.Figure()
    fig2.add_bar(x=ret["genre"], y=ret["d1"], name="D1 retention", marker_color=TEAL)
    fig2.add_bar(x=ret["genre"], y=ret["d30"], name="D30 retention", marker_color=KUKU)
    fig2.update_layout(barmode="group")
    fig2.update_yaxes(ticksuffix="%")
    st.plotly_chart(style(fig2, "High-hook genres win day 1 but lose the month",
                          "Retention by genre of first watched title", height=380),
                    width="stretch")


# ---------------------------------------------------------------------------
# Tab 3 — Content
# ---------------------------------------------------------------------------
with tab3:
    note(SYN_NOTE)
    surv = q("""
        WITH ew AS (SELECT e.title_id, e.ep_number, count(DISTINCT ce.user_id) AS w
                    FROM consumption_events ce JOIN episodes e ON e.episode_id=ce.episode_id
                    GROUP BY 1,2),
             s AS (SELECT ew.title_id, ew.ep_number, ew.w,
                          FIRST_VALUE(ew.w) OVER (PARTITION BY ew.title_id ORDER BY ew.ep_number) AS w1
                   FROM ew)
        SELECT t.experiment_group, s.ep_number, round(avg(100.0*s.w/NULLIF(s.w1,0)),1) AS pct
        FROM s JOIN titles t ON t.title_id=s.title_id
        WHERE t.experiment_group IN ('paywall_ep6','paywall_ep8') AND s.ep_number<=12
        GROUP BY 1,2 ORDER BY 1,2
    """)
    fig = go.Figure()
    for grp, col, wall in [("paywall_ep6", KUKU, 6), ("paywall_ep8", TEAL, 8)]:
        g = surv[surv["experiment_group"] == grp]
        fig.add_scatter(x=g["ep_number"], y=g["pct"], mode="lines+markers",
                        name=f"Paywall at ep {wall}", line=dict(color=col, width=3),
                        marker=dict(size=7))
        fig.add_vline(x=wall, line=dict(color=col, width=1.2, dash="dot"))
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    fig.update_xaxes(title="Episode number", dtick=1)
    st.plotly_chart(style(fig, "The paywall, not the content, is the cliff",
                          "Share of a title's episode-1 viewers still watching, by paywall position",
                          height=380), width="stretch")

    insight("Read this chart",
            "Both curves fall gently with each episode — then drop sharply <b>exactly at "
            "the paywall</b>, not before. The content keeps people; the paywall placement "
            "is the lever. Moving it later trades revenue per user for a longer "
            "engagement runway.", TEAL)

    colA, colB = st.columns([3, 2])
    lead = q(f"""
        WITH fu AS (SELECT user_id FROM users {W})
        SELECT t.title_name AS title, t.genre, t.format,
               count(DISTINCT ce.user_id) AS viewers,
               round(100.0*count(*) FILTER(WHERE ce.completed)/NULLIF(count(*),0),1) AS completion_pct
        FROM consumption_events ce JOIN episodes e ON e.episode_id=ce.episode_id
        JOIN titles t ON t.title_id=e.title_id
        WHERE ce.user_id IN (SELECT user_id FROM fu)
        GROUP BY 1,2,3 ORDER BY viewers DESC LIMIT 15
    """)
    rows = ""
    for _, r in lead.iterrows():
        w = max(2, min(100, float(r["completion_pct"])))
        rows += (f'<tr><td>{r["title"]}</td>'
                 f'<td><span class="pill">{r["genre"]}</span></td>'
                 f'<td>{r["format"]}</td>'
                 f'<td class="num">{int(r["viewers"]):,}</td>'
                 f'<td class="num"><span class="bar-wrap"><span class="bar-fill" '
                 f'style="width:{w}%"></span></span> {r["completion_pct"]:.0f}%</td></tr>')
    colA.markdown("**Title leaderboard** — top 15 by reach", unsafe_allow_html=True)
    colA.markdown(
        '<table class="ktab"><thead><tr><th>Title</th><th>Genre</th><th>Format</th>'
        '<th class="num">Viewers</th><th class="num">Completion</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>', unsafe_allow_html=True)

    fmt_df = q(f"""
        WITH fu AS (SELECT user_id FROM users {W})
        SELECT t.format, count(DISTINCT ce.user_id) AS users,
               round(sum(ce.seconds_consumed)/60.0/count(DISTINCT ce.user_id),1) AS minutes_per_user
        FROM consumption_events ce JOIN episodes e ON e.episode_id=ce.episode_id
        JOIN titles t ON t.title_id=e.title_id
        WHERE ce.seconds_consumed>=30 AND ce.user_id IN (SELECT user_id FROM fu)
        GROUP BY 1 ORDER BY minutes_per_user DESC
    """)
    figf = go.Figure(go.Bar(x=fmt_df["format"], y=fmt_df["minutes_per_user"],
                            marker_color=[BLUE, AMBER][:len(fmt_df)],
                            text=[f"{v:.1f}" for v in fmt_df["minutes_per_user"]],
                            textposition="outside", cliponaxis=False))
    figf.update_traces(textfont_color=P["ink"])
    figf.update_yaxes(rangemode="tozero")
    colB.plotly_chart(style(figf, "Minutes per user by format", height=360),
                      width="stretch")


# ---------------------------------------------------------------------------
# Tab 4 — Voice of customer (REAL reviews)
# ---------------------------------------------------------------------------
with tab4:
    note("Real public Play Store reviews (Kuku FM + Kuku TV, India, Aug–Nov 2026). "
         "Self-selected sample. Not filtered by the sidebar.")
    themes = pd.read_csv(os.path.join(PROC, "theme_summary.csv"))
    labeled = pd.read_csv(os.path.join(PROC, "kuku_reviews_labeled.csv"))

    name = {"payments_billing": "Payments & autopay", "content_quality": "Content quality",
            "pricing": "Pricing", "playback_tech": "Playback / tech", "ads": "Ads",
            "support": "Customer support", "discovery_nav": "Discovery & navigation",
            "app_stability": "App stability", "language": "Language", "praise": "Praise"}
    th = themes[themes["themes"] != "praise"].sort_values("share_of_reviews_pct").tail(8).copy()
    th["label"] = th["themes"].map(name).fillna(th["themes"])
    th["color"] = [KUKU if r < 2.5 else TEAL for r in th["avg_rating"]]
    top = th.sort_values("share_of_reviews_pct").iloc[-1]

    insight("Top complaint",
            f"<b>{top['label']}</b> is the single most common theme at "
            f"<b>{top['share_of_reviews_pct']:.1f}%</b> of reviews, averaging "
            f"<b>{top['avg_rating']:.1f}★</b>. Billing &amp; autopay friction — not "
            "content — is what drags the public rating down.", KUKU)

    colL, colR = st.columns(2)
    fig = go.Figure(go.Bar(
        x=th["share_of_reviews_pct"], y=th["label"], orientation="h",
        marker_color=th["color"],
        text=[f"{s:.1f}% · avg {r:.1f}" for s, r in zip(th["share_of_reviews_pct"], th["avg_rating"])],
        textposition="outside", cliponaxis=False))
    fig.update_traces(textfont_color=P["ink"])
    fig.update_xaxes(ticksuffix="%")
    colL.plotly_chart(style(fig, "What 1,200 real reviews complain about",
                            "Red = average rating below 2.5", height=380), width="stretch")

    dist = labeled.groupby(["rating", "app"]).size().reset_index(name="reviews")
    figd = go.Figure()
    for app, col in [("Kuku FM", BLUE), ("Kuku TV", AMBER)]:
        d = dist[dist["app"] == app]
        figd.add_bar(x=d["rating"], y=d["reviews"], name=app, marker_color=col)
    figd.update_layout(barmode="group")
    figd.update_xaxes(title="Star rating", dtick=1)
    colR.plotly_chart(style(figd, "Reviews are strongly polarised",
                            "600 reviews per app", height=380), width="stretch")

    st.markdown("**Representative payment complaints** — real, verbatim, 1-star")
    mask = labeled["themes"].fillna("").str.contains("payments_billing") & (labeled["rating"] == 1)
    for t in labeled.loc[mask, "text"].dropna().head(5):
        st.markdown(f"> {str(t)[:240]}")

st.divider()
note("Synthetic product metrics are a reproducible model, never presented as Kuku's "
     "real numbers. Company facts, review quotes, ratings and app imagery are real "
     "public data, shown for analysis only. Built in Python (Streamlit · DuckDB · Plotly).")

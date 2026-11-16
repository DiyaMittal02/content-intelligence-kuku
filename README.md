# Micro-drama & Audio Content Intelligence — Kuku (case study)

> **⚠️ SYNTHETIC DATA NOTICE.** This project uses a **reproducibly generated, synthetic dataset**. It does **not** contain, claim, or imply access to any real Kuku FM / Kuku TV internal data, user data, or performance numbers. Every chart and table built on generated data is labelled *"Synthetic."* The only real-world evidence used is **public Play Store reviews**, which are kept visually and analytically separate (see `notebooks/review_analysis.ipynb`). Metric definitions are in `database/data_dictionary.md`.

A product-analytics case study modelled on a micro-drama + audio storytelling app (framed around **Kuku**, which runs Kuku FM audio and Kuku TV micro-dramas). It demonstrates the analysis an entry-level Product Analyst would own: an activation funnel, cohort retention, episode-level drop-off, the paywall cliff, monetisation, and a readout of a simulated paywall-position experiment — all expressed in clean, commented SQL plus a Power BI dashboard, with recommendations prioritised by RICE.

Built by **Diya Mittal** — ex-Product Analyst intern at Pocket FM (Scout analytics platform).

---

## The five business questions this answers

1. **Where do users drop off** between install → first episode → paywall episode → subscription?
2. **Which genres, languages and titles retain users best** at D1, D7 and D30?
3. **Which episodes cause the biggest drop-off** inside a series — is it the paywall, or the content?
4. **Do micro-drama-first users retain / convert differently** from audio-first users?
5. **What do public reviews say is broken** (discovery, playback, pricing, payments), and how does that map to the funnel?

## Planted patterns (documented honestly)

The synthetic generator deliberately bakes in a few findable "stories" so the analysis has something real to detect. These are **planted on purpose** — detecting them is the point:

1. **High-hook / low-retention genre.** Thrillers over-index on D1 (a strong first-episode hook) but decay faster, so their D30 retention is poor relative to Drama/Romance.
2. **A payment-failure spike.** One calendar week has a UPI gateway incident: payment failure rate jumps from ~7% to ~35%, denting conversions that week.
3. **Paywall position effect.** Titles are split into a paywall-at-ep-6 vs paywall-at-ep-8 experiment group; the earlier paywall loses more users *at* the wall but barely moves eventual subscribe-rate among those who cross — i.e. moving the wall later recovers reach at little monetisation cost.

See `database/data_dictionary.md` → "Planted patterns" for the exact parameters.

---

## How to run

```bash
# 1. Install deps
python -m venv .venv && .venv\Scripts\activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 2. Generate the synthetic data (seeded, reproducible -> database/data/synthetic/*.csv)
python database/generate_data.py --users 50000 --seed 42
python database/validate_patterns.py                # confirm the 3 planted stories are detectable

# 3. Run the analysis SQL. With Postgres:
psql -d kuku_ci -f database/schema.sql && python database/load_to_postgres.py
psql -d kuku_ci -f sql/01_data_quality.sql          # ... through 09
# No Postgres? Validate every query against the CSVs via DuckDB:
python sql/_run_all.py

# 4. Collect + analyse the REAL Play Store reviews
python notebooks/fetch_reviews.py                   # public reviews -> data/reviews_raw/
python notebooks/classify_reviews.py                # keyword themes -> data/reviews_processed/

# 5. Build the marts, figures and the case-study PDF
python analysis/export_marts.py                     # aggregated marts -> dashboard/data/
python analysis/make_figures.py                     # editorial charts -> reports/figures/
python reports/build_case_study.py                  # -> reports/case_study.pdf

# 6. Launch the interactive dashboard (pure Python)
streamlit run app.py                                # live, filterable; opens in the browser
```

## Repository layout

```
content-intelligence-kuku/
├── README.md  ·  requirements.txt
├── database/
│   ├── schema.sql                 # 8-table Postgres DDL
│   ├── generate_data.py           # seeded generator; 3 planted patterns, documented
│   ├── validate_patterns.py       # proves the planted patterns are detectable
│   ├── load_to_postgres.py        # bulk COPY of the CSVs
│   └── data_dictionary.md         # every column + metric definition
├── sql/                           # 01_data_quality.sql ... 09_experiment_readout.sql + _run_all.py
├── notebooks/
│   ├── fetch_reviews.py           # REAL public reviews via urllib (no scraping package)
│   ├── classify_reviews.py        # transparent keyword theming
│   └── review_analysis.ipynb      # voice-of-customer analysis (real reviews)
├── app.py                         # interactive Streamlit dashboard (DuckDB + Plotly)
├── analysis/
│   ├── chart_style.py             # validated, colourblind-checked editorial palette
│   ├── export_marts.py            # synthetic + review data -> dashboard/data/*.csv
│   └── make_figures.py            # renders the figures
├── dashboard/
│   └── data/                      # aggregated marts (also used by the figures)
└── reports/
    ├── case_study.pdf             # the 1-read deliverable
    ├── build_case_study.py        # regenerates the PDF
    └── figures/                   # rendered charts
```

The dashboard (`app.py`) has four tabs — Overview, Funnel & retention, Content, and Voice of
customer — with sidebar filters (language, acquisition channel, device tier) that re-query the
data live. Synthetic product metrics and the real review evidence are kept clearly separate.

## Honesty & data rules (applied throughout)

- Every insight is tagged as one of: *observed public feedback* / *simulated analytical result* / *product hypothesis* / *validation needed*.
- Simulated retention, revenue, conversion and churn are **never** presented as Kuku's real performance.
- Public reviews: source, collection date, rating, app version and platform are kept; sample size and method are reported; reviews are noted as self-selected.
- No private, login-gated, or personal data is collected; platform terms and rate limits respected.

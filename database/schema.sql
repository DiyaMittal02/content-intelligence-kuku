-- =====================================================================
-- Micro-drama & Audio Content Intelligence (Kuku) — PostgreSQL schema
-- SYNTHETIC DATA. No real Kuku data is represented.
-- 8 core tables. Load order respects FKs: users, titles, episodes,
-- sessions, subscriptions, payments, consumption_events, app_events.
-- =====================================================================

DROP TABLE IF EXISTS app_events        CASCADE;
DROP TABLE IF EXISTS consumption_events CASCADE;
DROP TABLE IF EXISTS payments          CASCADE;
DROP TABLE IF EXISTS subscriptions     CASCADE;
DROP TABLE IF EXISTS sessions          CASCADE;
DROP TABLE IF EXISTS episodes          CASCADE;
DROP TABLE IF EXISTS titles            CASCADE;
DROP TABLE IF EXISTS users             CASCADE;

-- ---------------------------------------------------------------------
-- users: one row per registered user
-- Realism: language mix weighted to Hindi; ~70% low/mid-tier Android.
-- ---------------------------------------------------------------------
CREATE TABLE users (
    user_id       BIGINT       PRIMARY KEY,
    signup_ts     TIMESTAMP    NOT NULL,
    acq_channel   TEXT         NOT NULL,   -- organic | meta_ads | google_ads | youtube | referral | influencer
    language      TEXT         NOT NULL,   -- Hindi | Tamil | Telugu | ...
    state         TEXT         NOT NULL,   -- Indian state
    device_tier   TEXT         NOT NULL,   -- low | mid | high
    platform      TEXT         NOT NULL    -- Android | iOS
);

-- ---------------------------------------------------------------------
-- titles: a show (audio series or micro-drama series)
-- Realism: paywall typically at episode 5–10.
-- experiment_group marks the simulated paywall-position A/B.
-- ---------------------------------------------------------------------
CREATE TABLE titles (
    title_id          BIGINT   PRIMARY KEY,
    title_name        TEXT     NOT NULL,
    format            TEXT     NOT NULL,   -- audio | microdrama
    genre             TEXT     NOT NULL,
    language          TEXT     NOT NULL,
    n_episodes        INT      NOT NULL,
    paywall_ep        INT      NOT NULL,   -- first paid episode
    experiment_group  TEXT     NOT NULL    -- paywall_ep6 | paywall_ep8 | control
);

-- ---------------------------------------------------------------------
-- episodes: one row per episode of a title
-- Realism: micro-drama 60–120s; audio 8–15 min.
-- ---------------------------------------------------------------------
CREATE TABLE episodes (
    episode_id   BIGINT   PRIMARY KEY,
    title_id     BIGINT   NOT NULL REFERENCES titles(title_id),
    ep_number    INT      NOT NULL,
    duration_sec INT      NOT NULL,
    is_paid      BOOLEAN  NOT NULL,        -- ep_number >= title.paywall_ep
    UNIQUE (title_id, ep_number)
);

-- ---------------------------------------------------------------------
-- sessions: an app-open session
-- Realism: weekday/weekend and night-time peaks.
-- ---------------------------------------------------------------------
CREATE TABLE sessions (
    session_id   BIGINT     PRIMARY KEY,
    user_id      BIGINT     NOT NULL REFERENCES users(user_id),
    start_ts     TIMESTAMP  NOT NULL,
    end_ts       TIMESTAMP  NOT NULL,
    platform     TEXT       NOT NULL
);

-- ---------------------------------------------------------------------
-- subscriptions: trial / paid plan records
-- Realism: trial → paid conversion; monthly vs annual.
-- ---------------------------------------------------------------------
CREATE TABLE subscriptions (
    sub_id     BIGINT     PRIMARY KEY,
    user_id    BIGINT     NOT NULL REFERENCES users(user_id),
    plan       TEXT       NOT NULL,        -- trial | monthly | annual
    start_ts   TIMESTAMP  NOT NULL,
    end_ts     TIMESTAMP,
    price      NUMERIC(8,2) NOT NULL,
    status     TEXT       NOT NULL,        -- active | expired | cancelled
    renewed    BOOLEAN    NOT NULL
);

-- ---------------------------------------------------------------------
-- payments: payment attempts against a subscription
-- Realism: UPI-dominant; 5–10% failures (one planted spike week ~35%).
-- ---------------------------------------------------------------------
CREATE TABLE payments (
    payment_id  BIGINT      PRIMARY KEY,
    sub_id      BIGINT      NOT NULL REFERENCES subscriptions(sub_id),
    ts          TIMESTAMP   NOT NULL,
    amount      NUMERIC(8,2) NOT NULL,
    method      TEXT        NOT NULL,      -- upi | card | netbanking | wallet
    status      TEXT        NOT NULL       -- success | failed
);

-- ---------------------------------------------------------------------
-- consumption_events: a user watching/listening to an episode
-- Realism: drop-off decays per episode; spike at the paywall.
-- ---------------------------------------------------------------------
CREATE TABLE consumption_events (
    event_id         BIGINT    PRIMARY KEY,
    user_id          BIGINT    NOT NULL REFERENCES users(user_id),
    episode_id       BIGINT    NOT NULL REFERENCES episodes(episode_id),
    ts               TIMESTAMP NOT NULL,
    seconds_consumed INT       NOT NULL,
    completed        BOOLEAN   NOT NULL    -- reached >= 90% of duration
);

-- ---------------------------------------------------------------------
-- app_events: generic product telemetry
-- Realism: search, browse, share, paywall_view, etc. props as jsonb.
-- ---------------------------------------------------------------------
CREATE TABLE app_events (
    event_id    BIGINT     PRIMARY KEY,
    user_id     BIGINT     NOT NULL REFERENCES users(user_id),
    event_name  TEXT       NOT NULL,       -- app_open | search | browse | share | paywall_view | subscribe_click
    ts          TIMESTAMP  NOT NULL,
    props       JSONB
);

-- Helpful indexes for the analysis queries
CREATE INDEX idx_users_signup        ON users(signup_ts);
CREATE INDEX idx_cons_user_ts        ON consumption_events(user_id, ts);
CREATE INDEX idx_cons_episode        ON consumption_events(episode_id);
CREATE INDEX idx_sessions_user_ts    ON sessions(user_id, start_ts);
CREATE INDEX idx_subs_user           ON subscriptions(user_id);
CREATE INDEX idx_pay_sub             ON payments(sub_id);
CREATE INDEX idx_appevents_user_ts   ON app_events(user_id, ts);
CREATE INDEX idx_appevents_name      ON app_events(event_name);
CREATE INDEX idx_episodes_title      ON episodes(title_id, ep_number);

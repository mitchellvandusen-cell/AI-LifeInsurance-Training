-- InsuranceGrokBot Training Platform Schema
-- Designed for Neon PostgreSQL

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ══════════════════════════════════════════════════════════════
-- USERS
-- Core user accounts with authentication credentials.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    name            TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ══════════════════════════════════════════════════════════════
-- TRAINING SUBSCRIPTIONS
-- Tracks subscription status, included minutes, and billing periods.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS training_subscriptions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL UNIQUE,
    stripe_customer_id      TEXT,
    stripe_subscription_id  TEXT,
    plan_status     TEXT NOT NULL DEFAULT 'inactive'
                    CHECK (plan_status IN ('active', 'inactive', 'cancelled', 'past_due', 'trialing')),
    included_minutes_total  INTEGER NOT NULL DEFAULT 300,  -- 5 hours = 300 min
    included_minutes_used   INTEGER NOT NULL DEFAULT 0,
    billing_period_start    TIMESTAMPTZ,
    billing_period_end      TIMESTAMPTZ,
    wallet_balance_cents    INTEGER NOT NULL DEFAULT 0,  -- Pay-as-you-go balance in cents
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_training_subs_user ON training_subscriptions(user_id);
CREATE INDEX idx_training_subs_stripe ON training_subscriptions(stripe_subscription_id);

-- ══════════════════════════════════════════════════════════════
-- TRAINING SESSIONS
-- One record per training session. Stores persona data, timing,
-- billing info, and the final report card.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS training_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL,
    subscription_id UUID REFERENCES training_subscriptions(id),

    -- Persona & client info
    persona_data    JSONB NOT NULL,         -- Full persona (hidden from agent)
    client_info     JSONB NOT NULL,         -- Simplified info shown to agent

    -- Session timing
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'completed', 'cancelled', 'error')),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    duration_seconds INTEGER DEFAULT 0,

    -- Billing
    billed_minutes  INTEGER DEFAULT 0,
    cost_cents      INTEGER DEFAULT 0,
    billed_from     TEXT DEFAULT 'subscription'
                    CHECK (billed_from IN ('subscription', 'wallet', 'add_on')),

    -- Results
    report_card     JSONB,                  -- Full grading report
    final_state     JSONB,                  -- Final engine state snapshot

    -- Voice config
    voice_name      TEXT DEFAULT 'Sal',

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON training_sessions(user_id);
CREATE INDEX idx_sessions_status ON training_sessions(status);
CREATE INDEX idx_sessions_started ON training_sessions(started_at);

-- ══════════════════════════════════════════════════════════════
-- SESSION TRANSCRIPTS
-- Individual messages within a training session.
-- Stored separately for efficient querying and analytics.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS session_transcripts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES training_sessions(id) ON DELETE CASCADE,
    turn_number     INTEGER NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('agent', 'client', 'system')),
    content         TEXT NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata        JSONB DEFAULT '{}'::jsonb  -- tonality, analysis, etc.
);

CREATE INDEX idx_transcripts_session ON session_transcripts(session_id);
CREATE INDEX idx_transcripts_turn ON session_transcripts(session_id, turn_number);

-- ══════════════════════════════════════════════════════════════
-- REPORT CARDS
-- Stored separately from sessions for efficient querying.
-- Contains the detailed grading breakdown and KPI scores.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS report_cards (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES training_sessions(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL,

    -- Summary scores
    overall_score   REAL NOT NULL DEFAULT 0,
    letter_grade    TEXT NOT NULL DEFAULT 'F',
    close_probability REAL DEFAULT 0,
    detected_style  TEXT,

    -- Category scores (stored as JSONB for flexibility)
    categories      JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Deal killers analysis
    deal_killers    JSONB DEFAULT '{}'::jsonb,

    -- Full report (the complete grading engine output)
    full_report     JSONB NOT NULL,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reports_user ON report_cards(user_id);
CREATE INDEX idx_reports_session ON report_cards(session_id);
CREATE INDEX idx_reports_created ON report_cards(created_at);
CREATE INDEX idx_reports_user_created ON report_cards(user_id, created_at);

-- ══════════════════════════════════════════════════════════════
-- WALLET TRANSACTIONS
-- Tracks all wallet activity: deposits, usage deductions,
-- add-on purchases, and refunds.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS wallet_transactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL,
    subscription_id UUID REFERENCES training_subscriptions(id),

    type            TEXT NOT NULL
                    CHECK (type IN ('deposit', 'deduction', 'add_on', 'refund', 'subscription_reset')),
    amount_cents    INTEGER NOT NULL,       -- Positive for credits, negative for debits
    balance_after   INTEGER NOT NULL,       -- Wallet balance after this transaction

    -- Context
    description     TEXT,
    session_id      UUID REFERENCES training_sessions(id),
    stripe_payment_id TEXT,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wallet_user ON wallet_transactions(user_id);
CREATE INDEX idx_wallet_created ON wallet_transactions(created_at);

-- ══════════════════════════════════════════════════════════════
-- ADD-ON PURCHASES
-- Tracks purchased hour add-ons for the current billing period.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS addon_purchases (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL,
    subscription_id UUID REFERENCES training_subscriptions(id),

    package_type    TEXT NOT NULL CHECK (package_type IN ('2hr', '4hr')),
    minutes_total   INTEGER NOT NULL,       -- 120 or 240
    minutes_used    INTEGER NOT NULL DEFAULT 0,
    price_cents     INTEGER NOT NULL,       -- 1200 or 2400
    stripe_payment_id TEXT,

    billing_period_start TIMESTAMPTZ,
    billing_period_end   TIMESTAMPTZ,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_addons_user ON addon_purchases(user_id);

-- ══════════════════════════════════════════════════════════════
-- CALL RECORDINGS (Twilio Import)
-- Imported recordings from the user's InsuranceGrokBot account.
-- Analyzed by the training engine for report cards on real calls.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS call_recordings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL,

    -- Twilio data
    twilio_recording_sid TEXT,
    twilio_call_sid      TEXT,
    recording_url        TEXT,
    duration_seconds     INTEGER,
    call_date            TIMESTAMPTZ,

    -- Processing
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    transcript      JSONB,                  -- Full transcription
    report_card     JSONB,                  -- Analysis report

    -- Metadata
    caller_number   TEXT,
    agent_name      TEXT,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at    TIMESTAMPTZ
);

CREATE INDEX idx_recordings_user ON call_recordings(user_id);
CREATE INDEX idx_recordings_status ON call_recordings(status);
CREATE INDEX idx_recordings_date ON call_recordings(call_date);

-- ══════════════════════════════════════════════════════════════
-- DAILY ANALYTICS SNAPSHOTS
-- Precomputed daily KPI aggregates for fast dashboard rendering.
-- Populated by a background job or computed on demand.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS analytics_daily (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL,
    date            DATE NOT NULL,

    -- Training volume
    sessions_count  INTEGER DEFAULT 0,
    total_minutes   REAL DEFAULT 0,

    -- Average scores
    avg_overall     REAL DEFAULT 0,
    avg_tonality    REAL DEFAULT 0,
    avg_rapport     REAL DEFAULT 0,
    avg_questions   REAL DEFAULT 0,
    avg_compliance  REAL DEFAULT 0,
    avg_flow        REAL DEFAULT 0,
    avg_trust       REAL DEFAULT 0,
    avg_objection_handling REAL DEFAULT 0,
    avg_preframing  REAL DEFAULT 0,
    avg_presentation REAL DEFAULT 0,
    avg_close       REAL DEFAULT 0,
    avg_underwriting REAL DEFAULT 0,

    -- Objection stats
    objections_faced    INTEGER DEFAULT 0,
    objections_resolved INTEGER DEFAULT 0,

    -- Style distribution
    style_distribution  JSONB DEFAULT '{}'::jsonb,

    -- Close probability trend
    avg_close_probability REAL DEFAULT 0,

    UNIQUE(user_id, date)
);

CREATE INDEX idx_analytics_user_date ON analytics_daily(user_id, date);

-- ══════════════════════════════════════════════════════════════
-- USER SETTINGS (Training-specific)
-- Stores training preferences and InsuranceGrokBot account link.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS training_settings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL UNIQUE,

    -- Preferences
    preferred_voice TEXT DEFAULT 'Sal',
    auto_import_recordings BOOLEAN DEFAULT FALSE,

    -- InsuranceGrokBot account link
    grokbot_account_linked BOOLEAN DEFAULT FALSE,
    grokbot_api_key        TEXT,  -- Encrypted
    twilio_account_sid     TEXT,  -- For recording import
    twilio_auth_token      TEXT,  -- Encrypted

    -- Notification preferences
    email_weekly_report    BOOLEAN DEFAULT TRUE,
    email_session_summary  BOOLEAN DEFAULT TRUE,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ══════════════════════════════════════════════════════════════
-- FUNCTIONS & TRIGGERS
-- ══════════════════════════════════════════════════════════════

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_training_subs_updated
    BEFORE UPDATE ON training_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_training_settings_updated
    BEFORE UPDATE ON training_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

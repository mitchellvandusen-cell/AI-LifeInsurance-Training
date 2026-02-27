"""
Database connection and operations for the training platform.
Uses asyncpg for async PostgreSQL access with Neon.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import asyncpg

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=os.getenv("DATABASE_URL"),
            min_size=2,
            max_size=20,
        )
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


# ── Helper ────────────────────────────────────────────────────

def _row_to_dict(row: asyncpg.Record) -> dict:
    return dict(row) if row else {}


def _uuid() -> str:
    return str(uuid.uuid4())


# ══════════════════════════════════════════════════════════════
# SCHEMA INITIALIZATION — creates all tables on a fresh database
# ══════════════════════════════════════════════════════════════

async def init_schema():
    """Create every table, index, function, and trigger needed by the platform.

    Safe to call on every startup — uses IF NOT EXISTS / OR REPLACE throughout.
    """
    pool = await get_pool()

    await pool.execute("""
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        -- USERS
        CREATE TABLE IF NOT EXISTS users (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            email           TEXT NOT NULL UNIQUE,
            password_hash   TEXT NOT NULL,
            name            TEXT NOT NULL DEFAULT '',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

        -- TRAINING SUBSCRIPTIONS
        CREATE TABLE IF NOT EXISTS training_subscriptions (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id         UUID NOT NULL UNIQUE,
            stripe_customer_id      TEXT,
            stripe_subscription_id  TEXT,
            plan_status     TEXT NOT NULL DEFAULT 'inactive'
                            CHECK (plan_status IN ('active','inactive','cancelled','past_due','trialing')),
            included_minutes_total  INTEGER NOT NULL DEFAULT 300,
            included_minutes_used   INTEGER NOT NULL DEFAULT 0,
            billing_period_start    TIMESTAMPTZ,
            billing_period_end      TIMESTAMPTZ,
            wallet_balance_cents    INTEGER NOT NULL DEFAULT 0,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_training_subs_user   ON training_subscriptions(user_id);
        CREATE INDEX IF NOT EXISTS idx_training_subs_stripe ON training_subscriptions(stripe_subscription_id);

        -- TRAINING SESSIONS
        CREATE TABLE IF NOT EXISTS training_sessions (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id         UUID NOT NULL,
            subscription_id UUID REFERENCES training_subscriptions(id),
            persona_data    JSONB NOT NULL,
            client_info     JSONB NOT NULL,
            status          TEXT NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active','completed','cancelled','error')),
            started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ended_at        TIMESTAMPTZ,
            duration_seconds INTEGER DEFAULT 0,
            billed_minutes  INTEGER DEFAULT 0,
            cost_cents      INTEGER DEFAULT 0,
            billed_from     TEXT DEFAULT 'subscription'
                            CHECK (billed_from IN ('subscription','wallet','add_on')),
            report_card     JSONB,
            final_state     JSONB,
            voice_name      TEXT DEFAULT 'Sal',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_user    ON training_sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_status  ON training_sessions(status);
        CREATE INDEX IF NOT EXISTS idx_sessions_started ON training_sessions(started_at);

        -- SESSION TRANSCRIPTS
        CREATE TABLE IF NOT EXISTS session_transcripts (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            session_id      UUID NOT NULL REFERENCES training_sessions(id) ON DELETE CASCADE,
            turn_number     INTEGER NOT NULL,
            role            TEXT NOT NULL CHECK (role IN ('agent','client','system')),
            content         TEXT NOT NULL,
            timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            metadata        JSONB DEFAULT '{}'::jsonb
        );
        CREATE INDEX IF NOT EXISTS idx_transcripts_session ON session_transcripts(session_id);
        CREATE INDEX IF NOT EXISTS idx_transcripts_turn    ON session_transcripts(session_id, turn_number);

        -- REPORT CARDS
        CREATE TABLE IF NOT EXISTS report_cards (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            session_id      UUID NOT NULL REFERENCES training_sessions(id) ON DELETE CASCADE,
            user_id         UUID NOT NULL,
            overall_score   REAL NOT NULL DEFAULT 0,
            letter_grade    TEXT NOT NULL DEFAULT 'F',
            close_probability REAL DEFAULT 0,
            detected_style  TEXT,
            categories      JSONB NOT NULL DEFAULT '[]'::jsonb,
            deal_killers    JSONB DEFAULT '{}'::jsonb,
            full_report     JSONB NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_reports_user         ON report_cards(user_id);
        CREATE INDEX IF NOT EXISTS idx_reports_session      ON report_cards(session_id);
        CREATE INDEX IF NOT EXISTS idx_reports_created      ON report_cards(created_at);
        CREATE INDEX IF NOT EXISTS idx_reports_user_created ON report_cards(user_id, created_at);

        -- WALLET TRANSACTIONS
        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id         UUID NOT NULL,
            subscription_id UUID REFERENCES training_subscriptions(id),
            type            TEXT NOT NULL
                            CHECK (type IN ('deposit','deduction','add_on','refund','subscription_reset')),
            amount_cents    INTEGER NOT NULL,
            balance_after   INTEGER NOT NULL,
            description     TEXT,
            session_id      UUID REFERENCES training_sessions(id),
            stripe_payment_id TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_wallet_user    ON wallet_transactions(user_id);
        CREATE INDEX IF NOT EXISTS idx_wallet_created ON wallet_transactions(created_at);

        -- ADD-ON PURCHASES
        CREATE TABLE IF NOT EXISTS addon_purchases (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id         UUID NOT NULL,
            subscription_id UUID REFERENCES training_subscriptions(id),
            package_type    TEXT NOT NULL CHECK (package_type IN ('2hr','4hr')),
            minutes_total   INTEGER NOT NULL,
            minutes_used    INTEGER NOT NULL DEFAULT 0,
            price_cents     INTEGER NOT NULL,
            stripe_payment_id TEXT,
            billing_period_start TIMESTAMPTZ,
            billing_period_end   TIMESTAMPTZ,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_addons_user ON addon_purchases(user_id);

        -- CALL RECORDINGS
        CREATE TABLE IF NOT EXISTS call_recordings (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id         UUID NOT NULL,
            twilio_recording_sid TEXT,
            twilio_call_sid      TEXT,
            recording_url        TEXT,
            duration_seconds     INTEGER,
            call_date            TIMESTAMPTZ,
            status          TEXT NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending','processing','completed','failed')),
            transcript      JSONB,
            report_card     JSONB,
            caller_number   TEXT,
            agent_name      TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            processed_at    TIMESTAMPTZ
        );
        CREATE INDEX IF NOT EXISTS idx_recordings_user   ON call_recordings(user_id);
        CREATE INDEX IF NOT EXISTS idx_recordings_status ON call_recordings(status);
        CREATE INDEX IF NOT EXISTS idx_recordings_date   ON call_recordings(call_date);

        -- DAILY ANALYTICS
        CREATE TABLE IF NOT EXISTS analytics_daily (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id         UUID NOT NULL,
            date            DATE NOT NULL,
            sessions_count  INTEGER DEFAULT 0,
            total_minutes   REAL DEFAULT 0,
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
            objections_faced    INTEGER DEFAULT 0,
            objections_resolved INTEGER DEFAULT 0,
            style_distribution  JSONB DEFAULT '{}'::jsonb,
            avg_close_probability REAL DEFAULT 0,
            UNIQUE(user_id, date)
        );
        CREATE INDEX IF NOT EXISTS idx_analytics_user_date ON analytics_daily(user_id, date);

        -- TRAINING SETTINGS
        CREATE TABLE IF NOT EXISTS training_settings (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id         UUID NOT NULL UNIQUE,
            preferred_voice TEXT DEFAULT 'Sal',
            auto_import_recordings BOOLEAN DEFAULT FALSE,
            grokbot_account_linked BOOLEAN DEFAULT FALSE,
            grokbot_api_key        TEXT,
            twilio_account_sid     TEXT,
            twilio_auth_token      TEXT,
            email_weekly_report    BOOLEAN DEFAULT TRUE,
            email_session_summary  BOOLEAN DEFAULT TRUE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- MODULE TRAINING SESSIONS
        CREATE TABLE IF NOT EXISTS module_sessions (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id         UUID NOT NULL,
            module_key      TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active','completed','cancelled')),
            started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ended_at        TIMESTAMPTZ,
            duration_seconds INTEGER DEFAULT 0,
            billed_minutes  INTEGER DEFAULT 0,
            cost_cents      INTEGER DEFAULT 0,
            billed_from     TEXT DEFAULT 'subscription',
            session_state   JSONB DEFAULT '{}'::jsonb,
            voice_name      TEXT DEFAULT 'Sal',
            feedback_summary TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_mod_sessions_user   ON module_sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_mod_sessions_module ON module_sessions(module_key);

        -- HOMEWORK REPORTS
        CREATE TABLE IF NOT EXISTS homework_reports (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id         UUID NOT NULL,
            sessions_analyzed INTEGER NOT NULL,
            overall_assessment TEXT NOT NULL,
            strengths       JSONB NOT NULL DEFAULT '[]'::jsonb,
            weaknesses      JSONB NOT NULL DEFAULT '[]'::jsonb,
            assignments     JSONB NOT NULL DEFAULT '[]'::jsonb,
            focus_order     JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_homework_user ON homework_reports(user_id);

        -- USER SCRIPTS (for script practice module)
        CREATE TABLE IF NOT EXISTS user_scripts (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id         UUID NOT NULL,
            name            TEXT NOT NULL,
            content         TEXT NOT NULL,
            char_count      INTEGER NOT NULL DEFAULT 0,
            source          TEXT NOT NULL DEFAULT 'paste',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_user_scripts_user ON user_scripts(user_id);

        -- UPDATED_AT TRIGGER FUNCTION
        CREATE OR REPLACE FUNCTION update_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Triggers can't use IF NOT EXISTS, so check before creating
    triggers = [
        ("trg_training_subs_updated", "training_subscriptions"),
        ("trg_training_settings_updated", "training_settings"),
        ("trg_user_scripts_updated", "user_scripts"),
    ]
    for trig_name, table_name in triggers:
        exists = await pool.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_trigger WHERE tgname = $1)", trig_name
        )
        if not exists:
            await pool.execute(f"""
                CREATE TRIGGER {trig_name}
                    BEFORE UPDATE ON {table_name}
                    FOR EACH ROW EXECUTE FUNCTION update_updated_at()
            """)

    print("[DB] Schema initialized — all tables ready")


# ══════════════════════════════════════════════════════════════
# USER / AUTH OPERATIONS
# ══════════════════════════════════════════════════════════════

async def get_user_by_email(email: str) -> Optional[dict]:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM users WHERE email = $1", email)
    return _row_to_dict(row) if row else None


async def get_user_by_id(user_id: str) -> Optional[dict]:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM users WHERE id = $1", uuid.UUID(user_id))
    return _row_to_dict(row) if row else None


async def create_user(email: str, password_hash: str, name: str) -> dict:
    pool = await get_pool()
    user_id = uuid.uuid4()
    await pool.execute(
        """INSERT INTO users (id, email, password_hash, name, created_at)
           VALUES ($1, $2, $3, $4, NOW())""",
        user_id, email, password_hash, name,
    )
    return {"id": str(user_id), "email": email, "name": name}


# ══════════════════════════════════════════════════════════════
# SUBSCRIPTION OPERATIONS
# ══════════════════════════════════════════════════════════════

async def get_subscription(user_id: str) -> Optional[dict]:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM training_subscriptions WHERE user_id = $1",
        uuid.UUID(user_id),
    )
    return _row_to_dict(row) if row else None


async def create_subscription(user_id: str, stripe_customer_id: str = None) -> dict:
    pool = await get_pool()
    sub_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=30)
    await pool.execute(
        """INSERT INTO training_subscriptions
           (id, user_id, stripe_customer_id, plan_status,
            included_minutes_total, included_minutes_used,
            billing_period_start, billing_period_end, wallet_balance_cents)
           VALUES ($1, $2, $3, 'active', 300, 0, $4, $5, 0)""",
        sub_id, uuid.UUID(user_id), stripe_customer_id, now, period_end,
    )
    return {"id": str(sub_id), "user_id": user_id, "plan_status": "active"}


async def update_subscription_status(user_id: str, status: str):
    pool = await get_pool()
    await pool.execute(
        "UPDATE training_subscriptions SET plan_status = $1 WHERE user_id = $2",
        status, uuid.UUID(user_id),
    )


async def use_subscription_minutes(user_id: str, minutes: int) -> bool:
    """Deduct minutes from subscription. Returns True if enough minutes available."""
    pool = await get_pool()
    result = await pool.fetchrow(
        """UPDATE training_subscriptions
           SET included_minutes_used = included_minutes_used + $1
           WHERE user_id = $2
             AND plan_status = 'active'
             AND (included_minutes_total - included_minutes_used) >= $1
           RETURNING id""",
        minutes, uuid.UUID(user_id),
    )
    return result is not None


async def use_addon_minutes(user_id: str, minutes: int) -> bool:
    """Deduct minutes from the oldest active add-on purchase. Returns True if enough."""
    pool = await get_pool()
    result = await pool.fetchrow(
        """UPDATE addon_purchases
           SET minutes_used = minutes_used + $1
           WHERE id = (
               SELECT id FROM addon_purchases
               WHERE user_id = $2
                 AND billing_period_end > NOW()
                 AND (minutes_total - minutes_used) >= $1
               ORDER BY created_at ASC
               LIMIT 1
           )
           RETURNING id""",
        minutes, uuid.UUID(user_id),
    )
    return result is not None


async def get_remaining_minutes(user_id: str) -> dict:
    """Get remaining subscription minutes and wallet balance."""
    sub = await get_subscription(user_id)
    if not sub:
        return {"subscription_minutes": 0, "wallet_cents": 0, "addon_minutes": 0}

    # Check add-on minutes
    pool = await get_pool()
    addons = await pool.fetch(
        """SELECT COALESCE(SUM(minutes_total - minutes_used), 0) as remaining
           FROM addon_purchases
           WHERE user_id = $1 AND billing_period_end > NOW()""",
        uuid.UUID(user_id),
    )
    addon_mins = addons[0]["remaining"] if addons else 0

    return {
        "subscription_minutes": max(0, sub["included_minutes_total"] - sub["included_minutes_used"]),
        "wallet_cents": sub["wallet_balance_cents"],
        "addon_minutes": addon_mins,
    }


async def deduct_wallet(user_id: str, cents: int, session_id: str, description: str) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            result = await conn.fetchrow(
                """UPDATE training_subscriptions
                   SET wallet_balance_cents = wallet_balance_cents - $1
                   WHERE user_id = $2 AND wallet_balance_cents >= $1
                   RETURNING wallet_balance_cents""",
                cents, uuid.UUID(user_id),
            )
            if not result:
                return False
            await conn.execute(
                """INSERT INTO wallet_transactions
                   (id, user_id, subscription_id, type, amount_cents, balance_after,
                    description, session_id)
                   SELECT $1, $2, ts.id, 'deduction', $3, $4, $5, $6
                   FROM training_subscriptions ts WHERE ts.user_id = $2""",
                uuid.uuid4(), uuid.UUID(user_id), -cents,
                result["wallet_balance_cents"], description,
                uuid.UUID(session_id) if session_id else None,
            )
    return True


async def add_wallet_funds(user_id: str, cents: int, stripe_payment_id: str = None) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            result = await conn.fetchrow(
                """UPDATE training_subscriptions
                   SET wallet_balance_cents = wallet_balance_cents + $1
                   WHERE user_id = $2
                   RETURNING wallet_balance_cents""",
                cents, uuid.UUID(user_id),
            )
            balance = result["wallet_balance_cents"] if result else 0
            await conn.execute(
                """INSERT INTO wallet_transactions
                   (id, user_id, subscription_id, type, amount_cents, balance_after,
                    description, stripe_payment_id)
                   SELECT $1, $2, ts.id, 'deposit', $3, $4, 'Wallet top-up', $5
                   FROM training_subscriptions ts WHERE ts.user_id = $2""",
                uuid.uuid4(), uuid.UUID(user_id), cents, balance, stripe_payment_id,
            )
    return balance


# ══════════════════════════════════════════════════════════════
# SESSION OPERATIONS
# ══════════════════════════════════════════════════════════════

async def create_session(
    user_id: str, persona_data: dict, client_info: dict, voice_name: str = "Sal"
) -> dict:
    pool = await get_pool()
    session_id = uuid.uuid4()
    await pool.execute(
        """INSERT INTO training_sessions
           (id, user_id, persona_data, client_info, status, voice_name)
           VALUES ($1, $2, $3, $4, 'active', $5)""",
        session_id, uuid.UUID(user_id),
        json.dumps(persona_data), json.dumps(client_info), voice_name,
    )
    return {"id": str(session_id), "status": "active"}


async def end_session(
    session_id: str, duration_seconds: int, report_card: dict,
    final_state: dict, billed_minutes: int, cost_cents: int, billed_from: str
) -> dict:
    pool = await get_pool()
    await pool.execute(
        """UPDATE training_sessions
           SET status = 'completed', ended_at = NOW(),
               duration_seconds = $1, report_card = $2, final_state = $3,
               billed_minutes = $4, cost_cents = $5, billed_from = $6
           WHERE id = $7""",
        duration_seconds, json.dumps(report_card), json.dumps(final_state),
        billed_minutes, cost_cents, billed_from, uuid.UUID(session_id),
    )
    return {"id": session_id, "status": "completed"}


async def get_session(session_id: str) -> Optional[dict]:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM training_sessions WHERE id = $1", uuid.UUID(session_id)
    )
    return _row_to_dict(row) if row else None


async def get_user_sessions(user_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT ts.id, ts.status, ts.started_at, ts.ended_at, ts.duration_seconds,
                  ts.client_info, ts.billed_minutes, ts.cost_cents,
                  rc.id AS report_card_id,
                  rc.overall_score, rc.letter_grade
           FROM training_sessions ts
           LEFT JOIN report_cards rc ON rc.session_id = ts.id
           WHERE ts.user_id = $1
           ORDER BY ts.started_at DESC
           LIMIT $2 OFFSET $3""",
        uuid.UUID(user_id), limit, offset,
    )
    return [_row_to_dict(r) for r in rows]


async def save_transcript(session_id: str, turn_number: int, role: str, content: str, metadata: dict = None):
    pool = await get_pool()
    await pool.execute(
        """INSERT INTO session_transcripts (id, session_id, turn_number, role, content, metadata)
           VALUES ($1, $2, $3, $4, $5, $6)""",
        uuid.uuid4(), uuid.UUID(session_id), turn_number, role, content,
        json.dumps(metadata or {}),
    )


async def get_session_transcript(session_id: str) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT turn_number, role, content, timestamp, metadata
           FROM session_transcripts
           WHERE session_id = $1
           ORDER BY turn_number, timestamp""",
        uuid.UUID(session_id),
    )
    return [_row_to_dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════
# REPORT CARD OPERATIONS
# ══════════════════════════════════════════════════════════════

async def save_report_card(session_id: str, user_id: str, report: dict) -> str:
    pool = await get_pool()
    report_id = uuid.uuid4()
    # Grading engine uses "overall_grade" not "letter_grade",
    # and "sales_style.detected" not "detected_sales_style"
    letter_grade = report.get("letter_grade") or report.get("overall_grade", "F")
    detected_style = (
        report.get("detected_sales_style")
        or (report.get("sales_style", {}).get("detected"))
        or "Unknown"
    )
    await pool.execute(
        """INSERT INTO report_cards
           (id, session_id, user_id, overall_score, letter_grade,
            close_probability, detected_style, categories, deal_killers, full_report)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
        report_id, uuid.UUID(session_id), uuid.UUID(user_id),
        report.get("overall_score", 0), letter_grade,
        report.get("close_probability", 0), detected_style,
        json.dumps(report.get("categories", {})),
        json.dumps(report.get("deal_killers", {})),
        json.dumps(report),
    )
    return str(report_id)


async def get_report_card(report_id: str) -> Optional[dict]:
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT rc.*, ts.client_info, ts.duration_seconds
           FROM report_cards rc
           LEFT JOIN training_sessions ts ON rc.session_id = ts.id
           WHERE rc.id = $1""",
        uuid.UUID(report_id),
    )
    return _row_to_dict(row) if row else None


async def get_report_card_by_session(session_id: str) -> Optional[dict]:
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT rc.*, ts.client_info, ts.duration_seconds
           FROM report_cards rc
           LEFT JOIN training_sessions ts ON rc.session_id = ts.id
           WHERE rc.session_id = $1""",
        uuid.UUID(session_id),
    )
    return _row_to_dict(row) if row else None


async def get_user_report_cards(user_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT rc.*, ts.client_info, ts.duration_seconds
           FROM report_cards rc
           JOIN training_sessions ts ON rc.session_id = ts.id
           WHERE rc.user_id = $1
           ORDER BY rc.created_at DESC
           LIMIT $2 OFFSET $3""",
        uuid.UUID(user_id), limit, offset,
    )
    return [_row_to_dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════
# ANALYTICS OPERATIONS
# ══════════════════════════════════════════════════════════════

async def get_analytics(user_id: str, days: int = 30) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT * FROM analytics_daily
           WHERE user_id = $1 AND date >= (CURRENT_DATE - $2::integer)
           ORDER BY date ASC""",
        uuid.UUID(user_id), days,
    )
    return [_row_to_dict(r) for r in rows]


async def compute_analytics_for_date(user_id: str, date: datetime) -> dict:
    """Compute daily analytics from report cards for a specific date."""
    pool = await get_pool()
    target_date = date.date() if isinstance(date, datetime) else date

    reports = await pool.fetch(
        """SELECT rc.full_report, ts.duration_seconds
           FROM report_cards rc
           JOIN training_sessions ts ON rc.session_id = ts.id
           WHERE rc.user_id = $1 AND DATE(rc.created_at) = $2""",
        uuid.UUID(user_id), target_date,
    )

    if not reports:
        return {}

    count = len(reports)
    total_minutes = sum(r["duration_seconds"] or 0 for r in reports) / 60.0

    # Aggregate scores from report cards
    # Map analytics DB column names → grading engine category keys
    score_key_map = {
        "tonality": "tonality",
        "rapport": "rapport_discovery",
        "questions": "question_quality",
        "compliance": "compliance_authority",
        "flow": "flow",
        "trust": "trust_building",
        "objection_handling": "objection_handling",
        "preframing": "preframing",
        "presentation": "presentation",
        "close": "resistance_management",
        "underwriting": "medical_underwriting",
    }
    avgs = {}
    for analytics_key, engine_key in score_key_map.items():
        scores = []
        for r in reports:
            report = json.loads(r["full_report"]) if isinstance(r["full_report"], str) else r["full_report"]
            categories = report.get("categories", {})
            # categories is a dict: {"tonality": {"score": 80, ...}, ...}
            if isinstance(categories, dict):
                cat = categories.get(engine_key)
                if cat and isinstance(cat, dict):
                    scores.append(cat.get("score", 0))
            elif isinstance(categories, list):
                # Legacy format: [{"name": "Tonality", "score": 80}, ...]
                for cat in categories:
                    if isinstance(cat, dict):
                        name = cat.get("name", "").lower().replace(" ", "_").replace("&", "").replace("/", "_")
                        if name == analytics_key or name == engine_key:
                            scores.append(cat.get("score", 0))
                            break
        avgs[f"avg_{analytics_key}"] = sum(scores) / len(scores) if scores else 0

    overall_scores = []
    close_probs = []
    styles = {}
    objections_faced = 0
    objections_resolved = 0

    for r in reports:
        report = json.loads(r["full_report"]) if isinstance(r["full_report"], str) else r["full_report"]
        overall_scores.append(report.get("overall_score", 0))
        close_probs.append(report.get("close_probability", 0))
        style = report.get("detected_sales_style", "unknown")
        styles[style] = styles.get(style, 0) + 1
        dk = report.get("deal_killers", {})
        objections_faced += dk.get("total_objections", 0)
        objections_resolved += dk.get("resolved_objections", 0)

    analytics = {
        "user_id": user_id,
        "date": str(target_date),
        "sessions_count": count,
        "total_minutes": total_minutes,
        "avg_overall": sum(overall_scores) / len(overall_scores) if overall_scores else 0,
        "avg_close_probability": sum(close_probs) / len(close_probs) if close_probs else 0,
        "objections_faced": objections_faced,
        "objections_resolved": objections_resolved,
        "style_distribution": styles,
        **avgs,
    }

    # Upsert into analytics_daily
    await pool.execute(
        """INSERT INTO analytics_daily (id, user_id, date, sessions_count, total_minutes,
               avg_overall, avg_tonality, avg_rapport, avg_questions, avg_compliance,
               avg_flow, avg_trust, avg_objection_handling, avg_preframing,
               avg_presentation, avg_close, avg_underwriting,
               objections_faced, objections_resolved, style_distribution, avg_close_probability)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
           ON CONFLICT (user_id, date) DO UPDATE SET
               sessions_count = EXCLUDED.sessions_count,
               total_minutes = EXCLUDED.total_minutes,
               avg_overall = EXCLUDED.avg_overall,
               avg_close_probability = EXCLUDED.avg_close_probability""",
        uuid.uuid4(), uuid.UUID(user_id), target_date,
        count, total_minutes, analytics["avg_overall"],
        avgs.get("avg_tonality", 0), avgs.get("avg_rapport", 0),
        avgs.get("avg_questions", 0), avgs.get("avg_compliance", 0),
        avgs.get("avg_flow", 0), avgs.get("avg_trust", 0),
        avgs.get("avg_objection_handling", 0), avgs.get("avg_preframing", 0),
        avgs.get("avg_presentation", 0), avgs.get("avg_close", 0),
        avgs.get("avg_underwriting", 0),
        objections_faced, objections_resolved,
        json.dumps(styles), analytics["avg_close_probability"],
    )

    return analytics


# ══════════════════════════════════════════════════════════════
# WALLET TRANSACTION HISTORY
# ══════════════════════════════════════════════════════════════

async def get_wallet_transactions(user_id: str, limit: int = 50) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT * FROM wallet_transactions
           WHERE user_id = $1
           ORDER BY created_at DESC
           LIMIT $2""",
        uuid.UUID(user_id), limit,
    )
    return [_row_to_dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════
# CALL RECORDINGS
# ══════════════════════════════════════════════════════════════

async def save_call_recording(user_id: str, recording_data: dict) -> str:
    pool = await get_pool()
    rec_id = uuid.uuid4()
    await pool.execute(
        """INSERT INTO call_recordings
           (id, user_id, twilio_recording_sid, twilio_call_sid,
            recording_url, duration_seconds, call_date, caller_number, agent_name)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
        rec_id, uuid.UUID(user_id),
        recording_data.get("recording_sid"), recording_data.get("call_sid"),
        recording_data.get("recording_url"), recording_data.get("duration"),
        recording_data.get("call_date"), recording_data.get("caller_number"),
        recording_data.get("agent_name"),
    )
    return str(rec_id)


async def get_call_recordings(user_id: str, limit: int = 50) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT * FROM call_recordings
           WHERE user_id = $1
           ORDER BY call_date DESC
           LIMIT $2""",
        uuid.UUID(user_id), limit,
    )
    return [_row_to_dict(r) for r in rows]


async def update_recording_report(recording_id: str, transcript: dict, report: dict):
    pool = await get_pool()
    await pool.execute(
        """UPDATE call_recordings
           SET status = 'completed', transcript = $1, report_card = $2, processed_at = NOW()
           WHERE id = $3""",
        json.dumps(transcript), json.dumps(report), uuid.UUID(recording_id),
    )


# ══════════════════════════════════════════════════════════════
# SETTINGS
# ══════════════════════════════════════════════════════════════

async def get_settings(user_id: str) -> dict:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM training_settings WHERE user_id = $1", uuid.UUID(user_id)
    )
    if row:
        return _row_to_dict(row)
    # Create default settings
    await pool.execute(
        "INSERT INTO training_settings (id, user_id) VALUES ($1, $2)",
        uuid.uuid4(), uuid.UUID(user_id),
    )
    return {"user_id": user_id, "preferred_voice": "Sal", "auto_import_recordings": False}


async def update_settings(user_id: str, settings: dict):
    pool = await get_pool()
    allowed = [
        "preferred_voice", "auto_import_recordings",
        "grokbot_account_linked", "dialer_connection_code",
        "grokbot_api_key", "twilio_account_sid", "twilio_auth_token",
        "email_weekly_report", "email_session_summary",
    ]
    updates = {k: v for k, v in settings.items() if k in allowed}
    if not updates:
        return
    set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates.keys()))
    values = [uuid.UUID(user_id)] + list(updates.values())
    await pool.execute(
        f"UPDATE training_settings SET {set_clauses} WHERE user_id = $1",
        *values,
    )


# ══════════════════════════════════════════════════════════════
# MODULE SESSION OPERATIONS
# ══════════════════════════════════════════════════════════════

async def create_module_session(
    user_id: str, module_key: str, voice_name: str = "Sal"
) -> dict:
    pool = await get_pool()
    session_id = uuid.uuid4()
    await pool.execute(
        """INSERT INTO module_sessions (id, user_id, module_key, voice_name)
           VALUES ($1, $2, $3, $4)""",
        session_id, uuid.UUID(user_id), module_key, voice_name,
    )
    return {"id": str(session_id), "module_key": module_key, "status": "active"}


async def end_module_session(
    session_id: str, duration_seconds: int, session_state: dict,
    feedback_summary: str, billed_minutes: int = 0, cost_cents: int = 0,
    billed_from: str = "subscription",
) -> dict:
    pool = await get_pool()
    await pool.execute(
        """UPDATE module_sessions
           SET status = 'completed', ended_at = NOW(),
               duration_seconds = $1, session_state = $2,
               feedback_summary = $3, billed_minutes = $4,
               cost_cents = $5, billed_from = $6
           WHERE id = $7""",
        duration_seconds, json.dumps(session_state), feedback_summary,
        billed_minutes, cost_cents, billed_from, uuid.UUID(session_id),
    )
    return {"id": session_id, "status": "completed"}


async def get_module_sessions(user_id: str, module_key: str = None, limit: int = 50) -> list[dict]:
    pool = await get_pool()
    if module_key:
        rows = await pool.fetch(
            """SELECT * FROM module_sessions
               WHERE user_id = $1 AND module_key = $2
               ORDER BY started_at DESC LIMIT $3""",
            uuid.UUID(user_id), module_key, limit,
        )
    else:
        rows = await pool.fetch(
            """SELECT * FROM module_sessions
               WHERE user_id = $1
               ORDER BY started_at DESC LIMIT $2""",
            uuid.UUID(user_id), limit,
        )
    return [_row_to_dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════
# HOMEWORK OPERATIONS
# ══════════════════════════════════════════════════════════════

async def save_homework_report(user_id: str, report: dict) -> str:
    pool = await get_pool()
    report_id = uuid.uuid4()
    await pool.execute(
        """INSERT INTO homework_reports
           (id, user_id, sessions_analyzed, overall_assessment,
            strengths, weaknesses, assignments, focus_order)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
        report_id, uuid.UUID(user_id),
        report["sessions_analyzed"], report["overall_assessment"],
        json.dumps(report["strengths"]), json.dumps(report["weaknesses"]),
        json.dumps(report["assignments"]), json.dumps(report["focus_order"]),
    )
    return str(report_id)


async def get_latest_homework(user_id: str) -> Optional[dict]:
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT * FROM homework_reports
           WHERE user_id = $1
           ORDER BY created_at DESC LIMIT 1""",
        uuid.UUID(user_id),
    )
    return _row_to_dict(row) if row else None


async def get_homework_history(user_id: str, limit: int = 10) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT * FROM homework_reports
           WHERE user_id = $1
           ORDER BY created_at DESC LIMIT $2""",
        uuid.UUID(user_id), limit,
    )
    return [_row_to_dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════
# USER SCRIPTS
# ══════════════════════════════════════════════════════════════

async def save_user_script(
    user_id: str, name: str, content: str, source: str = "paste"
) -> dict:
    pool = await get_pool()
    script_id = uuid.uuid4()
    char_count = len(content)
    await pool.execute(
        """INSERT INTO user_scripts (id, user_id, name, content, char_count, source)
           VALUES ($1, $2, $3, $4, $5, $6)""",
        script_id, uuid.UUID(user_id), name, content, char_count, source,
    )
    return {"id": str(script_id), "name": name, "char_count": char_count}


async def get_user_scripts(user_id: str, limit: int = 50) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT id, name, char_count, source, created_at, updated_at
           FROM user_scripts
           WHERE user_id = $1
           ORDER BY updated_at DESC LIMIT $2""",
        uuid.UUID(user_id), limit,
    )
    return [_row_to_dict(r) for r in rows]


async def get_user_script(user_id: str, script_id: str) -> dict | None:
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT * FROM user_scripts
           WHERE id = $1 AND user_id = $2""",
        uuid.UUID(script_id), uuid.UUID(user_id),
    )
    return _row_to_dict(row) if row else None


async def update_user_script(
    user_id: str, script_id: str, name: str = None, content: str = None
) -> dict | None:
    pool = await get_pool()
    parts = []
    args = []
    idx = 1

    if name is not None:
        parts.append(f"name = ${idx}")
        args.append(name)
        idx += 1
    if content is not None:
        parts.append(f"content = ${idx}")
        args.append(content)
        idx += 1
        parts.append(f"char_count = ${idx}")
        args.append(len(content))
        idx += 1

    if not parts:
        return await get_user_script(user_id, script_id)

    args.append(uuid.UUID(script_id))
    args.append(uuid.UUID(user_id))
    query = f"""UPDATE user_scripts SET {', '.join(parts)}
                WHERE id = ${idx} AND user_id = ${idx + 1}
                RETURNING id, name, char_count, source, created_at, updated_at"""
    row = await pool.fetchrow(query, *args)
    return _row_to_dict(row) if row else None


async def delete_user_script(user_id: str, script_id: str) -> bool:
    pool = await get_pool()
    result = await pool.execute(
        """DELETE FROM user_scripts
           WHERE id = $1 AND user_id = $2""",
        uuid.UUID(script_id), uuid.UUID(user_id),
    )
    return result.endswith("1")

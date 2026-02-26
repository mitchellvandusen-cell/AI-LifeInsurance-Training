"""
Seed the database with a beta test user.

Can be run standalone:  python -m database.seed
Or called from app startup via seed_beta_user().
"""

from __future__ import annotations

import uuid

import bcrypt

# ── Beta test account credentials ─────────────────────────
BETA_EMAIL = "insurancegrokbot@insurancegrokbot.click"
BETA_PASSWORD = "insurancegrokbot"
BETA_NAME = "Beta Tester"


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def seed_beta_user():
    """Create the beta test user if they don't already exist.

    Gives them an active subscription with unlimited minutes and wallet balance
    so every feature can be tested without Stripe.
    """
    from src.core.database import get_pool

    pool = await get_pool()

    # Check if user exists
    existing = await pool.fetchrow(
        "SELECT id FROM users WHERE email = $1", BETA_EMAIL
    )
    if existing:
        print(f"[SEED] Beta user already exists ({BETA_EMAIL})")
        return

    user_id = uuid.uuid4()
    password_hash = _hash(BETA_PASSWORD)

    # 1. Create user
    await pool.execute(
        """INSERT INTO users (id, email, password_hash, name, created_at)
           VALUES ($1, $2, $3, $4, NOW())""",
        user_id, BETA_EMAIL, password_hash, BETA_NAME,
    )

    # 2. Create active subscription with unlimited minutes + unlimited wallet
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=365)  # 1 year so it doesn't expire during testing

    sub_id = uuid.uuid4()
    await pool.execute(
        """INSERT INTO training_subscriptions
           (id, user_id, stripe_customer_id, plan_status,
            included_minutes_total, included_minutes_used,
            billing_period_start, billing_period_end, wallet_balance_cents)
           VALUES ($1, $2, $3, 'active', 999999, 0, $4, $5, 99999999)""",
        sub_id, user_id, "beta_test_account", now, period_end,
    )

    # 3. Create default training settings
    await pool.execute(
        "INSERT INTO training_settings (id, user_id) VALUES ($1, $2)",
        uuid.uuid4(), user_id,
    )

    print(f"[SEED] Beta user created successfully!")
    print(f"       Email:    {BETA_EMAIL}")
    print(f"       Password: {BETA_PASSWORD}")
    print(f"       Sub:      active | 999,999 min | $999,999.99 wallet")


async def _main():
    import asyncpg, os
    from dotenv import load_dotenv

    load_dotenv()
    pool = await asyncpg.create_pool(dsn=os.getenv("DATABASE_URL"), min_size=1, max_size=2)

    # Patch get_pool to return our pool
    import src.core.database as db
    db._pool = pool

    await seed_beta_user()
    await pool.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(_main())

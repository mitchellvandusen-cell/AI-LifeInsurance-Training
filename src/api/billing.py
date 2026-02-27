"""
Billing routes: Stripe subscriptions, add-ons, wallet management.
"""

from __future__ import annotations

import os

import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.api.middleware import get_current_user
from src.core import database as db

router = APIRouter(prefix="/api/billing", tags=["billing"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Stripe Price IDs (configure in Stripe Dashboard)
PRICE_MONTHLY = os.getenv("STRIPE_PRICE_MONTHLY", "")       # $49.99/mo
PRICE_ADDON_2HR = os.getenv("STRIPE_PRICE_ADDON_2HR", "")   # $12
PRICE_ADDON_4HR = os.getenv("STRIPE_PRICE_ADDON_4HR", "")   # $24


class CreateCheckoutRequest(BaseModel):
    plan: str = "monthly"  # monthly, addon_2hr, addon_4hr


class WalletTopUpRequest(BaseModel):
    amount_cents: int  # Amount in cents to add


@router.get("/subscription")
async def get_subscription(request: Request):
    user = get_current_user(request)
    sub = await db.get_subscription(user["user_id"])
    remaining = await db.get_remaining_minutes(user["user_id"])
    return {
        "subscription": sub,
        "remaining": remaining,
    }


@router.post("/checkout")
async def create_checkout(req: CreateCheckoutRequest, request: Request):
    """Create a Stripe Checkout session for subscription or add-on."""
    user = get_current_user(request)
    user_data = await db.get_user_by_id(user["user_id"])

    # Get or create Stripe customer
    sub = await db.get_subscription(user["user_id"])
    customer_id = sub.get("stripe_customer_id") if sub else None

    if not customer_id:
        customer = stripe.Customer.create(
            email=user_data["email"],
            metadata={"user_id": user["user_id"]},
        )
        customer_id = customer.id

    # Determine price and mode
    if req.plan == "monthly":
        price_id = PRICE_MONTHLY
        mode = "subscription"
    elif req.plan == "addon_2hr":
        price_id = PRICE_ADDON_2HR
        mode = "payment"
    elif req.plan == "addon_4hr":
        price_id = PRICE_ADDON_4HR
        mode = "payment"
    else:
        raise HTTPException(status_code=400, detail="Invalid plan")

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        mode=mode,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=os.getenv("APP_URL", "http://localhost:8000") + "/dashboard?billing=success",
        cancel_url=os.getenv("APP_URL", "http://localhost:8000") + "/billing?billing=cancelled",
        metadata={
            "user_id": user["user_id"],
            "plan": req.plan,
        },
    )

    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/wallet/topup")
async def wallet_topup(req: WalletTopUpRequest, request: Request):
    """Create a Stripe payment for wallet top-up."""
    user = get_current_user(request)

    if req.amount_cents < 100:
        raise HTTPException(status_code=400, detail="Minimum top-up is $1.00")
    if req.amount_cents > 50000:
        raise HTTPException(status_code=400, detail="Maximum top-up is $500.00")

    sub = await db.get_subscription(user["user_id"])
    customer_id = sub.get("stripe_customer_id") if sub else None

    if not customer_id:
        user_data = await db.get_user_by_id(user["user_id"])
        customer = stripe.Customer.create(
            email=user_data["email"],
            metadata={"user_id": user["user_id"]},
        )
        customer_id = customer.id

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "unit_amount": req.amount_cents,
                "product_data": {"name": "Training Wallet Top-Up"},
            },
            "quantity": 1,
        }],
        success_url=os.getenv("APP_URL", "http://localhost:8000") + "/billing?topup=success",
        cancel_url=os.getenv("APP_URL", "http://localhost:8000") + "/billing?topup=cancelled",
        metadata={
            "user_id": user["user_id"],
            "type": "wallet_topup",
            "amount_cents": str(req.amount_cents),
        },
    )

    return {"checkout_url": session.url, "session_id": session.id}


@router.get("/wallet/transactions")
async def get_wallet_transactions(request: Request, limit: int = 50):
    user = get_current_user(request)
    return await db.get_wallet_transactions(user["user_id"], limit)


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user_id = data.get("metadata", {}).get("user_id")
        plan = data.get("metadata", {}).get("plan")
        payment_id = data.get("payment_intent") or data.get("subscription")

        if not user_id:
            return {"ok": True}

        if plan == "monthly":
            # Activate subscription
            await db.update_subscription_status(user_id, "active")

        elif plan == "addon_2hr":
            # Add 120 minutes
            pool = await db.get_pool()
            import uuid
            await pool.execute(
                """INSERT INTO addon_purchases
                   (id, user_id, subscription_id, package_type, minutes_total, price_cents,
                    stripe_payment_id, billing_period_start, billing_period_end)
                   SELECT $1, $2, ts.id, '2hr', 120, 1200, $3, ts.billing_period_start, ts.billing_period_end
                   FROM training_subscriptions ts WHERE ts.user_id = $2""",
                uuid.uuid4(), __import__("uuid").UUID(user_id), payment_id,
            )

        elif plan == "addon_4hr":
            pool = await db.get_pool()
            import uuid
            await pool.execute(
                """INSERT INTO addon_purchases
                   (id, user_id, subscription_id, package_type, minutes_total, price_cents,
                    stripe_payment_id, billing_period_start, billing_period_end)
                   SELECT $1, $2, ts.id, '4hr', 240, 2400, $3, ts.billing_period_start, ts.billing_period_end
                   FROM training_subscriptions ts WHERE ts.user_id = $2""",
                uuid.uuid4(), __import__("uuid").UUID(user_id), payment_id,
            )

        elif data.get("metadata", {}).get("type") == "wallet_topup":
            amount = int(data["metadata"].get("amount_cents", 0))
            if amount > 0:
                await db.add_wallet_funds(user_id, amount, payment_id)

    elif event_type == "customer.subscription.deleted":
        # Subscription cancelled
        customer_id = data.get("customer")
        pool = await db.get_pool()
        row = await pool.fetchrow(
            "SELECT user_id FROM training_subscriptions WHERE stripe_customer_id = $1",
            customer_id,
        )
        if row:
            await db.update_subscription_status(str(row["user_id"]), "cancelled")

    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        pool = await db.get_pool()
        row = await pool.fetchrow(
            "SELECT user_id FROM training_subscriptions WHERE stripe_customer_id = $1",
            customer_id,
        )
        if row:
            await db.update_subscription_status(str(row["user_id"]), "past_due")

    return {"ok": True}


@router.post("/portal")
async def create_portal_session(request: Request):
    """Create a Stripe Customer Portal session for billing management."""
    user = get_current_user(request)
    sub = await db.get_subscription(user["user_id"])

    if not sub or not sub.get("stripe_customer_id"):
        raise HTTPException(status_code=400, detail="No billing account found")

    session = stripe.billing_portal.Session.create(
        customer=sub["stripe_customer_id"],
        return_url=os.getenv("APP_URL", "http://localhost:8000") + "/billing",
    )

    return {"portal_url": session.url}

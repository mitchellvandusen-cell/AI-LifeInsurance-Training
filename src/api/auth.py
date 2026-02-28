"""
Authentication routes: login, register, session management.
"""

from __future__ import annotations

import bcrypt
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from src.api.middleware import create_token, get_current_user
from src.core import database as db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    new_password: str
    confirm_password: str


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


@router.post("/register")
async def register(req: RegisterRequest, response: Response):
    # Check if user exists
    existing = await db.get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create user
    password_hash = _hash_password(req.password)
    user = await db.create_user(req.email, password_hash, req.name)

    # Create training subscription (inactive until they subscribe)
    await db.create_subscription(user["id"])

    # Create default settings
    await db.get_settings(user["id"])

    # Generate token
    token = create_token(user["id"], user["email"])

    # Set HTTP-only cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=86400,
    )

    return {
        "user": {"id": user["id"], "email": user["email"], "name": user["name"]},
        "token": token,
    }


@router.post("/login")
async def login(req: LoginRequest, response: Response):
    user = await db.get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Strip any stray whitespace/null bytes from stored hash
    stored_hash = user["password_hash"].strip().replace("\x00", "")
    if not _verify_password(req.password, stored_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(str(user["id"]), user["email"])

    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=86400,
    )

    return {
        "user": {"id": str(user["id"]), "email": user["email"], "name": user.get("name", "")},
        "token": token,
    }


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, request: Request):
    user = get_current_user(request)
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    password_hash = _hash_password(req.new_password)
    await db.update_password(user["user_id"], password_hash)
    return {"ok": True}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("session_token")
    return {"ok": True}


@router.get("/me")
async def get_me(request: Request):
    user_info = get_current_user(request)
    user = await db.get_user_by_id(user_info["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sub = await db.get_subscription(user_info["user_id"])
    remaining = await db.get_remaining_minutes(user_info["user_id"])

    return {
        "user": {
            "id": str(user["id"]),
            "email": user["email"],
            "name": user.get("name", ""),
        },
        "subscription": {
            "status": sub["plan_status"] if sub else "inactive",
            "included_minutes_remaining": remaining["subscription_minutes"],
            "wallet_balance_cents": remaining["wallet_cents"],
            "addon_minutes_remaining": remaining["addon_minutes"],
        },
    }

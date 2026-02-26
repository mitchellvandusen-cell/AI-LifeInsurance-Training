"""
Authentication middleware for the training platform.
JWT-based auth with HTTP-only cookie support.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from fastapi import HTTPException, Request, WebSocket

SECRET_KEY = os.getenv("JWT_SECRET", "change-me-in-production-InsuranceGrokBot-2026")
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24


def create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(request: Request) -> dict:
    """Extract and validate user from request.
    Checks Authorization header first, then cookie.
    """
    token = None

    # Check Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]

    # Check cookie
    if not token:
        token = request.cookies.get("session_token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(token)
    return {"user_id": payload["sub"], "email": payload["email"]}


async def get_ws_user(websocket: WebSocket) -> dict:
    """Extract user from WebSocket connection.
    Checks query param 'token' or cookie.
    """
    token = websocket.query_params.get("token")
    if not token:
        token = websocket.cookies.get("session_token")
    if not token:
        await websocket.close(code=4001, reason="Not authenticated")
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"user_id": payload["sub"], "email": payload["email"]}
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        await websocket.close(code=4001, reason="Invalid token")
        return None

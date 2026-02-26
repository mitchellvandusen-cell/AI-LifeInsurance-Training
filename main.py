"""
InsuranceGrokBot — AI Sales Training for Life Insurance Agents
Entry point for the FastAPI server.

Mounts all API routers and serves the frontend static files.
"""

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent

from src.config import config
from src.core import database as db

# ── App Factory ──────────────────────────────────────────────

app = FastAPI(
    title="InsuranceGrokBot Training",
    description="AI Sales Training Platform for Life Insurance Agents",
    version="2.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Lifecycle ────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    await db.get_pool()

    # Seed beta test user on first boot
    from database.seed import seed_beta_user
    try:
        await seed_beta_user()
    except Exception as e:
        print(f"[SEED] Skipped: {e}")


@app.on_event("shutdown")
async def shutdown():
    await db.close_pool()


# ── Mount API Routers ────────────────────────────────────────

from src.api.auth import router as auth_router          # noqa: E402
from src.api.sessions import router as sessions_router    # noqa: E402
from src.api.billing import router as billing_router      # noqa: E402
from src.api.analytics import router as analytics_router  # noqa: E402
from src.api.recordings import router as recordings_router  # noqa: E402
from src.api.settings import router as settings_router    # noqa: E402

app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(billing_router)
app.include_router(analytics_router)
app.include_router(recordings_router)
app.include_router(settings_router)


# ── Legacy API Routes (original text-based training) ─────────
# Keep the original routes module for backwards compatibility
from src.api.routes import app as legacy_app  # noqa: E402

# Mount original session endpoints under /v1 prefix
for route in legacy_app.routes:
    if hasattr(route, "path") and route.path != "/":
        app.routes.append(route)


# ── Health Check ─────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


# ── Serve Frontend Static Files ──────────────────────────────
# Must be last so API routes take priority

app.mount("/", StaticFiles(directory=str(BASE_DIR / "frontend"), html=True), name="frontend")


# ── CLI Entry Point ──────────────────────────────────────────

def main():
    warnings = config.validate()
    for w in warnings:
        print(f"[WARNING] {w}")

    print("=" * 60)
    print("  InsuranceGrokBot — AI Sales Training Platform")
    print("=" * 60)
    print(f"  Server:  http://{config.host}:{config.port}")
    print(f"  API:     http://{config.host}:{config.port}/docs")
    print(f"  Frontend: http://{config.host}:{config.port}/")
    print("=" * 60)

    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
    )


if __name__ == "__main__":
    main()

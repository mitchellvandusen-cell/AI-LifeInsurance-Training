"""
InsuranceGrokBot — AI Sales Training for Life Insurance Agents
Entry point for the FastAPI server.

Mounts all API routers and serves the frontend static files.
"""

from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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

    # Create every table on a fresh database (safe to re-run)
    await db.init_schema()

    # Seed beta test user on first boot
    from database.seed import seed_beta_user
    try:
        await seed_beta_user()
    except Exception as e:
        print(f"[SEED] Skipped: {e}")

    # Debug: verify frontend directory
    frontend_dir = BASE_DIR / "frontend"
    if frontend_dir.is_dir():
        files = list(frontend_dir.glob("*.html"))
        print(f"[STATIC] Frontend dir: {frontend_dir} ({len(files)} HTML files)")
    else:
        print(f"[STATIC] WARNING: Frontend dir not found at {frontend_dir}")


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
from src.api.modules import router as modules_router      # noqa: E402

app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(billing_router)
app.include_router(analytics_router)
app.include_router(recordings_router)
app.include_router(settings_router)
app.include_router(modules_router)


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
# Mount CSS/JS/assets as static directories, then catch-all for HTML pages.

FRONTEND_DIR = BASE_DIR / "frontend"

for _name in ("css", "js", "assets", "images", "fonts"):
    _subdir = FRONTEND_DIR / _name
    if _subdir.is_dir():
        app.mount(f"/{_name}", StaticFiles(directory=str(_subdir)), name=_name)


@app.get("/{path:path}")
async def serve_frontend(path: str):
    """Catch-all: serve HTML pages from the frontend directory."""
    # Direct file match (e.g. favicon.ico, robots.txt)
    file_path = FRONTEND_DIR / path
    if file_path.is_file():
        return FileResponse(file_path)

    # Append .html (e.g. /login → login.html)
    html_path = FRONTEND_DIR / f"{path}.html"
    if html_path.is_file():
        return FileResponse(html_path, media_type="text/html")

    # Directory index (e.g. / → index.html)
    index_path = FRONTEND_DIR / path / "index.html"
    if index_path.is_file():
        return FileResponse(index_path, media_type="text/html")

    # Root fallback
    if not path or path == "/":
        return FileResponse(FRONTEND_DIR / "index.html", media_type="text/html")

    raise HTTPException(status_code=404, detail="Page not found")


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

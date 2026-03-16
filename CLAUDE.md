# CLAUDE.md — AI Life Insurance Sales Training Platform

## What This Project Is

An AI-powered sales training platform for life insurance agents. Agents practice selling against a realistic AI client (powered by xAI Grok) that has hidden behavioral scores (trust, authority, resistance) driving its responses. The platform grades performance, tracks progress across sessions, and imports real call recordings from the InsuranceGrokBot Dialer for analysis.

**Live domain:** insurancegrokbot.com

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | **FastAPI** (Python 3.11+, async/await throughout) |
| Database | **PostgreSQL** via Neon, **asyncpg** driver, UUID primary keys |
| LLM | **xAI Grok** (`grok4-1-fast-reasoning`) via OpenAI-compatible SDK |
| Voice | **xAI Realtime API** (WebSocket `wss://api.x.ai/v1/realtime`) |
| Billing | **Stripe** (subscriptions, add-ons, wallet) |
| Frontend | **Vanilla HTML/CSS/JS** (no build step, 15 pages) |
| Auth | **JWT** (HS256, 24hr expiry) + HTTP-only cookies + bcrypt |
| Deploy | **Heroku** (Procfile) |

---

## How to Run

```bash
# Local dev
pip install -r requirements.txt
cp .env.example .env  # fill in values
python main.py        # starts at http://localhost:8000

# Production (Heroku)
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --ws-ping-interval 20 --ws-ping-timeout 30 --timeout-keep-alive 120
```

**Startup sequence:** Load env → connect DB pool → run schema init (idempotent IF NOT EXISTS) → seed beta user → start session cleanup tasks → mount routers → serve static files.

**Health check:** `GET /api/health` → `{"status": "ok", "version": "2.0.0"}`

---

## Environment Variables

**Required:**
- `DATABASE_URL` — PostgreSQL connection string (Neon)
- `XAI_API_KEY` — xAI API key for Grok LLM + voice
- `JWT_SECRET` — random string for token signing
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` — Stripe billing
- `STRIPE_PRICE_MONTHLY`, `STRIPE_PRICE_ADDON_2HR`, `STRIPE_PRICE_ADDON_4HR` — Stripe price IDs
- `APP_URL` — base URL for redirects

**Optional:**
- `GROKBOT_API_URL` — Dialer API endpoint (default: `https://insurancegrokbot.com/api/v1/training`)
- `LLM_MODEL` — model override (default: `grok4-1-fast-reasoning`)
- `HOST` (default `0.0.0.0`), `PORT` (default `8000`), `DEBUG` (default `false`)

---

## Project Structure

```
main.py                            # FastAPI entry point & startup
src/
  config.py                        # Thresholds, LLM settings, score defaults
  api/
    auth.py                        # Register/login/logout (JWT + cookies)
    sessions.py                    # Training sessions + WebSocket voice streaming
    billing.py                     # Stripe subscriptions, add-ons, wallet
    analytics.py                   # KPI dashboard, trends
    recordings.py                  # Call recording import from Dialer API
    settings.py                    # User prefs, Dialer account linking
    modules.py                     # Focused training modules
    routes.py                      # Legacy v1 text-based routes
    middleware.py                   # JWT extraction (get_current_user, get_ws_user)
  core/
    database.py                    # Schema + all DB operations (~1400 lines)
    orchestrator.py                # Central controller tying engines together
    state_manager.py               # SessionState mutations + score tracking
  engine/
    grading_engine.py              # Adaptive report card generation
    objection_engine.py            # Objection triggers + isolation logic
    phase_manager.py               # Phase detection + mandatory flag validation
    compliance_tracker.py          # Micro-agreements, compliance ladder
    persona_generator.py           # 8 archetypes + 6-Axis + FACE profiles
    tonality_processor.py          # Audio metadata → tonality snapshots
    homework_engine.py             # Cross-session pattern analysis
    module_report_generator.py     # Module-specific reports
  models/
    state.py                       # State machine (HiddenState, SessionState, enums)
  knowledge/
    sales_mastery.py               # Module definitions (Tonality, Questions, etc.)
    mastery_curriculum.py          # 35-day curriculum, 5 phases
  prompts/
    system_prompt.py               # Dynamic LLM system prompt with state injection
    module_prompts.py              # Module-specific expert directives
  services/
    voice.py                       # xAI WebSocket + TranscriptPipeline
database/
  seed.py                          # Beta user seeding
frontend/
  *.html                           # 15 pages (dashboard, training, analytics, etc.)
  css/main.css, css/mobile.css     # Dark theme styles
  js/api.js                        # HTTP client + token management
  js/mobile-nav.js                 # Mobile nav
tests/
  test_core.py                     # 20+ unit tests (run: python tests/test_core.py)
```

---

## API Routes

| Prefix | File | Key Endpoints |
|--------|------|---------------|
| `/api/auth` | `auth.py` | `POST /register`, `POST /login`, `POST /logout`, `GET /me` |
| `/api/sessions` | `sessions.py` | `POST /start`, `GET /{id}`, `WS /ws/{id}`, `POST /{id}/end` |
| `/api/billing` | `billing.py` | `GET /subscription`, `POST /checkout`, `POST /wallet/topup`, `POST /webhook` |
| `/api/recordings` | `recordings.py` | `GET /`, `POST /sync`, `GET /{id}`, `POST /{id}/analyze` |
| `/api/analytics` | `analytics.py` | `GET /overview`, `GET /sessions`, `GET /trends` |
| `/api/settings` | `settings.py` | `GET`, `POST`, `POST /connect`, `POST /disconnect` |
| `/api/modules` | `modules.py` | `GET /`, `POST /start`, `WS /ws/{id}`, `POST /{id}/homework` |
| `/api/health` | `main.py` | `GET` — returns `{"status": "ok"}` |

---

## Database (13 Tables)

Schema auto-creates on startup via `database.py:init_schema()` (all IF NOT EXISTS — idempotent). No migration framework.

**Key tables:** `users`, `training_subscriptions`, `training_sessions`, `session_transcripts`, `report_cards`, `wallet_transactions`, `addon_purchases`, `call_recordings`, `analytics_daily`, `training_settings`, `module_sessions`, `homework_assignments`, `script_uploads`

All use UUID primary keys. Complex data stored as JSONB (personas, reports, settings).

---

## Core Business Logic

### Training Session Flow
1. **Persona generated** — 8 archetypes (Skeptical Professional, Concerned Parent, etc.) with Chase Hughes 6-Axis model + FACE difficulty profile
2. **7-phase pipeline:** INTRO → RAPPORT_DISCOVERY → MEDICAL_UNDERWRITING → PREFRAMING → PRESENTATION → OBJECTION_HANDLING → CLOSE
3. **Hidden behavioral scores** drive AI responses: Trust (0-100), Authority (0-100), Sales Resistance, Rapport, Conviction, Engagement
4. **Objection system** — 3 types (Smokescreen, True, Condition) with isolation protocol (Truth Test → Singularity Test → Commitment Test), root causes (MONEY/TIME/DECISION_MAKER)
5. **Compliance tracking** — micro-agreements, compliance ladder, frame control detection
6. **Adaptive grading** — 11 categories, only grades phases that occurred, generates pros/consequences/deal-killers

### Per-Turn Processing Pipeline (Orchestrator)
1. Analyze agent turn (tonality, phase, flags, compliance)
2. Check objection triggers
3. Build system prompt with fresh state injection
4. Call Grok LLM → generate client response
5. Process client response for behavioral signals

### Focused Training Modules
Tonality, Questions, Rapport, Frame Control, Objection Handling, Preframing, Close, Script Practice, Full Call Simulation

### 35-Day Curriculum
5 phases: Foundation (1-7) → Connection (8-14) → Control (15-21) → Mastery (22-28) → Integration (29-35)

---

## External Integrations

### InsuranceGrokBot Dialer API
- Endpoint: `{GROKBOT_API_URL}/recordings` (Bearer token auth)
- Response format: recordings under `"recordings"` or `"data"` key, with `has_more` pagination flag
- Recording URLs: use `audio_url` field (not `recording_url` which is an internal proxy path)
- Connection flow: user enters connection code in Settings → validated against `/validate` → stored for sync

### xAI Grok
- Chat: OpenAI-compatible SDK, `https://api.x.ai/v1`
- Voice: WebSocket `wss://api.x.ai/v1/realtime`, 24kHz PCM audio
- Voices: Ara (F), Rex (M), Sal (neutral), Eve (F), Leo (M)
- TranscriptPipeline handles dedup, debounce, echo/stutter removal

### Stripe
- Monthly subscription, 2hr/4hr add-on packages
- Webhook at `POST /api/billing/webhook`
- Wallet balance for pay-as-you-go minutes

---

## Testing

```bash
python tests/test_core.py
```

20+ tests covering: state mutations, score clamping, phase advancement, objection lifecycle, compliance tracking, tonality processing, persona generation, conversation flow, deal-killer analysis.

---

## Common Pitfalls / Things to Know

1. **Database schema is in code** (`database.py:init_schema()`), not migration files. It runs on every startup.
2. **No frontend build step** — edit HTML/CSS/JS directly in `frontend/`.
3. **System prompt rebuilds every turn** with fresh state variables — no scripted dialogue.
4. **Session cleanup** runs as a background task every 5 minutes (2hr TTL for sessions, 4hr for modules).
5. **GROKBOT_API_URL** defaults to `insurancegrokbot.com` — the `.click` domain is deprecated.
6. **Auth works via both** Authorization header AND HTTP-only cookies (check `middleware.py`).
7. **WebSocket connections** use query param or cookie for auth (see `get_ws_user`).
8. **Stripe prices** are configured via env vars, not hardcoded.
9. **The frontend** uses `js/api.js` as a centralized HTTP client with automatic token refresh.
10. **Legacy routes** in `routes.py` exist for backwards compatibility — new work goes in the specific route files.

# EUREKA MULTIVERSE — Deployment Guide

> **Status: LOCAL DOCKER DEPLOYMENT VALIDATED.** This document records only what was
> actually built and tested on the working machine. Anything not exercised is stated
> explicitly as **not validated**.

---

## 1. Architecture (preserved)

The deployed runtime is **`src/eureka/universe`** (the governed 8-EM Work Runtime). The EM
order is preserved: **EM Core → EM Structurer → EM Descriptor → EM Predictor → EM Prescriptor →
EM Actioner → EM Installer → EM Publisher**.

- The parallel harness `src/eureka/foundation/cognitive/*` (which imports the local
  **`eureka_cognitive_sdk`**) is **NOT** part of the deployed runtime. A physical audit proved
  the server (`src.eureka.universe.server:app`) loads **0** `foundation` modules and imports the
  runtime **without** the SDK. The SDK is therefore excluded from the image (see §7).

```
Browser ──► EUREKA Frontend (nginx :80 / external 5173 in dev)
                 │   /api/* (same-origin)
                 ▼
             EUREKA Backend (uvicorn :8000)  ──►  DeepSeek API   (DEEPSEEK_API_KEY ONLY here)
```

## 2. Requirements

- **Backend:** Python **3.12** (image `python:3.12-slim`; verified runtime `3.12.6`).
- **Frontend build:** Node **22** (image `node:22-alpine`); runtime nginx `1.27-alpine`.
- **No database.** The runtime keeps works/evidence in process memory (see §13).

## 3. Python — runtime environment

`requirements.txt` (pinned to versions installed + verified working in the functional env,
resolved via a real `pip install` in the image; `scipy` is included explicitly because the
server imports `scikit-fuzzy` at startup via the evolution router):

```
fastapi==0.110.0      uvicorn==0.30.1       pydantic==2.13.4      python-multipart==0.0.9
openai==2.21.0        python-dotenv==1.0.1  requests==2.34.2
reportlab==5.0.0      python-pptx==1.0.2    python-docx==1.1.0    matplotlib==3.9.0
scikit-fuzzy==0.5.0   scipy==1.17.1         numpy==2.2.6          pandas==3.0.3
openpyxl==3.1.5       pypdf==6.16.1
```
`requirements-dev.txt` adds `pytest==9.1.1` (development/tests only).

> Note: `reportlab`/`matplotlib`/`pandas`/`openpyxl`/`pypdf`/`python-pptx`/`python-docx` are used by
> the artifact-export / evidence / analytics capabilities. The server starts without some of them,
> but those EUREKA capabilities require them — so they are part of the runtime image.

## 4. Frontend — build

- `package.json` / `package-lock.json` → `npm ci` (reproducible); `npm run build` = `tsc -b && vite build`.
- Output: `dist/`. The production image serves `dist/` via **nginx** and **reverse-proxies `/api`
  to the backend** (same-origin; the backend is not exposed to the browser).
- **No `DEEPSEEK_API_KEY`** is present in the frontend image or bundle (see §12).

## 5. Variables de entorno (`.env.example` → `.env`)

Secrets are never committed. `.env` (repo root) is git-ignored; `.env.example` documents the vars.

| Variable | Default | Notes |
|---|---|---|
| `DEEPSEEK_API_KEY` | *(empty)* | **Secret. Backend only.** Missing → `/api/copilot` returns 500 `MISSING_DEEPSEEK_API_KEY` and the cognitive engine fails closed. |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | OpenAI-compatible endpoint. |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Served model. |
| `COGNITIVE_ENGINE` | `deepseek` | `deepseek` \| `ollama` \| `test_double`. |
| `OLLAMA_MODEL` | `deepseek-r1:14b` | Used when `COGNITIVE_ENGINE=ollama`. |
| `EUREKA_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated browser origins allowed to call the backend directly. In Docker the frontend uses same-origin via nginx. Set to `*` → credentials disabled. |
| `VITE_EUREKA_API_URL` | `http://localhost:5173` | Frontend build-time origin used to reach its own `/api` (only a route base, never a secret). |

## 6. Docker

- **`Dockerfile.backend`** — `python:3.12-slim`, non-root `eureka` user, `WORKDIR /app`,
  `PYTHONPATH=/app`, installs `requirements.txt`, copies **only** `src/`, exposes `8000`, runs
  `python -m uvicorn src.eureka.universe.server:app --host 0.0.0.0 --port 8000` (no reload),
  `HEALTHCHECK` → `GET /api/health`.
- **`eureka-frontend/Dockerfile`** — multi-stage: `node:22-alpine` (`npm ci` → `npm run build`)
  → `nginx:1.27-alpine` serving `dist/` + `nginx.conf` proxy.
- **`docker-compose.yml`** — services `backend` (8000) + `frontend` (5173→80), no DB.
- **`.dockerignore`** (root + `eureka-frontend`) — excludes `.git`, `.env*`, caches,
  `node_modules`, `dist`, backups, scratch, and unrelated project folders. **Never excludes
  `src/` or the requirements files.**

## 7. eureka_cognitive_sdk

**Excluded from the deployment** (decisión definitiva). It is local code under
`airl-compiler/src/eureka-cognitive-sdk/` (own `pyproject.toml`, deps `pydantic>=2.0.0` +
`python-dotenv`), but it is used **only** by the parallel `src/eureka/foundation/cognitive/*`
harness, which the deployed runtime does not import. It is **not** required for the 8-EM runtime
and is **not** installed artificially.

## 8. DeepSeek (validated)

`POST /api/copilot` (backend endpoint) forwards to `{DEEPSEEK_BASE_URL}/chat/completions` with
`Authorization: Bearer <key>` (key read from the backend env). **Validated in the running
container:** returned `choices[0].message.content` with `model=deepseek-v4-flash`. The key never
leaves the backend; the browser only talks to the EUREKA backend.

## 9. Ollama (preserved, NOT validated with a real instance)

`COGNITIVE_ENGINE=ollama` selects `OllamaProvider` (`ollama_provider.py`), default
`base_url=http://127.0.0.1:11434`, `timeout=1200`, `from {base_url}/api/generate`, model
`OLLAMA_MODEL`. It is **not** part of the default compose and was **not** exercised against a live
Ollama instance — so it is documented as supported-by-code but **not validated** here.

## 10. Healtchecks (validated)

- Backend: `GET /api/health` → `{"status":"OK"}`. Docker `HEALTHCHECK` reported **healthy**.
- Frontend: `GET /` → HTTP 200 (SPA served).

## 11. Validación (evidence)

| Check | Result |
|---|---|
| `docker compose build` | ✅ `eureka-backend:latest` + `eureka-frontend:latest` built |
| `docker compose up -d` | ✅ both **Up**; backend **healthy** |
| `GET :8000/api/health` | ✅ `{"status":"OK"}` |
| `GET :5173/` (frontend) | ✅ HTTP 200 |
| `GET :5173/api/health` (nginx → backend) | ✅ `{"status":"OK"}` (frontend↔backend) |
| `POST :8000/api/copilot` (DeepSeek REAL) | ✅ reply, `model=deepseek-v4-flash` |
| Real 8-EM flow (intake→execute) | ✅ **COMPLETED** — Descriptor→Predictor→Prescriptor(decision gate)→Actioner→Installer→Publisher all COMPLETED; Core+Structurer ran inside `orchestrate()` |

## 12. Seguridad

- **`DEEPSEEK_API_KEY` lives only on the backend** (`server.py` `POST /api/copilot` + the DeepSeek
  cognitive adapter). The frontend `vite.config.ts` no longer proxies `/api/copilot` to DeepSeek
  nor loads the key; the browser bundle has no key reference (only explanatory comments).
- **CORS** is configurable via `EUREKA_CORS_ORIGINS`; the default is a localhost allow-list, not a
  public wildcard. In Docker the frontend uses same-origin (nginx proxy) so CORS is moot.
- `.env` is git-ignored; `.env.example` carries no real secrets.

## 13. Persistencia — limitación conocida

`works_db`, `evidence_store`, `evidence_work_index` (in `server.py`) are **in-memory dicts**.
**Works and evidence are lost when the process restarts.** No MongoDB/Neo4j/Redis/sqlite is used.
Persistence is a future phase; do not introduce a DB without a confirmed need.

## 14. Pruebas / regresión

- **Frontend:** `vitest run` → **62/62 PASS** (unchanged).
- **Backend:** the pytest suite **cannot be collected from the repo root** — the test modules do
  `from src.eureka...` and pytest reports `ModuleNotFoundError: No module named 'src.eureka'`
  (pre-existing test-harness issue; the runtime itself imports fine). A documented baseline of
  **37 pre-existing failures (LEGACY_DRIFT)** remains. **No new runtime regressions were
  observed**: server imports cleanly, `/api/health` OK, DeepSeek REAL OK, and the 8-EM pipeline
  reached `COMPLETED`. The applied backend changes are additive/config-only
  (`/api/copilot`, CORS env, cross-platform debug-path fix) and do **not** modify EM/MathEngine logic.

## 15. Ejecución local

```bash
cp .env.example .env          # fill DEEPSEEK_API_KEY
docker compose up -d --build
# frontend http://localhost:5173   · backend http://localhost:8000/api/health
```

## 16. Producción

- Frontend served by nginx (80/443), `/api` proxied to the backend container (internal).
- Set `VITE_EUREKA_API_URL` build arg to the public origin (e.g. `https://eureka.example.com`)
  so the bundle uses the same-origin `/api` route.
- Backend port **not** exposed publicly.
- Set `EUREKA_CORS_ORIGINS` to the real browser origin(s).

## 17. DigitalOcean (prepared, NOT deployed)

A single Ubuntu Droplet with Docker + Docker Compose is sufficient (no GPU). With `COGNITIVE_ENGINE=deepseek`,
model inference is remote — **no local GPU needed**. Estimated: **2 vCPU / 2–4 GB RAM** for the
backend (the heavy `matplotlib`/`pandas`/`scipy`/`reportlab` libs are memory-hungry at import) + a
small frontend/nginx. Ollama local inference would require more RAM/CPU (and optional GPU) and is
out of the initial scope. Open ports: **80/443** (frontend) and allow **outbound** HTTPS to
`api.deepseek.com`. Keep `DEEPSEEK_API_KEY` as a Droplet environment secret (never in the repo).

## 18. Troubleshooting

- **`FAIL_CLOSED: Semantic interpretation failed`** → check `DEEPSEEK_API_KEY` is set in `.env`
  (`COGNITIVE_ENGINE=deepseek`). Historical cause: a hardcoded Windows debug path
  (`C:/Temp/deepseek_raw_response.txt`) broke on Linux; fixed to a safe temp path (non-fatal).
- **Backend not reaching DeepSeek** → confirm outbound HTTPS + a valid key; `POST /api/copilot`
  returns `500 MISSING_DEEPSEEK_API_KEY` if the key is absent.
- **Frontend can't reach `/api`** → confirm the nginx `/api` proxy (container DNS `backend`).

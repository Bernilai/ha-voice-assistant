# Smart Home Voice MVP (local)

Text-first Russian smart home demo: **Home Assistant** is the source of truth for device state; a **FastAPI** backend owns interpretation (stub), execution, ambiguity handling, status queries, compound actions, the in-memory **event log** (append between successful resets; cleared on successful `POST /api/demo/reset`), and **demo** controls; the **React** UI is a controlled client over those APIs.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose v2
- Optional: Python 3.11+ and Node 20+ for host-run backend/UI

## Quick start (full stack in Docker)

1. Copy environment defaults:

   ```powershell
   copy .env.example .env
   ```

   On Linux/macOS: `cp .env.example .env`

2. Set `HA_TOKEN` in `.env` to a Home Assistant long-lived access token when you want the backend to read/write a real HA instance (see [docs/setup.md](docs/setup.md)). For a first boot you may leave it empty while HA onboarding completes; `GET /api/state/house` will return **503** until a token is configured.

3. Start services (first run pulls images; Home Assistant may take **1–3 minutes** before port 8123 answers):

   ```powershell
   docker compose up --build
   ```

4. Backend health:

   ```powershell
   curl http://127.0.0.1:8000/api/health
   ```

   Expected: `{"status":"ok"}`

5. Demo UI (Vite dev server, proxies `/api` to the backend): **http://127.0.0.1:5173**

6. Home Assistant: **http://127.0.0.1:8123** — complete onboarding on first boot.

### Ports (defaults)

| Service          | Host port | Variable               |
|------------------|-----------|-------------------------|
| Home Assistant   | 8123      | `HOMEASSISTANT_PORT`    |
| Backend API      | 8000      | `BACKEND_PORT`          |
| Vite UI          | 5173      | `UI_PORT`               |
| Ollama (optional)| 11434     | `OLLAMA_PORT`           |

### Backend ↔ Home Assistant

- `HA_URL` (default `http://homeassistant:8123` in Compose) and `HA_TOKEN` configure the live HA client.
- The backend container waits until TCP **8123** on the `homeassistant` service is open before starting Uvicorn.
- Automated tests use an in-process **mock** HA client (`MockHomeAssistantClient`); they do not require a running Home Assistant.

### Optional: Ollama NLU for unknown phrases

The interpret path is normally a **deterministic phrase table**. To try LLM-backed interpretation for phrases the stub does not recognize, set **`OLLAMA_NLU_ENABLED=true`** in `.env` and ensure the **Ollama** service is running (Compose includes an `ollama` service). Relevant variables: **`OLLAMA_URL`**, **`OLLAMA_MODEL`**, **`OLLAMA_TIMEOUT`**. Model output is validated against fixed intent and entity allowlists; invalid JSON or incomplete entities still return **`unsupported`**. See [docs/architecture.md](docs/architecture.md) and [docs/api-contracts.md](docs/api-contracts.md).

## Run backend tests (host)

From the repository root:

```powershell
pip install -r backend/requirements.txt
pytest backend/tests -q
```

## Run UI on the host (optional)

```powershell
cd ui
npm install
$env:VITE_PROXY_TARGET = "http://127.0.0.1:8000"
npm run dev
```

Vitest:

```powershell
cd ui
npm run test
```

## Project layout

| Path            | Role                                      |
|-----------------|-------------------------------------------|
| `ha/`           | Home Assistant configuration (mounted)  |
| `backend/`      | FastAPI service                           |
| `ui/`           | Vite + React + TypeScript demo UI       |
| `docs/`         | Architecture, API contracts, setup      |

## Documentation

- [docs/setup.md](docs/setup.md) — environment and HA token notes  
- [docs/architecture.md](docs/architecture.md) — layers and boundaries  
- [docs/api-contracts.md](docs/api-contracts.md) — HTTP contracts  
- [docs/intent-catalog.md](docs/intent-catalog.md) — supported intents (honest subset)  

## Scope and limitations (intentional)

- **No unconstrained NLP**: `POST /api/intents/interpret` is a deterministic phrase table by default; optional Ollama fallback (`OLLAMA_NLU_ENABLED`) still gates on strict backend validation, not free-form execution.
- **Demo `mode` (`static` / `live` / `simulator`)** is an in-memory **operator label** (and a one-off `demo_set_mode` event when you call set-mode); execute/clarify/replay/reset **ignore** it. It does **not** switch execution engines or replace HA state.
- **`POST /api/demo/reset`** is **not transactional**: baseline application runs as a best-effort sequence (or a single mock snapshot); on failure, the event log and clarification store are **not** cleared.
- **`POST /api/demo/replay`** runs a **fixed catalog** of steps through the same execute path as normal commands; it is **not** a user-authored automation DSL. Replay stops on the first non-success step; an **unknown** `scenario_id` returns immediately and does **not** update `last_replay_summary` / `last_replay_at` in `GET /api/demo/status`.
- **Voice (P9, optional)** is a **narrow** extension: Home Assistant Assist can use `ha/custom_sentences/ru` → `intent_script.yaml` locally, while the backend exposes **`GET /api/voice/status`** and **`POST /api/voice/transcript`** so a transcript can reuse the same interpret/execute stack as text (explicit subset; no custom STT/TTS engine). Text and `/api/intents/*` remain the canonical stable path; set `VOICE_BRIDGE_ENABLED=0` to disable the transcript endpoint. See [docs/setup.md](docs/setup.md) and [docs/architecture.md](docs/architecture.md).

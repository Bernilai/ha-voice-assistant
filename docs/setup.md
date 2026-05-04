# Setup

## Expected services

- **Home Assistant** — state and service execution.
- **Backend** — FastAPI on port 8000 (default).
- **UI** — Vite dev server on port 5173 (default), proxies `/api` to the backend.

## Recommended startup path

1. Copy `.env.example` to `.env` if you have not already.
2. **Long-lived token**: in Home Assistant, create a long-lived access token and set `HA_TOKEN` in `.env`. Without it, live HA reads fail and `GET /api/state/house` returns **503** with a structured `detail` body.
3. `docker compose up --build` from the repository root.
4. Wait for HA (8123) and backend (8000) health.
5. Open the UI at **http://127.0.0.1:5173** and use the command console (text).
6. Optionally open the operator panel for reset, replay, and `demo/status`.
7. **P9 voice (optional)** — In HA, finish onboarding, enable **Assist**, add a local STT/TTS pipeline if desired, and rely on `ha/custom_sentences/ru` + `intent_script.yaml` for HA-local execution. For the **same backend event semantics** as text, use the UI “Голос (опционально)” strip or **`POST /api/voice/transcript`** (narrow phrase subset; see **`GET /api/voice/status`**). Set **`VOICE_BRIDGE_ENABLED=0`** in `.env` to disable the transcript endpoint while keeping text APIs unchanged.

## Host-run backend (development)

```powershell
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --port 8000
```

Point `HA_URL` / `HA_TOKEN` at your HA instance, or rely on tests’ mock client.

## Host-run UI

```powershell
cd ui
npm install
$env:VITE_PROXY_TARGET = "http://127.0.0.1:8000"
npm run dev
```

## Tests

- Backend: from repo root, `pytest backend/tests -q`
- UI: `cd ui && npm run test`

## Notes

- First HA boot requires the browser onboarding wizard; the backend waits for port 8123 but not for onboarding completion.
- Text-first demos remain canonical; P9 voice is optional and narrower than text (see [README.md](../README.md) and [docs/architecture.md](architecture.md)).

## Phased implementation

High-level roadmap: [.cursor/plans/phased_mvp_implementation_b5c52a3c.plan.md](../.cursor/plans/phased_mvp_implementation_b5c52a3c.plan.md).

# Architecture

## Purpose

This project is a local-first Russian-language smart home voice assistant MVP. It targets a deterministic demo without physical hardware: Home Assistant holds simulated or real entities, while product-specific routing and copy live in the FastAPI backend and the demo UI.

## System layers

### Home Assistant

- Source of truth for entity state, scenes, and service effects (`turn_on`, `turn_off`, `scene.turn_on`, etc.).
- Configuration under `ha/` (packages, scenes, intent wiring) is integration glue, not the primary business-logic layer for this MVP.

### Backend (FastAPI)

- **`GET /api/state/house`** — Reads HA `/api/states`, maps an MVP allowlist into normalized JSON (`version: "p3-ha"`).
- **`POST /api/intents/interpret`** — Deterministic stub (phrase table) first; optional **Ollama NLU fallback** when `OLLAMA_NLU_ENABLED=true` runs after unknown phrases, validates JSON against the same intent/entity allowlists as execute (see `backend/app/services/ollama_interpret.py`).
- **`POST /api/intents/execute`** — Writes (lights, scenes) and read-only status intents (`get_room_status`, `get_device_status`, `get_sensor_status`) through dedicated services; compound two-step actions; light ambiguity can return `clarification_required` before any write.
- **`POST /api/intents/clarify`** — Continues P5 execute-time clarification sessions only (TTL-bound, in-memory).
- **`GET /api/events`** — In-memory event log, newest first; entries are append-only until a successful demo reset clears the log.
- **`GET|POST /api/demo/*`** — Reset (baseline + clears log/sessions), replay (fixed catalog), set-mode (label only), status (operator metadata).
- **`GET /api/voice/status`**, **`POST /api/voice/transcript`** — P9 optional: operator metadata and transcript bridge over the same interpret/execute semantics (narrow subset); not a speech engine.

### UI (React + Vite)

- Polls house state and events; command flow: **interpret → execute** on stub success; **execute → clarify** for P5 ambiguity.
- **P9 voice strip** (optional): loads **`GET /api/voice/status`**, submits transcripts to **`POST /api/voice/transcript`**, shows outcome and **does not** replace the text console.
- **Interpret clarification bridge**: only `clarification.reason === "missing_room"` with `{ label, room }[]` options is turned into buttons that call **execute** with client-inferred `turn_on_device` / `turn_off_device` from the normalized phrase (`interpretFollowUp.ts`). Other interpret clarification shapes show an explicit “unsupported in UI” path — they are **not** backend clarification sessions.

### Integration

- Backend HA client (`HA_URL`, `HA_TOKEN`) for live reads/writes; tests inject `MockHomeAssistantClient`.

## Source of truth

Home Assistant is the single source of truth for house/device state. The backend does not maintain a parallel authoritative house model. The UI displays backend responses and HA-backed state; client-side inferred fields (e.g. intent from “включи/выключи” for missing-room follow-up) are **UI convenience only**, not persisted as backend truth.

## Deterministic vs best-effort

| Area | Behavior |
|------|----------|
| Interpret stub | Deterministic string matches; optional Ollama NLU only when enabled (`OLLAMA_NLU_ENABLED`), strict JSON validation against known intents/entities. |
| Clarification matching | Deterministic token/alias/option rules. |
| Replay step order and payloads | Fixed in code (deterministic catalog). |
| HA `call_service` / reads | Best-effort; failures surface as `error` in execute responses or **503** on house read. |
| Demo reset baseline (live) | Ordered service calls; **not atomic**; partial application possible on mid-sequence failure. |
| Mock HA in tests | Deterministic `reset_to_baseline` snapshot. |

## Voice and text (P9, optional)

Text is mandatory and always supported through the UI and **`POST /api/intents/*`**. P9 adds **two narrow, explicit paths**; neither replaces text or introduces a second intent engine:

1. **HA Assist (local)** — `ha/custom_sentences/ru/*.yaml` map spoken Russian to **`intent_script.yaml`**, which calls HA services directly. This is **HA-orchestrated**: convenient for on-device Assist, but backend **event log** entries are not produced for that path unless separately wired.
2. **Backend transcript bridge** — **`POST /api/voice/transcript`** accepts a transcript string, runs the same **`interpret_stub` → execute/status** pipeline as the text console, with a **strict allowlist** (e.g. requires `target_entity_id` for light on/off; no automatic continuation of clarification sessions). **`GET /api/voice/status`** documents the subset and limitations. Disable with **`VOICE_BRIDGE_ENABLED=0`**.

Unsupported or clarification-heavy cases **fall back to text** honestly (`execution_claimed: false` on the voice response when no execute success/error is claimed).

## Demo principle

Prefer explainable, test-backed behavior over open-ended realism. Operator-facing demo metadata (`GET /api/demo/status`) is explicitly **non-authoritative** relative to `GET /api/state/house`.

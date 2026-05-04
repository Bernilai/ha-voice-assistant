# Acceptance Checklist

Use this for handoff review: verify **implemented** behavior, not aspirational features.

## Environment

- [ ] `docker compose up --build` starts HA, backend, UI without manual patching.
- [ ] `GET /api/health` returns `{"status":"ok"}`.
- [ ] With `HA_TOKEN` set, `GET /api/state/house` returns **200** and `version: "p3-ha"`; without token (live client), expect **503** with JSON `detail.code` / `detail.message`.

## Core flows (text)

- [ ] Three MVP rooms appear in normalized house JSON.
- [ ] Light on/off with explicit `target_entity_id` updates HA-backed (or mock) state and lists affected entities in the execute response.
- [ ] Scene activation for catalog scenes works or surfaces a clear error from HA.
- [ ] Status intents (`get_room_status`, `get_device_status`, `get_sensor_status`) return compact Russian copy and `queried_entities` on success.
- [ ] Ambiguous kitchen (or multi-light) execute returns `clarification_required`; `POST /api/intents/clarify` can complete the write.
- [ ] `compound_action` with two valid steps runs sequentially; invalid shape / unsupported step returns documented `error_code` values.

## Interpret and UI bridge

- [ ] `POST /api/intents/interpret` returns stable keys (`raw_text`, `normalized_text`, `canonical_intent`, `entities`, `status`, `clarification`).
- [ ] UI: interpret success auto-calls execute; interpret `missing_room` shows room buttons; other interpret clarification shapes show the explicit unsupported-in-UI message (no fake backend session).
- [ ] Canonical IDs in payloads remain English (e.g. `light.living_room_main`), while user command examples remain Russian.

## MVP Russian smoke phrases (current subset)

- [ ] Lights: `включи/выключи свет` for kitchen, living room, bedroom (exact supported phrases from intent catalog).
- [ ] Curtains: `открой/закрой шторы` for living room and bedroom.
- [ ] Kettle: `включи чайник` / `выключи чайник` works without room mention (unique device rule).
- [ ] Heater: `включи/выключи обогреватель в спальне`.
- [ ] Temperature: `какая температура` in bedroom, kitchen, living room returns status via read-only path.
- [ ] Ambiguity rule: unique target -> no room required; ambiguous target -> room required or clarification (`выключи свет` -> `missing_room`).

## Demo controls

- [ ] `GET /api/demo/status` includes `replay_catalog`, `reset_contract`, `mode`, `mode_semantics`, and last reset/replay metadata fields.
- [ ] `POST /api/demo/reset` clears event log and clarification sessions **only after** baseline apply succeeds; on baseline failure, `ok: false` and log not cleared.
- [ ] `POST /api/demo/replay` runs catalog steps in order; stops on first non-success with partial `step_results`; unknown `scenario_id` leaves prior `last_replay_summary` unchanged.
- [ ] `POST /api/demo/set-mode` updates `mode` and `mode_semantics` only; does not change HA connectivity or execution routing by itself.

## Observability

- [ ] `GET /api/events` returns newest-first items with `id`, `timestamp`, `type`, `message`, `metadata`.

## Tests and docs

- [ ] `pytest backend/tests -q` passes.
- [ ] `cd ui && npm run test` passes.
- [ ] Canonical docs under `docs/` match the above behavior.

## Optional P9 voice (Assist + transcript bridge)

- [ ] `GET /api/voice/status` returns stable keys and honest limitations (`supported_transcript_phrases_ru`, `intentionally_unsupported_via_transcript`).
- [ ] With bridge enabled, a supported transcript (e.g. kitchen light on phrase) returns `outcome: "executed"` and `execution_claimed: true` only when execute/status returns success or error (not `clarification_required`).
- [ ] Interpret clarification phrases (e.g. “выключи свет”) return `fallback_to_text` with `execution_claimed: false` from **`POST /api/voice/transcript`**; text console still handles interpret → execute as before.
- [ ] `VOICE_BRIDGE_ENABLED=0` (or `false`) disables the transcript endpoint (`bridge_disabled`) without breaking **`POST /api/intents/*`**.

## Intentionally deferred

- [ ] Documented as out of scope: general NLP, voice-first-only flows, transactional whole-house rollback, user-authored replay DSL, `demo_mode` switching execution engines, custom cloud STT/TTS stacks.

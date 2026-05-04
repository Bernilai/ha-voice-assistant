# API Contracts

## Required endpoints

### GET /api/health
Returns service health information.

### GET /api/state/house
Returns current normalized house state for the UI (P3: assembled from Home Assistant `/api/states` via an explicit allowlist mapper; not a full HA registry dump).

Configuration:

- `HA_URL` (default `http://localhost:8123`): Home Assistant base URL.
- `HA_TOKEN` (required for live reads): long-lived access token.

Errors:

- On missing token, timeout, unreachable HA, or other integration failures, responds with **503** and JSON `detail` shaped as `{"code": "<string>", "message": "<human-readable>"}` (no stack traces in the body).

Response `version` field is `p3-ha` for this integration stage.

### GET /api/events
Returns recent event log items.

Query:

- `limit` (optional, default `50`, min `1`, max `200`): maximum number of items returned.
- Response field `order` is always `newest_first` (most recently appended event first).

### POST /api/intents/interpret
P1 baseline: deterministic stub (phrase table, not NLP). Converts raw user text into a **pre-execution** shape the UI or console can display and optionally map to `POST /api/intents/execute`.

Request JSON:

- `text` (string, required, non-empty): raw command text.

Response JSON (stable keys for P1):

- `raw_text`, `normalized_text`
- `canonical_intent` (string or null): maps to execute body field `intent` when you call `POST /api/intents/execute`
- `entities` (object)
- `status`: `success` | `clarification_required` | `unsupported`
- `clarification` (object or null): present when `status` is `clarification_required` (stub content only in P1)

**Interpret vs execute clarification:** stub `clarification_required` payloads are **not** P5 sessions and **must not** be sent to `POST /api/intents/clarify`. The demo UI only bridges one shape (`reason: "missing_room"` with `{ label, room }` options) by calling **execute** with a client-inferred `turn_on_device` / `turn_off_device` from the normalized phrase. Any other interpret clarification is unsupported in the UI and requires explicit execute JSON (e.g. API or HA wiring).

### POST /api/intents/execute
Accepts a normalized or partially normalized command. **Writes** (P4a) are routed through an execution orchestrator (P5): light on/off may return `clarification_required` when targets are ambiguous; `compound_action` runs two validated P4a steps in order. Resolved single-target writes still use the scenario engine and HA write adapter. **Reads** (P4b) run through a dedicated status service that only calls the same HA-backed read path as `GET /api/state/house` (no `call_service`, no state mutation). Intents outside P4a, P4b, and the narrow P5 extensions return `status: "error"` with `error_code: "unsupported_intent"`.

**P4a execution subset** (HA service calls on success):

- `turn_on_device` / `turn_off_device` — deterministic supported device matrix:
  - lights: `light.kitchen_main`, `light.living_room_main`, `light.bedroom_main`
  - curtains: `cover.living_room_curtains`, `cover.bedroom_curtains`
  - kettle: `switch.kitchen_kettle`
  - heater: `switch.bedroom_heater`
  Resolution policy is conservative:
  - unique target (example: kettle) can be resolved without room in the user phrase
  - ambiguous target (example: lights) requires room or a clarification step
  HA service mapping depends on domain: `light` / `switch` -> `turn_on` / `turn_off`; `cover` -> `open_cover` / `close_cover`.
- `activate_scene` — `entities.scene` as one of: `movie`, `good_morning`, `evening`, `away` (maps to `scene.<key>`).

**P5 extensions** (same POST body shape; HTTP 200):

- **Ambiguous lights** — `turn_on_device` / `turn_off_device` with `device_type: "light"` and no `target_entity_id`: if `entities.room` is set, clarification lists that room’s lights; if `room` is omitted, clarification lists all MVP lights (deterministic order). Policy: **clarification-first** (no silent pick).
- **`compound_action`** — `entities.steps` must be a JSON array of **exactly** two objects, each `{ "intent": "<P4a intent>", "entities": { ... } }`. Both steps are validated before any HA write; execution is sequential. On failure of step 2 after step 1 succeeded: `error_code` is `compound_partial_failure` and `affected_entities` contains entities written in step 1 only. Preflight resolution failures use `error_code` prefixed with `compound_preflight_` (suffix mirrors resolver codes, e.g. `compound_preflight_unsupported_target`). Invalid `steps` shape → `compound_invalid_shape`. Unsupported step intent → `compound_unsupported_step`.

**P4b status subset** (read-only; body assembled from normalized house state mapped from HA `/api/states`):

- `get_room_status` — `entities.room`: `living_room` | `kitchen` | `bedroom` (summary of that room’s MVP devices and sensors).
- `get_device_status` — `entities.room` + `entities.device_type` (only `light`: primary room light, same entity as P4a on/off).
- `get_sensor_status` — `entities.room` + `entities.sensor_kind` (narrow matrix): `living_room` + (`temperature` | `motion`); `kitchen` + (`temperature` | `window`); `bedroom` + (`temperature` | `humidity`). Other pairs → `unsupported_target`.

Response JSON (stable keys):

- `status`: `success` | `error` | `clarification_required` (P4b read-only paths use `success` | `error`; P5 may return `clarification_required` from execute for ambiguous lights).
- `spoken_response`, `ui_message` (short human-readable strings; status lines are compact Russian summaries).
- `affected_entities` (list): HA `entity_id` strings **written** or targeted by P4a execution (empty for P4b success).
- `queried_entities` (list): HA `entity_id` strings **read** for a successful P4b status response (all public entities in the room for `get_room_status`, or the single resolved entity for device/sensor status). Empty for P4a success and for typical errors.
- `trace` (object): P4a successes include `execution_engine` (`p4a-ha`), `intent`, `entities`, and `resolved_entity_id`, `ha_action` (`turn_on` | `turn_off` | `scene.turn_on`). P4b successes include `status_engine` (`p4b-status`), `intent`, `entities`, and `room_id` / `resolved_entity_id` / `sensor_kind` as applicable. P5 **clarification_required** from execute adds `execution_engine` (`p5-execute`), `phase` (`ambiguity`), `clarification_session_id`, and `ambiguous_entity_ids`. Successful `compound_action` uses `execution_engine` (`p5-compound`) and `steps` (array of per-step traces). Failures may include `phase` (`intent_gate` | `resolve` | `ha_read` | `assemble` | `validate` | `preflight` | `session_lookup` | `reply_match` | `expired`) and `resolution_error` or `ha_error` as applicable.
- `error_code`, `error_message` (strings or `null`): set on `error` (e.g. `unsupported_intent`, `unsupported_target`, `ambiguous_light_target`, `internal`, clarification codes `clarification_expired`, `clarification_session_invalid`, `clarification_reply_invalid`, compound codes above, or HA integration codes such as `ha_unreachable` on failed reads inside P4b).
- `clarification` (object or `null`): set when `status` is `clarification_required` from execute. Contains at least `session_id`, `pending_intent`, `options` (array of `{ id, label, room_id }` for lights), and `expires_in_seconds` (hint from server TTL). Clarification sessions are **in-memory** with a fixed TTL (default **120 seconds**); they are cleared on `POST /api/demo/reset`.

HTTP status remains **200** for validation/integration failures expressed in the body; `GET /api/state/house` continues to use **503** for read failures per P3.

### POST /api/intents/clarify
Accepts a clarification response to continue an ambiguous **execute** interaction (P5). Request JSON: `session_id` (string, required), `reply` (string, required) — deterministic match against the offered option `id`, narrow room tokens (`kitchen` / `кухня`, etc.), or the small alias set for each light (e.g. `подсветка`, `торшер`). Response body matches **`IntentExecuteResponse`** (same schema as `POST /api/intents/execute`): `success` after a resolved write, `clarification_required` again if the reply narrows but does not uniquely select, or `error` with `clarification_*` / other codes. Pending sessions expire by TTL; expired or unknown sessions return `clarification_expired` / `clarification_session_invalid`.

Interpret smoke phrases currently include Russian commands for lights, curtains, kettle, heater, and room temperature queries. Canonical internal IDs in responses remain English.

### GET /api/demo/status
P7 operator surface: returns **non-authoritative** demo metadata (does not replace `GET /api/state/house`).

Response JSON (stable keys):

- `mode`: current in-memory demo label from `POST /api/demo/set-mode` (`static` | `live` | `simulator`).
- `mode_semantics`: short Russian explanation of what `mode` means in this MVP (metadata for operators; not HA truth).
- `last_reset_at`, `last_reset_ok`, `last_reset_baseline_strategy`: last completed `POST /api/demo/reset` outcome (or `null` if none yet this process).
- `last_replay_at`, `last_replay_summary`: updated after each **known-catalog** replay finishes its handler (all steps `success`, or **stopped early** on the first non-`success` step). `null` until the first such run in this process. A request with an **unknown** `scenario_id` returns immediately (`steps_total: 0`, `completed_at: null`) and does **not** change these fields.
- `replay_catalog`: fixed list of `{ id, title, steps, deterministic, notes }` entries — the only scenario ids accepted by replay.
- `reset_contract`: one short paragraph stating reset side effects and non-transactional honesty.

### POST /api/demo/reset
P7: clears in-memory **clarification sessions** and **event log**, then applies the MVP **canonical baseline** to HA (mock shortcut or best-effort service sequence). **Not transactional:** if baseline application fails, the event log is **not** cleared and `ok` is `false` in the JSON body (HTTP still **200**).

Response JSON:

- `ok` (bool): `false` if baseline apply raised before clears; `true` on success path after clears and baseline.
- `message` (string): human-readable summary.
- `event_log_cleared`, `clarification_sessions_cleared` (bool): reflect what actually happened this call.
- `baseline_strategy`: `mock_reset_to_baseline` (test mock’s `reset_to_baseline` shortcut) or `ha_service_sequence` (live-like ordered `call_service` / write-adapter loop per `mvp_house_baseline`).
- `baseline_semantics` (string): explicit honesty about determinism vs best-effort / non-atomic behavior.
- `reset_at` (string): ISO-8601 UTC timestamp when the handler finished.

### POST /api/demo/replay
P7: runs a **fixed catalog** scenario by `scenario_id` (default `lights_kitchen_cycle` when the request body is empty). Each step is a normal `IntentExecuteRequest` executed through the same orchestrator as `POST /api/intents/execute` / P4b status service; `source` is set to `demo_replay` and `meta` includes `scenario_id` / step index. **Deterministic:** step order and payloads are fixed in code; **best-effort:** each HA write/read can still fail like any execute call — replay stops on the first non-`success` step and returns `ok: false` with partial `step_results` (including the failing step). This is **not** a general automation DSL: only catalog ids are valid; there is no user-authored script format beyond choosing `scenario_id`.

**Unknown `scenario_id`:** HTTP **200**, `ok: false`, `steps_run: 0`, `steps_total: 0`, `stopped_early: false`, empty `step_results`, `detail` explains the catalog; `completed_at` is `null`; `last_replay_*` demo status fields are unchanged.

Request JSON (optional body):

- `scenario_id` (string, optional): one of the catalog ids from `GET /api/demo/status` (`lights_kitchen_cycle`, `room_status_kitchen`, `scene_movie`, `compound_kitchen_bedroom_on`).

Response JSON:

- `ok`, `scenario_id`, `steps_total`, `steps_run`, `stopped_early`, `step_results` (per-step `intent` / `status` / `error_code`), `detail`, `completed_at`.

### POST /api/demo/set-mode
P7: stores an in-memory **demo mode label** only (`static` | `live` | `simulator`). The label is exposed via `GET /api/demo/status` and a single `demo_set_mode` row is appended to the event log; **execute**, **clarify**, **replay**, and **reset** do not read `mode` and behave the same regardless of label. Response includes `semantics` (Russian) describing operator expectations. This is **not** a second house state — `GET /api/state/house` remains the house truth.

### GET /api/voice/status (P9, optional)

Operator-facing metadata for the **optional** voice layer. Does **not** guarantee microphone, cloud STT, or a running Assist pipeline — only describes how this repo wires voice-related surfaces.

Response JSON (stable keys):

- `integration_kind`: always `ha_assist_plus_transcript_bridge` for this MVP stage.
- `bridge_enabled`, `transcript_endpoint_available`: reflect in-process config **`VOICE_BRIDGE_ENABLED`** (default on when unset). When disabled, `transcript_endpoint_available` is `false` and **`POST /api/voice/transcript`** returns `outcome: "bridge_disabled"` without executing.
- `ha_assist_local_path`, `transcript_bridge_path`: short Russian/technical explanations of the two paths (HA `custom_sentences` → `intent_script` vs backend transcript reuse).
- `supported_transcript_phrases_ru`: human-readable list aligned with the **narrow** transcript subset.
- `intentionally_unsupported_via_transcript`: bullet list of honest exclusions (clarification continuation, compounds, etc.).
- `clarification_policy_ru`: one paragraph stating that clarification sessions are **not** continued automatically from the transcript bridge.

### POST /api/voice/transcript (P9, optional)

Request JSON:

- `transcript` (string, required, non-empty after trim): treated like **`POST /api/intents/interpret`** `text`, then — only if allowed by the voice subset policy — the same **`POST /api/intents/execute`** (or internal status service) path as text, with `source: "voice"`.

Response JSON (stable keys):

- `outcome`: `executed` | `fallback_to_text` | `bridge_disabled`.
- `execution_claimed` (bool): **`true` only** when execute/status ran and returned **`success` or `error`**. It is **`false`** for bridge disabled, interpret failures, policy rejections, **`clarification_required`**, or client-only paths — i.e. **do not** treat a captured transcript alone as executed work.
- `transcript`, `message_ru`, `voice_path` (`transcript_bridge`).
- `interpret` (`IntentInterpretResponse` or `null`).
- `policy_reason` (string or `null`): machine-stable reason for fallback/disabled outcomes.
- `execute` (`IntentExecuteResponse` or `null`): present on **`executed`**, and on **`fallback_to_text`** when execute returned **`clarification_required`** so operators can continue via **`POST /api/intents/clarify`** from text.

## Canonical intent payload

```json
{
  "intent": "turn_off_device",
  "source": "text",
  "utterance": "выключи свет в гостиной",
  "entities": {
    "room": "living_room",
    "device_type": "light",
    "target_entity_id": "light.living_room_main"
  },
  "confidence": 0.95,
  "requires_clarification": false,
  "meta": {
    "language": "ru",
    "session_id": "demo-session-001"
  }
}
```
# Intent Catalog

This document lists intents **actually handled** by `POST /api/intents/execute` and related flows in the current codebase. Names not listed here are rejected with `unsupported_intent` (HTTP **200**, `status: "error"` in the body) unless noted otherwise.

## Write intents (P4a / scenario engine)

### `turn_on_device` / `turn_off_device`

- **Entities**: canonical internal fields stay English (`room`, `device_type`, `target_entity_id`), while end-user phrases are Russian.
- **Current deterministic coverage**:
  - `light`: kitchen / living room / bedroom main lights
  - `curtains`: living room / bedroom curtains (`cover.*`)
  - `kettle`: kitchen kettle (`switch.kitchen_kettle`)
  - `heater`: bedroom heater (`switch.bedroom_heater`)
- **Resolution rule (current MVP)**:
  - unique target (example: kettle) -> room can be omitted in user phrase
  - multiple possible targets (example: lights) -> room is required in phrase or clarification is required
- **HA mapping**:
  - `light.*` and `switch.*` -> `turn_on` / `turn_off`
  - `cover.*` -> `open_cover` / `close_cover`

### `activate_scene`

- **Entities**: `scene` ∈ `movie` | `good_morning` | `evening` | `away` (maps to `scene.<key>`).

### `compound_action`

- **Entities**: `steps` — JSON array of **exactly** two inner `{ "intent", "entities" }` objects, each a supported P4a intent payload.
- Validated **before** any write; sequential execution. See API contracts for partial failure and preflight error codes.

## Read-only status intents (P4b, same execute endpoint)

Routed internally to `StatusService` (no `call_service` writes):

### `get_room_status`

- **Entities**: `room` — MVP room id.

### `get_device_status`

- **Entities**: `room`, `device_type` (`light` only; primary/main light semantics per mapper).

### `get_sensor_status`

- **Entities**: `room`, `sensor_kind` — narrow supported matrix (see `docs/api-contracts.md`).

## Clarification (execute-time, P5)

Ambiguous light selection uses **`POST /api/intents/clarify`** with `session_id` and `reply`. This is **separate** from `POST /api/intents/interpret` stub clarifications (see below).

There is **no** `clarification_reply` intent on the execute endpoint; continuation is always the dedicated `/clarify` route.

## Interpret stub (`POST /api/intents/interpret`)

Not an intent registry entry: returns `canonical_intent` + `entities` for a **small fixed phrase set**, or `unsupported`, or `clarification_required` with stub-only clarification payloads. The UI only automates one clarification shape (`missing_room` for “выключи свет”); everything else is manual / unsupported in UI.

Current deterministic Russian phrase subset:

- **Lights**
  - `включи свет на кухне`
  - `выключи свет на кухне`
  - `включи свет в гостиной`
  - `выключи свет в гостиной`
  - `включи свет в спальне`
  - `выключи свет в спальне`
- **Curtains**
  - `открой шторы в гостиной`
  - `закрой шторы в гостиной`
  - `открой шторы в спальне`
  - `закрой шторы в спальне`
- **Kettle**
  - `включи чайник`
  - `выключи чайник`
  - `включи чайник на кухне`
  - `выключи чайник на кухне`
- **Heater**
  - `включи обогреватель в спальне`
  - `выключи обогреватель в спальне`
- **Temperature**
  - `какая температура в спальне`
  - `какая температура на кухне`
  - `какая температура в гостиной`

Also supported:

- `включи режим кино`, `режим кино` -> `activate_scene` (`scene: movie`)
- `статус кухни`, `что на кухне` -> `get_room_status` / `room: kitchen`
- `выключи свет` -> `clarification_required` (`missing_room`)

### Optional: Ollama NLU fallback (off by default)

If **`OLLAMA_NLU_ENABLED=true`** (see `.env.example`), unknown phrases are sent to a local **Ollama** instance after the stub misses. The LLM is constrained by a system prompt to emit JSON; the backend **validates** intents and entities against the same allowlists used elsewhere (rooms, `target_entity_id`, `device_type`, scene keys, and **`get_sensor_status` (room, sensor_kind) pairs** matching P4b / `status_resolver.py`). Invalid or incomplete model output yields **`status: "unsupported"`**, same as an unknown stub phrase. This does not replace deterministic demo behavior when the flag is off.

Not in scope at this stage (when NLU is disabled or validation fails):

- broad Russian paraphrase/synonym handling outside the fixed phrase table
- unconstrained open-ended natural-language interpretation without backend validation

## P9 voice subset (transcript bridge)

**`POST /api/voice/transcript`** reuses the same deterministic interpret+execute path but remains intentionally narrow and conservative. Treat text via **`POST /api/intents/*`** as the canonical MVP path; voice is optional.

## Not implemented in this MVP

The following appear in broader product sketches but **are not** execute-supported in this repository:

- `set_brightness`, `set_temperature`
- Open-ended natural language beyond the interpret phrase table
- Arbitrary user-defined replay or automation DSL

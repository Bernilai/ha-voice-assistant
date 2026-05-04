# Demo Script

## Preconditions

- Stack running (`docker compose up` or host-run backend + UI).
- For live HA: valid `HA_TOKEN` and entities matching the MVP mapper (or use tests/mock for a dry run).
- Optional: `POST /api/demo/reset` to restore the documented baseline and clear the in-memory event log and clarification sessions (best-effort / non-transactional — see `GET /api/demo/status` `reset_contract`).

## Recommended order

1. Dashboard: house layout from `GET /api/state/house`, last utterance and normalized flow in the command panel.
2. Deterministic phrase: e.g. **«включи свет на кухне»** (interpret stub + execute).
3. State change visible on the kitchen light row; new rows in the event log (`intent_interpret`, `intent_execute_*`, etc.).
4. Scene: phrase **«включи режим кино»** or direct execute with `activate_scene` / `movie`.
5. Status: `get_room_status` for a room (operator/debug or API client); replay scenario **`room_status_kitchen`** runs one such step.
6. Ambiguity: execute `turn_off_device` with `device_type: "light"` and **no** `target_entity_id` in kitchen — use execute clarification buttons or `POST /api/intents/clarify`.
7. Operator panel: `GET /api/demo/status` fields, **reset**, **replay** catalog buttons (`lights_kitchen_cycle`, `scene_movie`, `compound_kitchen_bedroom_on`, etc.), **set-mode** (label only — execution unchanged).
8. Voice (P9): optional future layer via Home Assistant; if unstable, stay on text — same backend contracts.

## Suggested Russian phrases (interpret stub)

These match the backend stub table (`interpret_stub.py`), not general language:

- Включи свет на кухне / Выключи свет на кухне
- Включи свет в гостиной / Выключи свет в гостиной
- Включи свет в спальне / Выключи свет в спальне
- Открой шторы в гостиной / Закрой шторы в гостиной
- Открой шторы в спальне / Закрой шторы в спальне
- Включи чайник / Выключи чайник (room optional: unique target)
- Включи обогреватель в спальне / Выключи обогреватель в спальне
- Какая температура в спальне / на кухне / в гостиной
- Включи режим кино / режим кино
- Выключи свет (stub `missing_room`; clarification required)

Scope note: this is a deterministic MVP command table. Broader Russian paraphrases/synonyms are intentionally not guaranteed yet and may return **`unsupported`** unless sent as explicit execute JSON.

## Fallback plan

If voice or Assist is unavailable, continue with the command console and operator replay/reset. All critical flows are text- and API-accessible.

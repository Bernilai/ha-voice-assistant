from __future__ import annotations

from typing import Final

P4A_EXECUTE_INTENTS: Final[frozenset[str]] = frozenset(
    {
        "turn_on_device",
        "turn_off_device",
        "activate_scene",
    }
)

# P5: two-step orchestration only; validated in CompoundService.
COMPOUND_ACTION_INTENT: Final[str] = "compound_action"

# Read-only status subset (P4b): same POST /api/intents/execute, separate StatusService.
P4B_STATUS_INTENTS: Final[frozenset[str]] = frozenset(
    {
        "get_room_status",
        "get_device_status",
        "get_sensor_status",
    }
)

# Keys accepted in entities["scene"] for activate_scene (maps to scene.<key>)
P4A_SCENE_KEYS: Final[frozenset[str]] = frozenset({"movie", "good_morning", "evening", "away"})

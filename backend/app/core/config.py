"""Environment-backed settings (no second SoT for house state)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ha_url: str
    ha_token: str
    ha_timeout_seconds: float

    @classmethod
    def from_env(cls) -> Settings:
        url = os.environ.get("HA_URL", "http://localhost:8123").rstrip("/")
        token = os.environ.get("HA_TOKEN", "").strip()
        timeout = float(os.environ.get("HA_TIMEOUT", "15"))
        return cls(ha_url=url, ha_token=token, ha_timeout_seconds=timeout)

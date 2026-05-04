"""Home Assistant integration boundary (P3)."""

from app.integrations.ha_client import HomeAssistantClient
from app.integrations.ha_write_adapter import HAWriteAdapter

__all__ = ["HAWriteAdapter", "HomeAssistantClient"]

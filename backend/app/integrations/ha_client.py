"""Thin Home Assistant REST client (read states, call services)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class HomeAssistantIntegrationError(Exception):
    """Base for HA boundary failures (no stack traces in API responses)."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class HomeAssistantConfigurationError(HomeAssistantIntegrationError):
    """Missing or invalid local configuration (e.g. token)."""


class HomeAssistantUnavailableError(HomeAssistantIntegrationError):
    """HA unreachable, timed out, or returned an unexpected error."""


class HomeAssistantClient:
    """GET /api/states and POST /api/services/<domain>/<service>."""

    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        self._owns_client = http_client is None
        self._http = http_client or httpx.Client(
            base_url=settings.ha_url,
            headers={
                "Authorization": f"Bearer {settings.ha_token}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(settings.ha_timeout_seconds),
        )

    @classmethod
    def from_env(cls) -> HomeAssistantClient:
        return cls(Settings.from_env())

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    def get_states(self) -> list[dict[str, Any]]:
        if not self._settings.ha_token:
            raise HomeAssistantConfigurationError(
                "ha_token_missing",
                "HA_TOKEN is not set; cannot read Home Assistant state.",
            )
        try:
            r = self._http.get("/api/states")
        except httpx.TimeoutException as e:
            logger.warning("HA get_states timeout: %s", e)
            raise HomeAssistantUnavailableError(
                "ha_timeout",
                "Home Assistant did not respond in time.",
            ) from None
        except httpx.RequestError as e:
            logger.warning("HA get_states request error: %s", e)
            raise HomeAssistantUnavailableError(
                "ha_unreachable",
                "Could not reach Home Assistant.",
            ) from None

        if r.status_code == 401 or r.status_code == 403:
            raise HomeAssistantUnavailableError(
                "ha_auth_failed",
                "Home Assistant rejected the access token.",
            )
        if r.status_code != 200:
            logger.warning("HA get_states HTTP %s", r.status_code)
            raise HomeAssistantUnavailableError(
                "ha_bad_response",
                f"Home Assistant returned HTTP {r.status_code} for /api/states.",
            )

        data = r.json()
        if not isinstance(data, list):
            raise HomeAssistantUnavailableError(
                "ha_bad_payload",
                "Home Assistant /api/states returned a non-list body.",
            )
        return data

    def call_service(
        self,
        domain: str,
        service: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if not self._settings.ha_token:
            raise HomeAssistantConfigurationError(
                "ha_token_missing",
                "HA_TOKEN is not set; cannot call Home Assistant services.",
            )
        path = f"/api/services/{domain}/{service}"
        body = payload or {}
        try:
            r = self._http.post(path, json=body)
        except httpx.TimeoutException as e:
            logger.warning("HA call_service timeout %s.%s: %s", domain, service, e)
            raise HomeAssistantUnavailableError(
                "ha_timeout",
                "Home Assistant did not respond in time.",
            ) from None
        except httpx.RequestError as e:
            logger.warning("HA call_service request error %s.%s: %s", domain, service, e)
            raise HomeAssistantUnavailableError(
                "ha_unreachable",
                "Could not reach Home Assistant.",
            ) from None

        if r.status_code in (401, 403):
            raise HomeAssistantUnavailableError(
                "ha_auth_failed",
                "Home Assistant rejected the access token.",
            )
        if r.status_code < 200 or r.status_code >= 300:
            logger.warning("HA call_service HTTP %s for %s", r.status_code, path)
            raise HomeAssistantUnavailableError(
                "ha_bad_response",
                f"Home Assistant returned HTTP {r.status_code} for service {domain}.{service}.",
            )

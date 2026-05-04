"""HomeAssistantClient with mocked HTTP (no live HA)."""

from __future__ import annotations

import httpx
import pytest

from app.core.config import Settings
from app.integrations.ha_client import (
    HomeAssistantClient,
    HomeAssistantConfigurationError,
    HomeAssistantUnavailableError,
)


def test_get_states_success() -> None:
    payload = [{"entity_id": "light.kitchen_main", "state": "on", "attributes": {}}]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url).endswith("/api/states")
        assert request.headers.get("Authorization") == "Bearer test-token"
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    http = httpx.Client(
        base_url="http://ha.test",
        headers={"Authorization": "Bearer test-token"},
        transport=transport,
    )
    settings = Settings(ha_url="http://ha.test", ha_token="test-token", ha_timeout_seconds=5.0)
    client = HomeAssistantClient(settings, http_client=http)
    try:
        out = client.get_states()
        assert out == payload
    finally:
        client.close()


def test_get_states_missing_token() -> None:
    settings = Settings(ha_url="http://ha.test", ha_token="", ha_timeout_seconds=5.0)
    transport = httpx.MockTransport(lambda r: httpx.Response(500))
    http = httpx.Client(base_url="http://ha.test", transport=transport)
    client = HomeAssistantClient(settings, http_client=http)
    try:
        with pytest.raises(HomeAssistantConfigurationError) as ei:
            client.get_states()
        assert ei.value.code == "ha_token_missing"
    finally:
        client.close()


def test_get_states_non_list_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"not": "a list"})

    transport = httpx.MockTransport(handler)
    http = httpx.Client(
        base_url="http://ha.test",
        headers={"Authorization": "Bearer t"},
        transport=transport,
    )
    settings = Settings(ha_url="http://ha.test", ha_token="t", ha_timeout_seconds=5.0)
    client = HomeAssistantClient(settings, http_client=http)
    try:
        with pytest.raises(HomeAssistantUnavailableError) as ei:
            client.get_states()
        assert ei.value.code == "ha_bad_payload"
    finally:
        client.close()


def test_call_service_posts_expected_path() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(str(request.url))
        assert request.method == "POST"
        return httpx.Response(200, json=[])

    transport = httpx.MockTransport(handler)
    http = httpx.Client(
        base_url="http://ha.test",
        headers={"Authorization": "Bearer t"},
        transport=transport,
    )
    settings = Settings(ha_url="http://ha.test", ha_token="t", ha_timeout_seconds=5.0)
    client = HomeAssistantClient(settings, http_client=http)
    try:
        client.call_service("light", "turn_on", {"entity_id": "light.kitchen_main"})
        assert any(p.endswith("/api/services/light/turn_on") for p in paths)
    finally:
        client.close()

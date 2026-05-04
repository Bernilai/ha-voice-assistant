import pytest
from fastapi.testclient import TestClient

from app.main import app

from tests.mock_ha_client import MockHomeAssistantClient


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        mock = MockHomeAssistantClient()
        st = c.app.state.app_state
        st.ha_client = mock
        st.rebind_ha_stack()
        assert c.post("/api/demo/reset").status_code == 200
        yield c

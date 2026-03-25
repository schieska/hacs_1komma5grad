"""Fixtures for 1KOMMA5GRAD integration tests."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import pytest_socket
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.helpers import entity_registry as er

from custom_components.einskomma5grad.const import DOMAIN

MOCK_DIR = (
    Path(__file__).parent.parent
    / "custom_components"
    / "einskomma5grad"
    / "test"
    / "mocks"
)

SYSTEM_ID = "a1b2c3d4-0000-0000-0000-000000000001"
EV_ID = "00000000-0000-0000-0000-000000000000"

# HA slugifies entity names: dashes become underscores
SYSTEM_SLUG = SYSTEM_ID.replace("-", "_")
EV_SLUG = EV_ID.replace("-", "_")


def entity_id_for(hass: HomeAssistant, entity_domain: str, unique_id: str) -> str | None:
    """Resolve entity_id from integration unique_id (stable when device naming changes)."""
    return er.async_get(hass).async_get_entity_id(entity_domain, DOMAIN, unique_id)


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request):
    """Re-enable sockets before the asyncio ``event_loop`` fixture runs on Windows.

    pytest-homeassistant-custom-component calls disable_socket(allow_unix_socket=True).
    ProactorEventLoop still uses AF_INET socketpair() for its self-pipe. Fixture setup
    runs after ``pytest_runtest_setup``, so enabling here is late enough to stick.
    """
    if fixturedef.argname == "event_loop":
        pytest_socket.enable_socket()
    yield


def load_mock(filename: str) -> dict | list:
    """Load a mock JSON file."""
    with open(MOCK_DIR / filename) as f:
        return json.load(f)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain="einskomma5grad",
        title="Test System",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        options={CONF_SCAN_INTERVAL: 60},
        unique_id="test_unique_id",
    )


def _make_response(data, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = data
    resp.text = json.dumps(data)
    return resp


@pytest.fixture
def mock_api():
    """Mock all API calls made by the integration."""
    mock_data = {
        "systems": load_mock("GET_systems.json"),
        "live_overview": load_mock("GET_systems_id_live-overview.json"),
        "prices": load_mock("GET_systems_id_charts_market-prices.json"),
        "ems_settings": load_mock("GET_systems_id_ems_actions_get-settings.json"),
        "ev_chargers": load_mock("GET_systems_id_devices_evs.json"),
        "ev_modes": load_mock(
            "GET_sites_id_assets_evs_displayed-ev-charging-modes.json"
        ),
    }

    def get_router(url, **kwargs):
        if "/api/v2/systems" in url:
            # Distinguish list vs single system: /api/v2/systems vs /api/v2/systems/{id}
            path = url.split("/api/v2/systems")[1]
            if path and path != "/":
                # Single system request — return the first system object directly
                return _make_response(mock_data["systems"]["data"][0])
            return _make_response(mock_data["systems"])
        if "live-overview" in url:
            return _make_response(mock_data["live_overview"])
        if "market-prices" in url:
            return _make_response(mock_data["prices"])
        if "get-settings" in url:
            return _make_response(mock_data["ems_settings"])
        if "displayed-ev-charging-modes" in url:
            return _make_response(mock_data["ev_modes"])
        if "/devices/evs" in url:
            return _make_response(mock_data["ev_chargers"])
        raise ValueError(f"Unexpected GET URL: {url}")

    def post_router(url, **kwargs):
        if "set-manual-override" in url:
            return _make_response({}, status=201)
        raise ValueError(f"Unexpected POST URL: {url}")

    def patch_router(url, **kwargs):
        if "/devices/evs/" in url:
            return _make_response({})
        raise ValueError(f"Unexpected PATCH URL: {url}")

    # Patch Client to avoid OAuth/JWKS network calls
    # Patch requests at the module level in each API file
    with (
        patch(
            "custom_components.einskomma5grad.coordinator.Client"
        ) as mock_client_cls,
        patch(
            "custom_components.einskomma5grad.api.systems.requests.get",
            side_effect=get_router,
        ),
        patch(
            "custom_components.einskomma5grad.api.system.requests.get",
            side_effect=get_router,
        ),
        patch(
            "custom_components.einskomma5grad.api.system.requests.post",
            side_effect=post_router,
        ),
        patch(
            "custom_components.einskomma5grad.api.ev_charger.requests.patch",
            side_effect=patch_router,
        ),
    ):
        client = MagicMock()
        client.get_token.return_value = "mock_token"
        client.HEARTBEAT_API = "https://heartbeat.1komma5grad.com"
        mock_client_cls.return_value = client

        yield {"client": client, "data": mock_data}


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_api,
    enable_custom_integrations,
) -> MockConfigEntry:
    """Set up the integration with mocked API."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Trigger a coordinator refresh so entities receive their first update
    coordinator = hass.data[DOMAIN][mock_config_entry.entry_id].coordinator
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    return mock_config_entry

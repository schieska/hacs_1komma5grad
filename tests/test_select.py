"""Test 1KOMMA5GRAD EV charging mode select entity."""

from homeassistant.core import HomeAssistant

from custom_components.einskomma5grad.const import DOMAIN
from tests.conftest import EV_ID, SYSTEM_ID, entity_id_for


def _ev_mode_select_id(hass: HomeAssistant) -> str:
    eid = entity_id_for(
        hass, "select", f"{DOMAIN}_ev_charging_mode_{SYSTEM_ID}_{EV_ID}"
    )
    assert eid is not None
    return eid


async def test_ev_charging_mode_select_exists(
    hass: HomeAssistant, setup_integration
):
    """Test that the EV charging mode select entity is created."""
    state = hass.states.get(_ev_mode_select_id(hass))
    assert state is not None


async def test_ev_charging_mode_select_value(
    hass: HomeAssistant, setup_integration
):
    """Test that the EV charging mode shows the current mode from API."""
    state = hass.states.get(_ev_mode_select_id(hass))
    assert state is not None
    # Mock EV charger has chargingMode: "QUICK_CHARGE"
    assert state.state == "QUICK_CHARGE"


async def test_ev_charging_mode_options_from_api(
    hass: HomeAssistant, setup_integration
):
    """Test that options come from the displayed-ev-charging-modes API."""
    state = hass.states.get(_ev_mode_select_id(hass))
    assert state is not None
    options = state.attributes.get("options", [])
    assert "SMART_CHARGE" in options
    assert "SOLAR_CHARGE" in options
    assert "QUICK_CHARGE" in options
    assert len(options) == 3


async def test_ev_charging_mode_select_option(
    hass: HomeAssistant, setup_integration
):
    """Test changing the EV charging mode via select_option service call."""
    entity_id = _ev_mode_select_id(hass)

    # Verify initial state
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "QUICK_CHARGE"

    # Change charging mode to SMART_CHARGE
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id, "option": "SMART_CHARGE"},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify the state changed
    state = hass.states.get(entity_id)
    assert state.state == "SMART_CHARGE"

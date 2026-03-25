"""Test 1KOMMA5GRAD EMS switch entity."""

from homeassistant.core import HomeAssistant

from custom_components.einskomma5grad.const import DOMAIN
from tests.conftest import SYSTEM_ID, entity_id_for


def _ems_switch_id(hass: HomeAssistant) -> str:
    eid = entity_id_for(hass, "switch", f"{DOMAIN}_ems_auto_mode_{SYSTEM_ID}")
    assert eid is not None
    return eid


async def test_ems_switch_exists(hass: HomeAssistant, setup_integration):
    """Test that the EMS auto mode switch is created."""
    state = hass.states.get(_ems_switch_id(hass))
    assert state is not None


async def test_ems_switch_state(hass: HomeAssistant, setup_integration):
    """Test EMS switch reflects overrideAutoSettings from mock data."""
    state = hass.states.get(_ems_switch_id(hass))
    assert state is not None
    # Mock has overrideAutoSettings: false, so auto mode is ON
    assert state.state == "on"

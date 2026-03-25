"""Device registry helpers."""

from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .coordinator import Coordinator


def system_id_slug(system_id: str) -> str:
    """Stable slug fragment (matches legacy entity_id suffixes)."""
    return system_id.replace("-", "_")


def system_device_info(coordinator: Coordinator, system_id: str) -> DeviceInfo:
    """Group all entities for one Heartbeat system under a single device."""
    system = coordinator.get_system_by_id(system_id)
    name = system.display_name() if system else system_id
    return DeviceInfo(
        identifiers={(DOMAIN, system_id)},
        name=name,
        manufacturer="1KOMMA5°",
        model="Heartbeat",
        configuration_url="https://app.1komma5grad.com/",
    )

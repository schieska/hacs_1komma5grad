"""Per-appliance power from summaryCards (EV, AC, heat pump)."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Coordinator
from .device import system_device_info, system_id_slug


_SECTION_LABEL = {
    "evChargers": "EV charger",
    "acs": "Air conditioning",
    "heatPumps": "Heat pump",
}


class SummaryAppliancePowerSensor(CoordinatorEntity, SensorEntity):
    """Power for one appliance row in summaryCards."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: Coordinator,
        system_id: str,
        section: str,
        appliance_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._system_id = system_id
        self._section = section
        self._appliance_id = appliance_id
        slug_aid = appliance_id.replace("-", "_")
        self._attr_unique_id = (
            f"{DOMAIN}_summary_{section}_{system_id}_{appliance_id}"
        )
        self._attr_suggested_object_id = (
            f"summary_{section.lower()}_{system_id_slug(system_id)}_{slug_aid}"
        )

    @property
    def device_info(self):
        return system_device_info(self.coordinator, self._system_id)

    @property
    def name(self) -> str:
        label = _SECTION_LABEL.get(self._section, self._section)
        short = self._appliance_id.split("-")[-1][:8]
        return f"{label} power {short}"

    @property
    def native_value(self) -> float | None:
        overview = self.coordinator.get_live_data_by_id(self._system_id) or {}
        cards = overview.get("summaryCards") or {}
        key = (
            "evChargers"
            if self._section == "evChargers"
            else "acs"
            if self._section == "acs"
            else "heatPumps"
        )
        for item in cards.get(key) or []:
            if item.get("applianceId") != self._appliance_id:
                continue
            pwr = item.get("power") or {}
            val = pwr.get("value")
            return float(val) if val is not None else None
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

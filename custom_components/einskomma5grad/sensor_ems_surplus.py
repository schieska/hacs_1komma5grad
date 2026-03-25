"""EMS manual settings: heat pump max solar surplus."""

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


class EMSHeatPumpMaxSurplusSensor(CoordinatorEntity, SensorEntity):
    """maxSolarSurplusUsage from a HEAT_PUMP manualSettings entry."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: Coordinator, system_id: str, heat_pump_id: str
    ) -> None:
        super().__init__(coordinator)
        self._system_id = system_id
        self._heat_pump_id = heat_pump_id
        slug = heat_pump_id.replace("-", "_")
        self._attr_unique_id = (
            f"{DOMAIN}_ems_hp_max_surplus_{system_id}_{heat_pump_id}"
        )
        self._attr_suggested_object_id = (
            f"ems_hp_max_surplus_{system_id_slug(system_id)}_{slug}"
        )

    @property
    def device_info(self):
        return system_device_info(self.coordinator, self._system_id)

    @property
    def name(self) -> str:
        short = self._heat_pump_id.split("-")[-1][:8]
        return f"Heat pump max solar surplus {short}"

    def _find_hp_entry(self) -> dict | None:
        ems = (self.coordinator.data.ems_settings or {}).get(self._system_id)
        if not ems:
            return None
        for idx, entry in (ems.get("manualSettings") or {}).items():
            if not isinstance(entry, dict):
                continue
            if entry.get("type") != "HEAT_PUMP":
                continue
            eid = str(entry.get("id") or idx)
            if eid == self._heat_pump_id:
                return entry
        return None

    @property
    def native_value(self) -> float | None:
        entry = self._find_hp_entry()
        if not entry:
            return None
        block = entry.get("maxSolarSurplusUsage") or {}
        val = block.get("value")
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

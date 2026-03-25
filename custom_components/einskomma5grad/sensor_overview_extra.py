"""Sensors from live-overview: self-sufficiency, hero totals, timestamp, HP external power."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import Coordinator
from .device import system_device_info, system_id_slug

if TYPE_CHECKING:
    pass


class SelfSufficiencySensor(CoordinatorEntity, SensorEntity):
    """Autarky / self-sufficiency ratio from liveHeroView."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: Coordinator, system_id: str) -> None:
        super().__init__(coordinator)
        self._system_id = system_id
        self._attr_unique_id = f"{DOMAIN}_self_sufficiency_{system_id}"
        self._attr_suggested_object_id = (
            f"self_sufficiency_{system_id_slug(system_id)}"
        )

    @property
    def device_info(self):
        return system_device_info(self.coordinator, self._system_id)

    @property
    def name(self) -> str:
        return "Self-sufficiency"

    @property
    def native_value(self) -> float | None:
        hero = (
            self.coordinator.get_live_data_by_id(self._system_id) or {}
        ).get("liveHeroView") or {}
        raw = hero.get("selfSufficiency")
        if raw is None:
            return None
        try:
            return round(float(raw) * 100.0, 2)
        except (TypeError, ValueError):
            return None

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class LiveOverviewTotalSocSensor(CoordinatorEntity, SensorEntity):
    """Battery SoC from liveHeroView totalStateOfCharge (may mirror summary battery)."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: Coordinator, system_id: str) -> None:
        super().__init__(coordinator)
        self._system_id = system_id
        self._attr_unique_id = f"{DOMAIN}_live_hero_total_soc_{system_id}"
        self._attr_suggested_object_id = (
            f"live_hero_total_soc_{system_id_slug(system_id)}"
        )

    @property
    def device_info(self):
        return system_device_info(self.coordinator, self._system_id)

    @property
    def name(self) -> str:
        return "Storage state of charge (overview)"

    @property
    def native_value(self) -> float | None:
        hero = (
            self.coordinator.get_live_data_by_id(self._system_id) or {}
        ).get("liveHeroView") or {}
        raw = hero.get("totalStateOfCharge")
        if raw is None:
            return None
        try:
            return round(float(raw) * 100.0, 2)
        except (TypeError, ValueError):
            return None

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class LiveOverviewTimestampSensor(CoordinatorEntity, SensorEntity):
    """When live-overview payload was produced."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: Coordinator, system_id: str) -> None:
        super().__init__(coordinator)
        self._system_id = system_id
        self._attr_unique_id = f"{DOMAIN}_live_overview_timestamp_{system_id}"
        self._attr_suggested_object_id = (
            f"live_overview_timestamp_{system_id_slug(system_id)}"
        )

    @property
    def device_info(self):
        return system_device_info(self.coordinator, self._system_id)

    @property
    def name(self) -> str:
        return "Live data timestamp"

    @property
    def native_value(self) -> datetime | None:
        overview = self.coordinator.get_live_data_by_id(self._system_id) or {}
        raw = overview.get("timestamp")
        if not raw:
            return None
        try:
            return dt_util.parse_datetime(str(raw))
        except (TypeError, ValueError):
            return None

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class HeatPumpExternalPowerSensor(CoordinatorEntity, SensorEntity):
    """Optional external heat pump power from liveHeroView.heatPumpsAggregated.powerExternal."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: Coordinator, system_id: str) -> None:
        super().__init__(coordinator)
        self._system_id = system_id
        self._attr_unique_id = f"{DOMAIN}_heat_pump_external_power_{system_id}"
        self._attr_suggested_object_id = (
            f"heat_pump_external_power_{system_id_slug(system_id)}"
        )

    @property
    def device_info(self):
        return system_device_info(self.coordinator, self._system_id)

    @property
    def name(self) -> str:
        return "Heat pump external power"

    @property
    def native_value(self) -> float | None:
        hero = (
            self.coordinator.get_live_data_by_id(self._system_id) or {}
        ).get("liveHeroView") or {}
        block = hero.get("heatPumpsAggregated") or {}
        ext = block.get("powerExternal")
        if ext is None or not isinstance(ext, dict):
            return None
        val = ext.get("value")
        return float(val) if val is not None else None

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

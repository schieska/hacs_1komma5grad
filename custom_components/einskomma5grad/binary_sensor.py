"""Binary sensors: Heartbeat online, EMS flags."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Coordinator
from .device import system_device_info, system_id_slug


class HeartbeatOnlineBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """live-overview status field (e.g. ONLINE)."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: Coordinator, system_id: str) -> None:
        super().__init__(coordinator)
        self._system_id = system_id
        self._attr_unique_id = f"{DOMAIN}_heartbeat_online_{system_id}"
        self._attr_suggested_object_id = (
            f"heartbeat_online_{system_id_slug(system_id)}"
        )

    @property
    def device_info(self):
        return system_device_info(self.coordinator, self._system_id)

    @property
    def name(self) -> str:
        return "Heartbeat connection"

    @property
    def is_on(self) -> bool | None:
        overview = self.coordinator.get_live_data_by_id(self._system_id) or {}
        status = overview.get("status")
        if status is None:
            return None
        return str(status).upper() == "ONLINE"

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class EMSTimeOfUseBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """EMS timeOfUseEnabled."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: Coordinator, system_id: str) -> None:
        super().__init__(coordinator)
        self._system_id = system_id
        self._attr_unique_id = f"{DOMAIN}_ems_time_of_use_{system_id}"
        self._attr_suggested_object_id = (
            f"ems_time_of_use_{system_id_slug(system_id)}"
        )

    @property
    def device_info(self):
        return system_device_info(self.coordinator, self._system_id)

    @property
    def name(self) -> str:
        return "EMS time-of-use"

    @property
    def is_on(self) -> bool | None:
        ems = (self.coordinator.data.ems_settings or {}).get(self._system_id)
        if not ems:
            return None
        raw = ems.get("timeOfUseEnabled")
        if raw is None:
            return None
        return bool(raw)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class EMSConsentBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """EMS consentGiven."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: Coordinator, system_id: str) -> None:
        super().__init__(coordinator)
        self._system_id = system_id
        self._attr_unique_id = f"{DOMAIN}_ems_consent_{system_id}"
        self._attr_suggested_object_id = f"ems_consent_{system_id_slug(system_id)}"

    @property
    def device_info(self):
        return system_device_info(self.coordinator, self._system_id)

    @property
    def name(self) -> str:
        return "EMS consent"

    @property
    def is_on(self) -> bool | None:
        ems = (self.coordinator.data.ems_settings or {}).get(self._system_id)
        if not ems:
            return None
        raw = ems.get("consentGiven")
        if raw is None:
            return None
        return bool(raw)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class EMSBatteryForecastBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """enableForecastCharging on a BATTERY manualSettings entry."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: Coordinator, system_id: str, manual_key: str
    ) -> None:
        super().__init__(coordinator)
        self._system_id = system_id
        self._manual_key = manual_key
        self._attr_unique_id = (
            f"{DOMAIN}_ems_battery_forecast_{system_id}_{manual_key}"
        )
        self._attr_suggested_object_id = (
            f"ems_battery_forecast_{system_id_slug(system_id)}_{manual_key}"
        )

    @property
    def device_info(self):
        return system_device_info(self.coordinator, self._system_id)

    @property
    def name(self) -> str:
        return "EMS battery forecast charging"

    def _entry(self) -> dict | None:
        ems = (self.coordinator.data.ems_settings or {}).get(self._system_id)
        if not ems:
            return None
        entry = (ems.get("manualSettings") or {}).get(self._manual_key)
        if isinstance(entry, dict) and entry.get("type") == "BATTERY":
            return entry
        return None

    @property
    def is_on(self) -> bool | None:
        entry = self._entry()
        if not entry:
            return None
        raw = entry.get("enableForecastCharging")
        if raw is None:
            return None
        return bool(raw)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Coordinator = hass.data[DOMAIN][config_entry.entry_id].coordinator

    entities: list[BinarySensorEntity] = []
    for system in coordinator.data.systems:
        sid = system.id()
        entities.extend(
            [
                HeartbeatOnlineBinarySensor(coordinator, sid),
                EMSTimeOfUseBinarySensor(coordinator, sid),
                EMSConsentBinarySensor(coordinator, sid),
            ]
        )
    for sid, manual_key in coordinator.consume_new_ems_battery_forecast_specs():
        entities.append(EMSBatteryForecastBinarySensor(coordinator, sid, manual_key))

    async_add_entities(entities)

    def _on_coordinator_update() -> None:
        new_specs = coordinator.consume_new_ems_battery_forecast_specs()
        if not new_specs:
            return
        new_ents = [
            EMSBatteryForecastBinarySensor(coordinator, sid, mk)
            for sid, mk in new_specs
        ]
        hass.async_create_task(async_add_entities(new_ents))

    config_entry.async_on_unload(coordinator.async_add_listener(_on_coordinator_update))

"""Read-only EV detail sensors (target SOC, capacity, schedules, etc.)."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfElectricCurrent, UnitOfEnergy
from homeassistant.core import callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN
from .coordinator import Coordinator
from .device import system_device_info


class _EVExtraSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Coordinator,
        system_id: str,
        ev_id: str,
        *,
        unique_suffix: str,
        suggested_slug: str,
        entity_name: str,
        unit: str | None,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass | None,
        entity_category: EntityCategory | None = None,
        use_text_device_class: bool = False,
    ) -> None:
        super().__init__(coordinator)
        self._system_id = system_id
        self._ev_id = ev_id
        self._attr_name = entity_name
        self._attr_unique_id = f"{DOMAIN}_ev_{unique_suffix}_{system_id}_{ev_id}"
        ev = coordinator.get_ev_data(ev_id)
        ev_part = slugify(ev.ev_name) if ev and ev.ev_name else ev_id.replace("-", "_")
        self._attr_suggested_object_id = f"ev_{suggested_slug}_{ev_part}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_entity_category = entity_category

    @property
    def device_info(self):
        return system_device_info(self.coordinator, self._system_id)

    def _ev(self):
        return self.coordinator.get_ev_data(self._ev_id)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class EVTargetSocSensor(_EVExtraSensor):
    def __init__(self, coordinator: Coordinator, system_id: str, ev_id: str) -> None:
        super().__init__(
            coordinator,
            system_id,
            ev_id,
            unique_suffix="target_soc",
            suggested_slug="target_soc",
            entity_name="EV target charge",
            unit=PERCENTAGE,
            device_class=SensorDeviceClass.BATTERY,
            state_class=SensorStateClass.MEASUREMENT,
        )

    @property
    def native_value(self) -> float | None:
        ev = self._ev()
        return ev.target_soc_percent if ev else None


class EVDefaultSocSensor(_EVExtraSensor):
    def __init__(self, coordinator: Coordinator, system_id: str, ev_id: str) -> None:
        super().__init__(
            coordinator,
            system_id,
            ev_id,
            unique_suffix="default_soc",
            suggested_slug="default_soc",
            entity_name="EV default charge limit",
            unit=PERCENTAGE,
            device_class=SensorDeviceClass.BATTERY,
            state_class=SensorStateClass.MEASUREMENT,
        )

    @property
    def native_value(self) -> float | None:
        ev = self._ev()
        return ev.default_soc_percent if ev else None


class EVCapacitySensor(_EVExtraSensor):
    def __init__(self, coordinator: Coordinator, system_id: str, ev_id: str) -> None:
        super().__init__(
            coordinator,
            system_id,
            ev_id,
            unique_suffix="battery_capacity",
            suggested_slug="battery_capacity",
            entity_name="EV battery capacity",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY_STORAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

    @property
    def native_value(self) -> float | None:
        ev = self._ev()
        return ev.capacity_kwh if ev else None


class EVMinChargingCurrentSensor(_EVExtraSensor):
    def __init__(self, coordinator: Coordinator, system_id: str, ev_id: str) -> None:
        super().__init__(
            coordinator,
            system_id,
            ev_id,
            unique_suffix="min_charging_current",
            suggested_slug="min_charging_current",
            entity_name="EV min charging current",
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

    @property
    def native_value(self) -> float | None:
        ev = self._ev()
        return ev.min_charging_current_a if ev else None


class EVDepartureTimeSensor(_EVExtraSensor):
    def __init__(self, coordinator: Coordinator, system_id: str, ev_id: str) -> None:
        super().__init__(
            coordinator,
            system_id,
            ev_id,
            unique_suffix="departure_time",
            suggested_slug="departure_time",
            entity_name="EV primary departure time",
            unit=None,
            device_class=None,
            state_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

    @property
    def native_value(self) -> str | None:
        ev = self._ev()
        return ev.departure_time if ev else None


class EVManufacturerSensor(_EVExtraSensor):
    def __init__(self, coordinator: Coordinator, system_id: str, ev_id: str) -> None:
        super().__init__(
            coordinator,
            system_id,
            ev_id,
            unique_suffix="manufacturer",
            suggested_slug="manufacturer",
            entity_name="EV manufacturer",
            unit=None,
            device_class=None,
            state_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

    @property
    def native_value(self) -> str | None:
        ev = self._ev()
        return ev.manufacturer if ev else None


class EVModelSensor(_EVExtraSensor):
    def __init__(self, coordinator: Coordinator, system_id: str, ev_id: str) -> None:
        super().__init__(
            coordinator,
            system_id,
            ev_id,
            unique_suffix="model",
            suggested_slug="model",
            entity_name="EV model",
            unit=None,
            device_class=None,
            state_class=None,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

    @property
    def native_value(self) -> str | None:
        ev = self._ev()
        return ev.model if ev else None


EV_EXTRA_SENSOR_TYPES = (
    EVTargetSocSensor,
    EVDefaultSocSensor,
    EVCapacitySensor,
    EVMinChargingCurrentSensor,
    EVDepartureTimeSensor,
    EVManufacturerSensor,
    EVModelSensor,
)

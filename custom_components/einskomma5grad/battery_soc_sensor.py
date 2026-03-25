from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Coordinator
from .device import system_device_info, system_id_slug


class BatteryStateOfChargeSensor(CoordinatorEntity, SensorEntity):
    """Representation of the Battery State of Charge Sensor."""

    def __init__(
        self, coordinator: Coordinator, system_id: str
    ) -> None:
        """Initialise sensor."""
        super().__init__(coordinator)

        self._system_id = system_id
        self._summary_cards = {}
        self._attr_has_entity_name = True
        self._attr_suggested_object_id = (
            f"battery_state_of_charge_{system_id_slug(system_id)}"
        )

    @property
    def device_info(self):
        """Attach to the Heartbeat system device."""
        return system_device_info(self.coordinator, self._system_id)

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Battery state of charge"

    @property
    def icon(self) -> str:
        soc = self.get_soc()

        if soc is None:
            return "mdi:battery-off"

        if soc < 0.2:
            return "mdi:battery-10"
        if soc < 0.4:
            return "mdi:battery-30"
        if soc < 0.6:
            return "mdi:battery-50"
        if soc < 0.8:
            return "mdi:battery-70"

        return "mdi:battery"

    @property
    def native_unit_of_measurement(self):
        return PERCENTAGE

    @property
    def unique_id(self) -> str:
        """Return unique id."""

        return f"{DOMAIN}_battery_soc_{self._system_id}"

    def get_soc(self) -> None | float:
        """Return the state of the entity."""
        if "battery" not in self._summary_cards:
            return None

        try:
            # External devices like EV chargers and heat pumps have a "power" key in the data
            if "stateOfCharge" in self._summary_cards["battery"]:
                return self._summary_cards["battery"]["stateOfCharge"]
        except KeyError:
            self.coordinator.logger.debug("No data available for %s", "battery")
        except TypeError:
            self.coordinator.logger.debug("No data available for %s", "battery")

        return None

    @property
    def native_value(self) -> None | float:
        if self.get_soc() is None:
            return None

        return float(self.get_soc() * 100)

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return SensorDeviceClass.BATTERY

    @property
    def state_class(self) -> SensorStateClass | str | None:
        """Return the state class of the sensor."""
        return SensorStateClass.MEASUREMENT

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        self._summary_cards = self.coordinator.get_live_data_by_id(self._system_id)[
            "summaryCards"
        ]

        self.async_write_ha_state()

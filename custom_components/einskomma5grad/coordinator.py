"""Integration 101 Template integration using DataUpdateCoordinator."""

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api.client import Client
from .api.error import ApiError
from .api.ev_charger import ChargingMode
from .api.system import System
from .api.systems import Systems
from .const import CONF_EXCLUDED_SYSTEM_IDS, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _parse_excluded_system_ids(options: dict) -> frozenset[str]:
    raw = options.get(CONF_EXCLUDED_SYSTEM_IDS)
    if not raw:
        return frozenset()
    return frozenset(part.strip() for part in str(raw).split(",") if part.strip())

@dataclass
class EVData:
    """Class to hold EV data."""

    ev_name: str | None
    current_soc: float | None
    charging_mode: str | None
    system_id: str | None
    target_soc_percent: float | None = None
    default_soc_percent: float | None = None
    capacity_kwh: float | None = None
    min_charging_current_a: float | None = None
    departure_time: str | None = None
    manufacturer: str | None = None
    model: str | None = None


@dataclass
class SystemsData:
    """Class to hold api data."""

    systems: list[System]

    prices: dict[str, dict] | None = None

    live_overview: dict[str, dict] | None = None

    ems_settings: dict[str, dict | None] | None = None

    ev_data: dict[str, EVData] | None = None

    ev_charging_modes: dict[str, list[str]] | None = None


def _evdata_from_raw(
    raw: dict, system_id: str, ev_name: str | None, current_soc: float | None, mode: str
) -> EVData:
    prof = raw.get("profile") or {}
    cs = raw.get("chargeSettings") or {}
    cap = prof.get("capacity") or {}
    cap_wh = cap.get("value")
    cap_kwh = float(cap_wh) / 1000.0 if cap_wh is not None else None
    min_a = prof.get("minChargingCurrent") or {}
    min_cur = min_a.get("value")
    tgt = cs.get("targetSoc")
    dft = cs.get("defaultSoc")
    return EVData(
        ev_name=ev_name,
        current_soc=current_soc,
        charging_mode=mode,
        system_id=system_id,
        target_soc_percent=round(float(tgt) * 100.0, 2) if tgt is not None else None,
        default_soc_percent=round(float(dft) * 100.0, 2) if dft is not None else None,
        capacity_kwh=round(cap_kwh, 3) if cap_kwh is not None else None,
        min_charging_current_a=float(min_cur) if min_cur is not None else None,
        departure_time=cs.get("primaryScheduleDepartureTime"),
        manufacturer=prof.get("manufacturer"),
        model=prof.get("model"),
    )

class Coordinator(DataUpdateCoordinator):
    """1KOMMA5GRAD coordinator."""

    data: SystemsData

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""

        self.hass = hass

        # Initialise your api here
        self.api = Client(
            config_entry.data[CONF_USERNAME], config_entry.data[CONF_PASSWORD]
        )

        # set variables from options.  You need a default here incase options have not been set
        self.poll_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        self._excluded_system_ids = _parse_excluded_system_ids(config_entry.options)
        self._summary_appliance_keys: set[str] = set()
        self._ems_battery_keys: set[str] = set()
        self._ems_hp_surplus_keys: set[str] = set()

        # Initialise DataUpdateCoordinator
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            # Method to call on every update interval.
            update_method=self.async_update_data,
            # Polling interval. Will only be polled if there are subscribers.
            # Using config option here but you can just use a value.
            update_interval=timedelta(seconds=self.poll_interval),
        )

    async def async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """

        systems_client = Systems(self.api)

        try:
            systems = await self.hass.async_add_executor_job(systems_client.get_systems)

            if self._excluded_system_ids:
                before = len(systems)
                systems = [
                    s for s in systems if s.id() not in self._excluded_system_ids
                ]
                if len(systems) < before:
                    _LOGGER.info(
                        "Excluded %d Heartbeat system(s) per integration options",
                        before - len(systems),
                    )

            if not systems:
                raise UpdateFailed(
                    "No Heartbeat systems to load (check account or excluded systems option)"
                )

            now = dt_util.now()
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=2)

            prices = {}
            ems_settings = {}
            live_overview = {}
            ev_data = {}
            ev_charging_modes = {}
            for system in systems:
                prices[system.id()] = await self.hass.async_add_executor_job(
                    system.get_prices,
                    start,
                    end,
                )

                try:
                    ems_settings[system.id()] = await self.hass.async_add_executor_job(
                        system.get_ems_settings,
                    )
                except ApiError:
                    _LOGGER.warning(
                        "Failed to get EMS settings for system %s, skipping",
                        system.id(),
                    )
                    ems_settings[system.id()] = None

                live_overview[system.id()] = await self.hass.async_add_executor_job(
                    system.get_live_overview,
                )

                ev_chargers = await self.hass.async_add_executor_job(
                    system.get_ev_chargers,
                )

                for ev_charger in ev_chargers:
                    ev_data[ev_charger.id()] = _evdata_from_raw(
                        ev_charger.raw_data(),
                        system.id(),
                        ev_charger.name(),
                        ev_charger.current_soc(),
                        ev_charger.charging_mode().value,
                    )

                ev_charging_modes[system.id()] = await self.hass.async_add_executor_job(
                    system.get_displayed_ev_charging_modes,
                )

            # What is returned here is stored in self.data by the DataUpdateCoordinator
            return SystemsData(
                systems=systems,
                prices=prices,
                live_overview=live_overview,
                ems_settings=ems_settings,
                ev_data=ev_data,
                ev_charging_modes=ev_charging_modes,
            )
        except ApiError as err:
            raise UpdateFailed(err) from err

    def set_charging_mode(self, system_id: str, ev_id: str, mode: str):
        """Set the charging mode for an EV."""
        systems = Systems(self.api)
        system = systems.get_system(system_id)

        for charger in system.get_ev_chargers():
            if charger.id() == ev_id:
                charger.set_charging_mode(ChargingMode(mode))

    def set_ev_current_soc(self, system_id: str, ev_id: str, soc: float):
        """Set the current state of charge for an EV."""
        systems = Systems(self.api)
        system = systems.get_system(system_id)

        for charger in system.get_ev_chargers():
            if charger.id() == ev_id:
                charger.set_current_soc(soc)
                return

        _LOGGER.error("EV with id %s not found in system %s", ev_id, system_id)

    def get_ev_data(self, ev_id: str) -> EVData | None:
        """Return current state of charge by EV id."""
        if ev_id in self.data.ev_data:
            return self.data.ev_data[ev_id]

        return None

    def get_system_by_id(self, system_id: str) -> System | None:
        """Return device by device id."""
        for system in self.data.systems:
            if system.id() == system_id:
                return system

        return None

    def get_prices_by_id(self, system_id: str) -> dict | None:
        """Return prices by system id."""

        return self.data.prices[system_id]

    def set_ems_auto_mode(self, system_id: str, enable: bool):
        """Enable EMS auto mode."""
        systems = Systems(self.api)
        systems.get_system(system_id).set_ems_mode(enable)

    def get_live_data_by_id(self, system_id: str) -> dict | None:
        """Return prices by system id."""

        return self.data.live_overview[system_id]

    def consume_new_summary_appliance_specs(self) -> list[tuple[str, str, str]]:
        """New (system_id, summary section, applianceId) tuples for summaryCards power sensors."""
        specs: list[tuple[str, str, str]] = []
        for system in self.data.systems:
            sid = system.id()
            overview = (self.data.live_overview or {}).get(sid) or {}
            cards = overview.get("summaryCards") or {}
            for section, list_key in (
                ("evChargers", "evChargers"),
                ("acs", "acs"),
                ("heatPumps", "heatPumps"),
            ):
                for item in cards.get(list_key) or []:
                    aid = item.get("applianceId")
                    if not aid:
                        continue
                    ukey = f"{sid}|{section}|{aid}"
                    if ukey in self._summary_appliance_keys:
                        continue
                    self._summary_appliance_keys.add(ukey)
                    specs.append((sid, section, aid))
        return specs

    def consume_new_ems_battery_forecast_specs(self) -> list[tuple[str, str]]:
        """(system_id, manual_settings_key) for BATTERY manualSettings blocks."""
        specs: list[tuple[str, str]] = []
        for system in self.data.systems:
            sid = system.id()
            ems = (self.data.ems_settings or {}).get(sid)
            if not ems:
                continue
            for idx, entry in (ems.get("manualSettings") or {}).items():
                if not isinstance(entry, dict):
                    continue
                if entry.get("type") != "BATTERY":
                    continue
                ukey = f"{sid}|bat|{idx}"
                if ukey in self._ems_battery_keys:
                    continue
                self._ems_battery_keys.add(ukey)
                specs.append((sid, str(idx)))
        return specs

    def consume_new_ems_hp_surplus_specs(self) -> list[tuple[str, str]]:
        """(system_id, heat_pump_id) for HEAT_PUMP max solar surplus."""
        specs: list[tuple[str, str]] = []
        for system in self.data.systems:
            sid = system.id()
            ems = (self.data.ems_settings or {}).get(sid)
            if not ems:
                continue
            for idx, entry in (ems.get("manualSettings") or {}).items():
                if not isinstance(entry, dict):
                    continue
                if entry.get("type") != "HEAT_PUMP":
                    continue
                hp_id = str(entry.get("id") or idx)
                ukey = f"{sid}|hp|{hp_id}"
                if ukey in self._ems_hp_surplus_keys:
                    continue
                self._ems_hp_surplus_keys.add(ukey)
                specs.append((sid, hp_id))
        return specs

import logging

import requests

from .client import Client, REQUEST_TIMEOUT
from .error import RequestError
from .system import System

_LOGGER = logging.getLogger(__name__)

_NULL_SYSTEM_ID = "00000000-0000-0000-0000-000000000000"


class Systems:
    def __init__(self, client: Client):
        self.client = client

    def get_system(self, system_id: str) -> System:
        try:
            res = requests.get(
                url=self.client.HEARTBEAT_API + "/api/v2/systems/" + system_id,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.client.get_token(),
                },
                timeout=REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as err:
            raise RequestError(f"Failed to get system due to network error: {err}") from err

        if res.status_code != 200:
            raise RequestError("Failed to get system: " + res.text)

        return System(self.client, res.json())

    # Returns a list with all systems the user has access to
    def get_systems(self) -> list[System]:
        try:
            res = requests.get(
                url=self.client.HEARTBEAT_API + "/api/v2/systems",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.client.get_token(),
                },
                timeout=REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as err:
            raise RequestError(f"Failed to get systems due to network error: {err}") from err

        if res.status_code != 200:
            raise RequestError("Failed to get systems: " + res.text)

        systems = res.json()["data"]

        active_systems = []
        for system in systems:
            sid = system["id"]
            if sid == _NULL_SYSTEM_ID:
                continue
            status = system.get("status", "ACTIVE")
            if str(status).upper() != "ACTIVE":
                _LOGGER.debug(
                    "Skipping Heartbeat system %s (status=%s, only ACTIVE is loaded)",
                    sid,
                    status,
                )
                continue
            active_systems.append(system)

        return [System(self.client, row) for row in active_systems]

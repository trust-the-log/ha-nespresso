"""The Nespresso integration."""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NespressoApiError, NespressoAuthError, NespressoClient
from .const import CONF_MARKET, DEFAULT_MARKET, DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    market = entry.data.get(CONF_MARKET, DEFAULT_MARKET)

    client = NespressoClient(
        session,
        access_token=entry.data["access_token"],
        refresh_token=entry.data.get("refresh_token"),
        market=market,
    )

    coordinator = NespressoCoordinator(hass, client, entry.data.get("customer_id"))
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class NespressoCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, client: NespressoClient, customer_id: str | None = None) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.client = client
        self.machines: list[dict] = []
        self.customer_id = customer_id

    async def _async_update_data(self) -> dict:
        try:
            if not self.customer_id:
                self.customer_id = await self.client.get_customer_id()
            if not self.machines:
                self.machines = await self.client.get_machines()

            data = {}
            for machine in self.machines:
                machine_id = machine["id"]
                status = await self.client.get_machine_status(self.customer_id, machine_id)
                presence = await self.client.get_machine_presence(self.customer_id, machine_id)
                data[machine_id] = {"machine": machine, "status": status, "presence": presence}
            return data

        except NespressoAuthError:
            _LOGGER.info("Token expired, attempting refresh")
            if await self.client.refresh_access_token():
                # Retry after refresh
                data = {}
                for machine in self.machines:
                    machine_id = machine["id"]
                    status = await self.client.get_machine_status(self.customer_id, machine_id)
                    presence = await self.client.get_machine_presence(self.customer_id, machine_id)
                    data[machine_id] = {"machine": machine, "status": status, "presence": presence}
                return data
            raise UpdateFailed("Token expired — open Chrome and reconfigure with fresh cookies")

        except NespressoApiError as err:
            raise UpdateFailed(f"API error: {err}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Network error: {err}") from err

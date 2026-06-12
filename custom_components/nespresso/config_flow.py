"""Config flow for Nespresso integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NespressoApiError, NespressoAuthError, NespressoClient
from .const import CONF_MARKET, DEFAULT_MARKET, DOMAIN

_LOGGER = logging.getLogger(__name__)

MARKETS = ["it", "fr", "de", "es", "gb", "us", "ch", "at", "be", "nl", "pt"]

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required("access_token"): str,
        vol.Optional("refresh_token", default=""): str,
        vol.Optional(CONF_MARKET, default=DEFAULT_MARKET): vol.In(MARKETS),
    }
)


class NespressoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nespresso."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            access_token = user_input["access_token"].strip()
            refresh_token = user_input.get("refresh_token", "").strip() or None
            market = user_input.get(CONF_MARKET, DEFAULT_MARKET)

            session = async_get_clientsession(self.hass)
            client = NespressoClient(
                session,
                access_token=access_token,
                refresh_token=refresh_token,
                market=market,
            )
            try:
                customer_id = await client.get_customer_id()
                machines = await client.get_machines()
                if not machines:
                    errors["base"] = "no_machines"
                else:
                    await self.async_set_unique_id(customer_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Nespresso ({market.upper()})",
                        data={
                            "access_token": access_token,
                            "refresh_token": refresh_token,
                            CONF_MARKET: market,
                            "customer_id": customer_id,
                        },
                    )
            except NespressoAuthError as e:
                _LOGGER.error("Auth error: %s", e)
                errors["base"] = "invalid_token"
            except NespressoApiError as e:
                _LOGGER.error("API error: %s", e)
                errors["base"] = "invalid_token"
            except aiohttp.ClientError as e:
                _LOGGER.error("Network error: %s", e)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

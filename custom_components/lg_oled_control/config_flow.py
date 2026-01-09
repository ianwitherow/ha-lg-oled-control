"""Config flow for LG OLED Control integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from bscpylgtv import WebOsClient
from websockets.exceptions import WebSocketException

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_CLIENT_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_NAME, default="LG TV"): str,
    }
)


class LGOLEDConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LG OLED Control."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._host: str = ""
        self._name: str = ""
        self._client_key: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - get device IP."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._name = user_input.get(CONF_NAME, "LG TV")

            # Check if already configured
            await self.async_set_unique_id(self._host)
            self._abort_if_unique_id_configured()

            # Move to pairing step
            return await self.async_step_pairing()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_pairing(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the pairing step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # User confirmed they're ready - attempt pairing
            try:
                client_key = await self._async_pair_tv()
                self._client_key = client_key

                return self.async_create_entry(
                    title=self._name,
                    data={
                        CONF_HOST: self._host,
                        CONF_NAME: self._name,
                        CONF_CLIENT_KEY: self._client_key,
                    },
                )
            except asyncio.TimeoutError:
                errors["base"] = "timeout"
            except ConnectionRefusedError:
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected error during pairing: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="pairing",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={"host": self._host},
        )

    async def _async_pair_tv(self) -> str:
        """Attempt to pair with the TV and return the client key."""
        client = await WebOsClient.create(self._host, ping_interval=None, states=[])

        try:
            await asyncio.wait_for(client.connect(), timeout=60)
            # After successful connection, the client has the key
            client_key = client.client_key
            return client_key
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

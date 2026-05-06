"""Config flow for Control4 AVM."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .avm_client import Avm16Client, AvmError
from .const import (
    CONF_OUTPUT_COUNT,
    CONF_POLL_INTERVAL,
    DEFAULT_OUTPUT_COUNT,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PORT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def _validate_host(host: str, port: int) -> None:
    """Round-trip a single GET to confirm we have an AVM at this address."""
    client = Avm16Client(host, port)
    try:
        await client.async_connect()
        await client.get_route(1)
    finally:
        await client.async_close()


class AvmConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()
            try:
                await _validate_host(host, port)
            except AvmError:
                errors["base"] = "cannot_connect"
            except OSError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"AVM-16S1-B ({host})",
                    data={CONF_HOST: host, CONF_PORT: port},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return AvmOptionsFlow(entry)


class AvmOptionsFlow(OptionsFlow):
    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        opts = self.entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_OUTPUT_COUNT,
                        default=opts.get(CONF_OUTPUT_COUNT, DEFAULT_OUTPUT_COUNT),
                    ): vol.All(int, vol.Range(min=1, max=16)),
                    vol.Optional(
                        CONF_POLL_INTERVAL,
                        default=opts.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                    ): vol.All(int, vol.Range(min=2, max=300)),
                }
            ),
        )

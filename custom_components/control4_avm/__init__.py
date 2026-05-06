"""Control4 AVM-16S1-B integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .avm_client import Avm16Client, AvmError
from .const import (
    ATTR_INPUT,
    ATTR_OUTPUT,
    CONF_OUTPUT_COUNT,
    CONF_POLL_INTERVAL,
    DEFAULT_OUTPUT_COUNT,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PORT,
    DOMAIN,
    SERVICE_SET_ROUTE,
)
from .coordinator import AvmCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.NUMBER, Platform.SELECT]

SET_ROUTE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_OUTPUT): vol.All(int, vol.Range(min=1, max=16)),
        vol.Required(ATTR_INPUT): vol.All(int, vol.Range(min=0, max=16)),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    output_count = entry.options.get(CONF_OUTPUT_COUNT, DEFAULT_OUTPUT_COUNT)
    poll_interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)

    client = Avm16Client(host, port)
    try:
        await client.async_connect()
    except OSError as err:
        _LOGGER.error("Could not open UDP endpoint to %s:%s: %s", host, port, err)
        return False

    coordinator = AvmCoordinator(hass, entry, client, output_count, poll_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _handle_set_route(call: ServiceCall) -> None:
        output = int(call.data[ATTR_OUTPUT])
        input_ = int(call.data[ATTR_INPUT])
        # Apply to every configured AVM (typically just one)
        for record in hass.data[DOMAIN].values():
            try:
                await record["client"].set_route(output, input_)
            except AvmError as err:
                _LOGGER.error("set_route failed: %s", err)
                raise
            await record["coordinator"].async_request_refresh()

    if not hass.services.has_service(DOMAIN, SERVICE_SET_ROUTE):
        hass.services.async_register(
            DOMAIN, SERVICE_SET_ROUTE, _handle_set_route, schema=SET_ROUTE_SCHEMA
        )

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        record = hass.data[DOMAIN].pop(entry.entry_id, None)
        if record:
            await record["client"].async_close()
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_SET_ROUTE)
    return unloaded

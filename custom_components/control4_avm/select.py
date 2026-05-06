"""Select entity per output: pick which input is routed."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .avm_client import Avm16Client
from .const import DEFAULT_INPUT_COUNT, DISCONNECTED_LABEL, DOMAIN
from .coordinator import AvmCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    record = hass.data[DOMAIN][entry.entry_id]
    coordinator: AvmCoordinator = record["coordinator"]
    client: Avm16Client = record["client"]

    entities = [
        AvmRouteSelect(coordinator, client, entry, output)
        for output in range(1, coordinator.output_count + 1)
    ]
    async_add_entities(entities)


class AvmRouteSelect(CoordinatorEntity[AvmCoordinator], SelectEntity):
    """Pick the input routed to a given output."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AvmCoordinator,
        client: Avm16Client,
        entry: ConfigEntry,
        output: int,
    ) -> None:
        super().__init__(coordinator)
        self._client = client
        self._output = output
        self._attr_unique_id = f"{entry.entry_id}_route_out{output}"
        self._attr_name = f"Output {output} source"
        self._attr_options = [DISCONNECTED_LABEL] + [
            f"Input {i}" for i in range(1, DEFAULT_INPUT_COUNT + 1)
        ]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"AVM-16S1-B ({entry.data[CONF_HOST]})",
            manufacturer="Control4",
            model="AVM-16S1-B",
        )

    @property
    def current_option(self) -> str | None:
        state = self.coordinator.data.get(self._output) if self.coordinator.data else None
        if not state or state.get("route") is None:
            return None
        route = state["route"]
        if route == 0:
            return DISCONNECTED_LABEL
        return f"Input {route}"

    async def async_select_option(self, option: str) -> None:
        if option == DISCONNECTED_LABEL:
            input_ = 0
        else:
            input_ = int(option.removeprefix("Input ").strip())
        await self._client.set_route(self._output, input_)
        await self.coordinator.async_request_refresh()

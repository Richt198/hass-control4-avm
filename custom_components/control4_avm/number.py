"""Number entities per output for bass / treble / balance."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .avm_client import Avm16Client
from .const import (
    BALANCE_CENTER, BALANCE_MAX, BALANCE_MIN,
    BASS_CENTER, BASS_MAX, BASS_MIN,
    DOMAIN,
    TREBLE_CENTER, TREBLE_MAX, TREBLE_MIN,
)
from .coordinator import AvmCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ToneSpec:
    key: str
    label: str
    minimum: int
    maximum: int
    center: int
    setter_name: str  # method name on Avm16Client


SPECS: list[_ToneSpec] = [
    _ToneSpec("bass",    "Bass",    BASS_MIN,    BASS_MAX,    BASS_CENTER,    "set_bass"),
    _ToneSpec("treble",  "Treble",  TREBLE_MIN,  TREBLE_MAX,  TREBLE_CENTER,  "set_treble"),
    _ToneSpec("balance", "Balance", BALANCE_MIN, BALANCE_MAX, BALANCE_CENTER, "set_balance"),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    record = hass.data[DOMAIN][entry.entry_id]
    coordinator: AvmCoordinator = record["coordinator"]
    client: Avm16Client = record["client"]

    entities = [
        AvmToneNumber(coordinator, client, entry, output, spec)
        for output in range(1, coordinator.output_count + 1)
        for spec in SPECS
    ]
    async_add_entities(entities)


class AvmToneNumber(CoordinatorEntity[AvmCoordinator], NumberEntity):
    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: AvmCoordinator,
        client: Avm16Client,
        entry: ConfigEntry,
        output: int,
        spec: _ToneSpec,
    ) -> None:
        super().__init__(coordinator)
        self._client = client
        self._output = output
        self._spec = spec
        self._attr_unique_id = f"{entry.entry_id}_{spec.key}_out{output}"
        self._attr_name = f"Output {output} {spec.label}"
        self._attr_native_min_value = spec.minimum
        self._attr_native_max_value = spec.maximum
        self._attr_native_step = 1
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"AVM-16S1-B ({entry.data[CONF_HOST]})",
            manufacturer="Control4",
            model="AVM-16S1-B",
        )

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        st = self.coordinator.data.get(self._output)
        if not st:
            return None
        return st.get(self._spec.key)

    async def async_set_native_value(self, value: float) -> None:
        setter: Callable[[int, int], Awaitable[None]] = getattr(self._client, self._spec.setter_name)
        await setter(self._output, int(round(value)))
        await self.coordinator.async_request_refresh()

"""Media-player entity per output: source, volume, mute."""
from __future__ import annotations

import logging

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .avm_client import Avm16Client
from .const import DEFAULT_INPUT_COUNT, DISCONNECTED_LABEL, DOMAIN, VOL_MAX, VOL_MIN
from .coordinator import AvmCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    record = hass.data[DOMAIN][entry.entry_id]
    coordinator: AvmCoordinator = record["coordinator"]
    client: Avm16Client = record["client"]
    async_add_entities(
        AvmZone(coordinator, client, entry, output)
        for output in range(1, coordinator.output_count + 1)
    )


class AvmZone(CoordinatorEntity[AvmCoordinator], MediaPlayerEntity):
    """One audio zone = one matrix output."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.VOLUME_STEP
    )

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
        self._attr_unique_id = f"{entry.entry_id}_zone_out{output}"
        self._attr_name = f"Output {output}"
        self._attr_source_list = [DISCONNECTED_LABEL] + [
            f"Input {i}" for i in range(1, DEFAULT_INPUT_COUNT + 1)
        ]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"AVM-16S1-B ({entry.data[CONF_HOST]})",
            manufacturer="Control4",
            model="AVM-16S1-B",
        )

    def _state(self) -> dict | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._output)

    @property
    def state(self) -> str | None:
        st = self._state()
        if st is None or st.get("route") is None:
            return None
        return MediaPlayerState.OFF if st["route"] == 0 else MediaPlayerState.ON

    @property
    def source(self) -> str | None:
        st = self._state()
        if st is None or st.get("route") is None:
            return None
        return DISCONNECTED_LABEL if st["route"] == 0 else f"Input {st['route']}"

    @property
    def volume_level(self) -> float | None:
        st = self._state()
        if st is None or st.get("volume") is None:
            return None
        return st["volume"] / VOL_MAX

    @property
    def is_volume_muted(self) -> bool | None:
        st = self._state()
        if st is None or st.get("mute") is None:
            return None
        return bool(st["mute"])

    async def async_select_source(self, source: str) -> None:
        if source == DISCONNECTED_LABEL:
            input_ = 0
        else:
            input_ = int(source.removeprefix("Input ").strip())
        await self._client.set_route(self._output, input_)
        await self.coordinator.async_request_refresh()

    async def async_set_volume_level(self, volume: float) -> None:
        level = max(VOL_MIN, min(VOL_MAX, round(volume * VOL_MAX)))
        await self._client.set_volume(self._output, level)
        await self.coordinator.async_request_refresh()

    async def async_mute_volume(self, mute: bool) -> None:
        await self._client.set_mute(self._output, mute)
        await self.coordinator.async_request_refresh()

    async def async_volume_up(self) -> None:
        st = self._state()
        if not st or st.get("volume") is None:
            return
        await self._client.set_volume(self._output, min(VOL_MAX, st["volume"] + 1))
        await self.coordinator.async_request_refresh()

    async def async_volume_down(self) -> None:
        st = self._state()
        if not st or st.get("volume") is None:
            return
        await self._client.set_volume(self._output, max(VOL_MIN, st["volume"] - 1))
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, int | None] | None:
        st = self._state()
        if st is None:
            return None
        return {
            "bass": st.get("bass"),
            "treble": st.get("treble"),
            "balance": st.get("balance"),
        }

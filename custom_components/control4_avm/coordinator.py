"""DataUpdateCoordinator for the Control4 AVM."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .avm_client import Avm16Client, AvmError
from .const import DEFAULT_OUTPUT_COUNT, DEFAULT_POLL_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class AvmCoordinator(DataUpdateCoordinator):
    """Polls every output's route/volume/mute on a fixed interval."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: Avm16Client,
        output_count: int = DEFAULT_OUTPUT_COUNT,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=poll_interval),
        )
        self.client = client
        self.entry = entry
        self.output_count = output_count

    async def _async_update_data(self) -> dict[int, dict]:
        try:
            return await self.client.get_all_outputs(self.output_count)
        except AvmError as err:
            raise UpdateFailed(f"Polling AVM failed: {err}") from err

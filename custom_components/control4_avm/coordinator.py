"""DataUpdateCoordinator for the Control4 AVM."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .avm_client import Avm16Client, AvmError
from .const import (
    DEFAULT_INPUT_COUNT,
    DEFAULT_OUTPUT_COUNT,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    VOL_MAX_LEGACY,
)

_LOGGER = logging.getLogger(__name__)


def parse_input_names(raw: str | None) -> list[str]:
    """Parse a comma-separated list of input names, in input order.

    A blank entry keeps the default "Input N" label for that slot; trailing
    blanks are dropped. Capped at the 16 physical inputs.
    """
    if not raw:
        return []
    names = [name.strip() for name in raw.split(",")]
    while names and not names[-1]:
        names.pop()
    return names[:DEFAULT_INPUT_COUNT]


class AvmCoordinator(DataUpdateCoordinator):
    """Polls every output's route/volume/mute on a fixed interval."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: Avm16Client,
        output_count: int = DEFAULT_OUTPUT_COUNT,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
        volume_max: int = VOL_MAX_LEGACY,
        input_names: str | None = None,
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
        self.volume_max = volume_max
        self.input_names = parse_input_names(input_names)

    @property
    def input_labels(self) -> list[str]:
        """Labels for the selectable inputs, in input order (input 1 first).

        When names are configured, only the named inputs are offered;
        otherwise all 16 inputs appear as "Input N".
        """
        if self.input_names:
            return [
                name or f"Input {i}"
                for i, name in enumerate(self.input_names, start=1)
            ]
        return [f"Input {i}" for i in range(1, DEFAULT_INPUT_COUNT + 1)]

    def input_label(self, input_: int) -> str:
        """Label for input number ``input_``, falling back to "Input N"."""
        if 1 <= input_ <= len(self.input_names) and self.input_names[input_ - 1]:
            return self.input_names[input_ - 1]
        return f"Input {input_}"

    def input_for_label(self, label: str) -> int | None:
        """Input number for a source label, or None if unrecognized.

        The default "Input N" form is always accepted so existing automations
        keep working after inputs are renamed.
        """
        for i, known in enumerate(self.input_labels, start=1):
            if known == label:
                return i
        if label.startswith("Input "):
            try:
                input_ = int(label.removeprefix("Input ").strip())
            except ValueError:
                return None
            if 1 <= input_ <= DEFAULT_INPUT_COUNT:
                return input_
        return None

    async def _async_update_data(self) -> dict[int, dict]:
        try:
            return await self.client.get_all_outputs(self.output_count)
        except AvmError as err:
            raise UpdateFailed(f"Polling AVM failed: {err}") from err

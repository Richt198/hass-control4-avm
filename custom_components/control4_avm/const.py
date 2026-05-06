"""Constants for Control4 AVM-16S1-B integration."""
from __future__ import annotations

DOMAIN = "control4_avm"

DEFAULT_PORT = 8750
DEFAULT_OUTPUT_COUNT = 16
DEFAULT_INPUT_COUNT = 16
DEFAULT_POLL_INTERVAL = 10  # seconds

# Wire-level value ranges (verified against a real AVM-16S1-B by probing).
# AVM rejects out-of-range writes with reply code "v01".
VOL_MIN, VOL_MAX = 0, 25            # 0x00..0x19; default for unused outputs is 21.
BASS_MIN, BASS_MAX, BASS_CENTER = 0, 12, 6
TREBLE_MIN, TREBLE_MAX, TREBLE_CENTER = 0, 12, 6
BALANCE_MIN, BALANCE_MAX, BALANCE_CENTER = 0, 50, 25  # 0=full left, 50=full right

CONF_OUTPUT_COUNT = "output_count"
CONF_INPUT_COUNT = "input_count"
CONF_POLL_INTERVAL = "poll_interval"

DISCONNECTED_LABEL = "Disconnected"

SERVICE_SET_ROUTE = "set_route"
ATTR_OUTPUT = "output"
ATTR_INPUT = "input"

"""Constants for Control4 AVM-16S1-B integration."""
from __future__ import annotations

DOMAIN = "control4_avm"

DEFAULT_PORT = 8750
DEFAULT_OUTPUT_COUNT = 16
DEFAULT_INPUT_COUNT = 16
DEFAULT_POLL_INTERVAL = 10  # seconds

# Wire-level value ranges (verified against a real AVM-16S1-B by probing).
# AVM rejects out-of-range writes with reply code "v01".
# Volume scale differs by model: the AVM-16S1-B accepts 0..25 (0x00..0x19),
# while the C4-16ZAMSV3-B uses 0..100 (0x00..0x64). The scale in use is a
# per-entry option, auto-detected on first setup (see __init__.py).
VOL_MIN = 0
VOL_MAX_LEGACY = 25
VOL_MAX_WIDE = 100
VOL_MAX_CHOICES = {
    VOL_MAX_LEGACY: "0-25 (AVM-16S1-B)",
    VOL_MAX_WIDE: "0-100 (C4-16ZAMSV3-B)",
}
BASS_MIN, BASS_MAX, BASS_CENTER = 0, 12, 6
TREBLE_MIN, TREBLE_MAX, TREBLE_CENTER = 0, 12, 6
BALANCE_MIN, BALANCE_MAX, BALANCE_CENTER = 0, 50, 25  # 0=full left, 50=full right

CONF_OUTPUT_COUNT = "output_count"
CONF_INPUT_COUNT = "input_count"
CONF_INPUT_NAMES = "input_names"
CONF_POLL_INTERVAL = "poll_interval"
CONF_VOLUME_MAX = "volume_max"

DISCONNECTED_LABEL = "Disconnected"

SERVICE_SET_ROUTE = "set_route"
ATTR_OUTPUT = "output"
ATTR_INPUT = "input"

# Control4 AVM-16S1-B — Home Assistant integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Maintained](https://img.shields.io/badge/maintained-yes-brightgreen)

A fully local Home Assistant integration for the **Control4 AVM-16S1-B** 16×16 audio matrix. It talks directly to the matrix over UDP — **no Control4 controller, no cloud account, no dealer involvement**.

The official Control4 integration requires a dealer-provisioned cloud account and uses the controller as a relay. This one cuts both out: HA owns the matrix end-to-end.

---

## Features

- **`media_player` per output (×16)** — source, volume, mute; bass/treble/balance exposed as state attributes.
- **`select` per output (×16)** — bare dropdown if you just want routing.
- **`number` sliders per output (×48)** — bass, treble, balance with the device's verified ranges.
- **`control4_avm.set_route` service** — `{output: 3, input: 5}` for scripts and automations.
- **Local-polling only** — direct UDP to port 8750, no internet egress.
- **Config flow** — set up entirely from the UI; no YAML.

## Compatible hardware

| Model | Status |
|---|---|
| Control4 AVM-16S1-B | ✅ Verified end-to-end (capture + ABI probe) |
| Control4 C4-16ZAMSV3-B | ⚠️ Reported working. Uses a 0-100 volume scale, supported from v0.3.0 (see [issue #1](https://github.com/Richt198/hass-control4-avm/issues/1)) |
| Other Control4 "AVSwitch IP" family devices | Untested but likely compatible (same `c4.asw.*` command set) |
| Triad AMS-16 / AMS-8 | ❌ Different protocol — use a different integration |

## Installation

### HACS (recommended)

1. In Home Assistant: **HACS → ⋮ (top-right) → Custom repositories**.
2. Repository URL: `https://github.com/Richt198/hass-control4-avm` · Category: **Integration**.
3. Install **Control4 AVM-16S1-B Audio Matrix**.
4. **Settings → System → Restart Home Assistant**.
5. **Settings → Devices & Services → Add Integration → "Control4 AVM-16S1-B"** → enter the matrix's IP.

### Manual

```bash
cd /config
git clone https://github.com/Richt198/hass-control4-avm.git /tmp/control4_avm
cp -r /tmp/control4_avm/custom_components/control4_avm custom_components/
```
Then restart HA and add the integration.

## Updating and choosing a version

Releases are listed on the [Releases page](https://github.com/Richt198/hass-control4-avm/releases). Each one says what changed and whether any settings need checking afterwards.

### Stable updates

When a new stable release is published, HACS shows it as an update under **Settings → Updates**. Install it, then restart Home Assistant. The new code is not loaded until the restart.

### Trying a beta (pre-release)

Fixes are published as pre-releases first (for example `v0.3.0-beta.1`) so they can be tested before everyone receives them. HACS hides pre-releases unless you opt in:

1. **Settings → Devices & services → HACS**, open the **Control4 AVM-16S1-B Audio Matrix** device.
2. Enable the **Pre-release** entity (it is disabled by default), then switch it on.
3. HACS now offers the beta as an update. Install it and restart Home Assistant.

Alternatively, in **HACS → Control4 AVM-16S1-B Audio Matrix → ⋮ → Redownload**, choose a specific version from the list.

If you test a beta, please comment on the related issue to say whether it worked.

### Rolling back

**HACS → Control4 AVM-16S1-B Audio Matrix → ⋮ → Redownload**, pick the previous version (for example `v0.2.0`), then restart Home Assistant. Switch the **Pre-release** entity off again if you no longer want beta updates.

## What you get

After setup, per output (16 in total):

| Entity | Purpose |
|---|---|
| `media_player.output_N` | Source / volume / mute. Tone values are in `attributes`. |
| `select.output_N_source` | Just the source picker (if `media_player` is overkill for your dashboard). |
| `number.output_N_bass` | Bass (0–12, centre 6) |
| `number.output_N_treble` | Treble (0–12, centre 6) |
| `number.output_N_balance` | Balance (0–50, centre 25; 0 = full left, 50 = full right) |

### Service: `control4_avm.set_route`

```yaml
service: control4_avm.set_route
data:
  output: 3       # 1–16
  input: 5        # 1–16, or 0 to disconnect
```

### Example automation: kitchen plays whatever the lounge is playing

```yaml
trigger:
  - platform: state
    entity_id: media_player.output_2   # lounge
    attribute: source
action:
  - service: media_player.select_source
    target:
      entity_id: media_player.output_5  # kitchen
    data:
      source: "{{ state_attr('media_player.output_2', 'source') }}"
```

## Configuration options

After install, **Configure** the integration to tweak:

| Option | Default | Notes |
|---|---|---|
| Number of outputs | 16 | Reduce if your unit is the 8-output variant. |
| Poll interval (seconds) | 10 | Lower = snappier UI but more UDP traffic. The full state takes ~1.5s to fetch, so don't go below 3s. |
| Volume scale | Auto-detected | `0-25` for the AVM-16S1-B, `0-100` for the C4-16ZAMSV3-B. Detected on first setup; if 100% in Home Assistant is quieter than the front panel allows, set this to `0-100`. |

## Wire protocol (for the curious / for porting)

Plain ASCII over UDP/8750, CRLF-terminated. Reverse-engineered from a packet capture between an HC250 controller and the matrix, then verified by direct probing.

```text
Frame:   0<verb><seq:4hex> <command> [<args>]\r\n
Verbs:   s = SET, g = GET (client → AVM)
         r = REPLY, t = NOTIFY (AVM → client)
Reply:   0r<seq> <code> [<echo>]   — code "000" OK, "v01" out-of-range, "n01" unknown
Numbers: 2-digit lowercase hex; outputs/inputs 1..16 = 01..10
```

| Function | Command | Range |
|---|---|---|
| Route | `c4.asw.out <out> <in>` (set) / `c4.asw.in <out>` (get) | input `00` disconnects, `01..10` selects |
| Volume | `c4.asw.vol <out> <v>` | `00..19` (0..25) on AVM-16S1-B, `00..64` (0..100) on C4-16ZAMSV3-B |
| Mute | `c4.asw.mute <out> <m>` | `00` off, `01` on |
| Bass | `c4.asw.bass <out> <v>` | `00..0c` (0..12), centre `06` |
| Treble | `c4.asw.treble <out> <v>` | `00..0c` (0..12), centre `06` |
| Balance | `c4.asw.bal <out> <v>` | `00..32` (0..50), centre `19` (25). 0 = L, 50 = R. |

Co-existence with an HC250 is *technically* fine on the wire (UDP is stateless, the AVM replies to whoever asked), but if both the HC250 and HA are pushing state, whichever wrote last wins. Pick one source of truth — see Troubleshooting below.

## Troubleshooting

**"My changes from HA keep reverting after a few seconds."**
The HC250 still owns the AVM in your Composer project. It re-asserts state on its own cycle. Fix: in Composer Pro, remove the AVM device from the project and refresh navigators. After that, HA is the sole writer.

**"`Cannot connect` when adding the integration."**
- Ping the AVM: `ping <ip>`. The AVM uses MAC OUI `00:0F:FF`. If it doesn't ping, network-side issue.
- Check nothing else is bound to UDP/8750 on the HA host (rare).
- The AVM only listens on UDP — TCP probes won't reveal it.

**"Some outputs show `unknown`/`unavailable` after polling."**
The device occasionally drops UDP packets under load. The integration retries once. If you see persistent gaps, raise the poll interval in the integration options.

**"The `media_player` doesn't show a `playing` state, just `on`/`off`."**
Correct — the AVM is a switch, not a media source. State reflects whether an input is routed. Use the `source` attribute to know which input.

## How the protocol was discovered

In case you want to do the same for a sibling device:

1. **Composer-side `.c4d.dll`** — decompiled, but it's only the GUI. The real packet logic lives on the controller.
2. **Runtime `.c4l`** — extracted off the HC250 over SSH (`/mnt/internal/drivers/avswitch_ip_control4.c4l`). Stripped ARM ELF, but its symbols (`HandleMibRsp...`, `c4.asw.*`) confirm command names.
3. **Packet capture** — port mirror on the upstream switch (Aruba 2930F: `mirror 1 remote ip ...`) → tshark on the laptop with the HP-ERM dissector → decoded the inner UDP payloads → plain ASCII commands.
4. **Range probing** — a small UDP client iterating values until the AVM rejected with `v01`, then restoring originals.

The full packet-capture approach is documented in the Git history and `dev/` scripts.

## Contributing

PRs welcome. Useful additions:
- Support for the AVM-8 variant (8 outputs).
- Loudness/EQ commands (the runtime driver references `LOUDNESS_*` but I haven't decoded the wire form yet).
- Input-gain control (the `SetInputGainLevel` symbol exists; needs probing).

## License

MIT — see [LICENSE](LICENSE).

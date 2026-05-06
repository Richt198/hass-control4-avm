# Control4 AVM-16S1-B

Local Home Assistant control of the Control4 AVM-16S1-B 16x16 audio matrix.

## What you get

- 16 `media_player` entities (one per output) — source, volume, mute, plus bass/treble/balance attributes
- 16 `select` entities for direct source picking
- 48 `number` entities (bass/treble/balance × 16 outputs)
- A `control4_avm.set_route` service for automations

## Local-only

No cloud, no Control4 dealer account, no controller required. The integration speaks the AVM's native ASCII protocol over UDP/8750 directly.

## After install

Restart HA, then add the integration via **Settings → Devices & Services → Add Integration**, and enter the matrix's IP address.

# Windows SoulFrame Device Simulator

For the complete Windows three-terminal workflow and LAN notes, see the [development guide](../docs/DEVELOPMENT.md). This document covers simulator-specific behavior.

## Existing-agent audit

`agent.py` remains the Raspberry Pi entry point. It registers a device, persists
its token in `/home/admin/soulframe/config/device.json`, polls `/device/sync`,
caches assigned media, launches fullscreen Pi-configured `mpv`, reports runtime
telemetry, and acknowledges dashboard commands. Its startup path, cache paths,
mpv arguments, and Linux hardware probes are unchanged.

The simulator is an additional client. Shared HTTP registration, sync, download
authentication, command acknowledgement, and media filename helpers live in
`device_protocol.py`; graphical playback and storage remain platform-specific.

## Install on Windows

1. Install Python 3 with Tkinter and [mpv](https://mpv.io/installation/) and put `mpv.exe`
   on `PATH`.
2. From `soulframe-agent`, install simulator dependencies:

```powershell
py -m pip install -r simulator_requirements.txt
```

3. Start the backend, then run:

```powershell
$env:SOULFRAME_API_URL = "http://localhost:8000"
py agent.py --simulator
```

`py simulator.py` is equivalent. The first launch stores only simulator identity,
logs, playlists, and cached media in `%LOCALAPPDATA%\SoulFrameSimulator`; it never
reads or writes the Raspberry Pi's `/home/admin/soulframe` files.

## Pair, assign, and inspect

The window displays the backend-issued pairing code and QR code. Claim that code
from the existing SoulFrame web app, then open the simulator device and choose
**Assign Content**. Direct ready-media assignment and playlists use the same sync
contract as a Pi device and appear automatically on the next poll.

The top controls force a sync, clear only the simulator cache, toggle fullscreen,
and simulate an offline connection. Logs are at
`%LOCALAPPDATA%\SoulFrameSimulator\logs\simulator.log`; telemetry and log tail
appear in the existing device runtime dashboard.

## Limits and verification

The simulator reports genuine desktop disk/uptime/playback-error data. Pi-only
temperature, CPU-frequency, and hardware-throttling values are intentionally not
fabricated. Embedded playback requires Windows mpv support; if mpv is not on
PATH, the window presents an actionable playback error while pairing/sync still
work. The Pi agent was syntax-regression checked only; no physical Pi was used.

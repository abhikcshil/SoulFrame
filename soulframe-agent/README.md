# SoulFrame device clients

This directory contains two polling clients that use the shared `device_protocol.py` helpers:

- `agent.py`: Raspberry Pi/Linux client. It renders pairing/error screens, caches assigned media under `/home/admin/soulframe`, and launches fullscreen mpv.
- `simulator.py`: Windows Tkinter client. It stores all state under `%LOCALAPPDATA%\SoulFrameSimulator` and embeds mpv in a desktop window.

Both clients register a device, obtain a pairing code, sync assignments/configuration/commands, download only assigned ready media, acknowledge commands, and report a runtime snapshot. They do not share identity or cache paths.

## Choose a guide

- [Physical Pi/Linux setup](SETUP_DEVICE.md)
- [Windows simulator](SIMULATOR.md)
- [Repository development guide](../docs/DEVELOPMENT.md)
- [Architecture and protocol overview](../docs/ARCHITECTURE.md)

## Tests

```powershell
cd soulframe-agent
python -m unittest tests.test_simulator
```

These tests exercise simulator behavior and protocol assumptions with mocks. They do not prove physical display, mpv decoder, X11, hardware telemetry, or Raspberry Pi autostart behavior.

# SoulFrame Device Setup (Testing-Focused)

## What This Agent Now Does

The device runs a clear state-driven loop with explicit states:

- `unpaired`
- `paired_idle`
- `playing`
- `playback_error`

It also shows a debug overlay (device_id, content_revision, last sync time) for test verification.
Its regular sync payload reports app/runtime state, free storage, temperature and CPU frequency when the Pi exposes them, MPV dropped frames when available, playback errors, and a short agent-log tail for the dashboard runtime panel.

## Requirements (Raspberry Pi / Linux)

- Python 3
- `mpv`
- `qrencode`
- `python3-pil` (Pillow)
- `requests`

Install:

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-pil mpv qrencode
pip3 install requests pillow
```

## Device Config

Create `/home/admin/soulframe/config/device.json`:

```json
{
  "api_base_url": "http://YOUR_BACKEND_IP:8000",
  "device_name": "Living Room Frame",
  "app_version": "0.2.0",
  "poll_interval_seconds": 15
}
```

No device token is required in config. The agent auto-registers on first start and stores:

- `device_id`
- `device_token`

## Run

```bash
cd /home/admin/soulframe
python3 device_agent.py
```

Or use systemd with `setup_device.sh`.

## Expected State Behavior

1. Unpaired:
- Fullscreen pairing UI
- QR code + pairing code
- Stays until claimed

2. Paired idle:
- "SoulFrame connected"
- Account + device name
- "Waiting for media..."

3. Playing:
- Downloads/caches assigned media (no re-download if unchanged checksum)
- Starts fullscreen mpv playback
- Restarts cleanly when content revision changes

4. Playback error:
- Fullscreen explicit error screen with filename/reason when available
- Continues syncing and auto-recovers when valid content arrives

## Offline Behavior

- Network loss does not crash the process
- Current playback keeps running from local cache
- Sync resumes automatically when network returns

## Useful Test Commands

```bash
# Agent log
tail -f /home/admin/soulframe/logs/agent.log

# MPV log
tail -f /home/admin/soulframe/logs/mpv.log

# Service log (if systemd)
sudo journalctl -u soulframe -f
```

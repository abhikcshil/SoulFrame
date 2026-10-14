# Raspberry Pi/Linux device setup

The physical client is `agent.py`. It assumes a Linux desktop/X11 session for fullscreen mpv and stores its working files in `/home/admin/soulframe`. The repository does not declare a specific Pi model or Raspberry Pi OS release as hardware-certified; validate display playback on the target device.

## Prerequisites

- Raspberry Pi OS/Linux with Python 3 and an active display session.
- Network access to the SoulFrame backend.
- `mpv`, `qrencode`, Pillow, and `requests`.

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-pil mpv qrencode
pip3 install requests pillow
```

## Deploy the agent

Create the expected directories, then copy **all** current client modules from this repository. Do not rely on the placeholder download URL in `setup_device.sh` as a deployment source.

```bash
mkdir -p /home/admin/soulframe/{config,cache,media,logs}
# Copy agent.py and device_protocol.py into /home/admin/soulframe by your chosen deployment method.
```

Create `/home/admin/soulframe/config/device.json`:

```json
{
  "api_base_url": "http://YOUR_BACKEND_HOST:8000",
  "device_name": "Living Room Frame",
  "app_version": "0.2.0",
  "poll_interval_seconds": 15
}
```

On first successful registration, the agent adds `device_id` and `device_token` to this local file. Keep it private; do not put it in source control or copy it to another device.

## Run and pair

```bash
cd /home/admin/soulframe
python3 agent.py
```

The unclaimed display shows pairing information. Sign in to the dashboard, use **Claim Device**, enter the displayed pairing code, then assign ready media. The agent reports state, storage/cache data, logs, and Pi metrics when exposed by the OS.

## systemd autostart

`setup_device.sh` shows the service shape, but inspect/update it for your deployment method before use. A service must run the copied `agent.py` as the display-session user and set the correct `DISPLAY`/`XDG_RUNTIME_DIR` values. After creating `/etc/systemd/system/soulframe.service`:

```bash
sudo systemctl daemon-reload
sudo systemctl enable soulframe.service
sudo systemctl start soulframe.service
sudo journalctl -u soulframe -f
```

## Logs and hardware diagnostics

```bash
tail -n 50 -f /home/admin/soulframe/logs/agent.log
tail -n 50 -f /home/admin/soulframe/logs/mpv.log
vcgencmd measure_temp
vcgencmd measure_clock arm
vcgencmd get_throttled
```

The agent writes `agent.log`; mpv log availability depends on the installed mpv invocation/configuration. A missing sensor value in the dashboard means the OS/client could not provide it. See [troubleshooting](../docs/TROUBLESHOOTING.md#raspberry-pi-diagnostics) for diagnostic guidance.

## Updating safely

Stop the service, copy compatible versions of `agent.py` **and** `device_protocol.py`, preserve `config/device.json`, then restart and inspect logs. Changes that alter the sync contract may require updating all client modules together. Verify on a physical display after an update; the Windows simulator cannot validate Pi GPU, HDMI, X11, or thermal behavior.

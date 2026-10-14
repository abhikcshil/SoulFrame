# Troubleshooting

Start with the terminal output and the browser/device logs. Preserve the database and media directory while diagnosing; deleting either is not a routine first step.

## Phone cannot open the dashboard

1. Run Vite with `npm run dev:host`, not a loopback-only host.
2. Open `http://<development-pc-lan-ip>:5173` from the phone, with both devices on the same LAN.
3. Allow ports `5173` and `8000` through Windows Firewall on the Private profile.
4. Confirm `http://<development-pc-lan-ip>:8000/health` works from the phone.

## Dashboard opens but login reports a load/network error

Verify the backend is running and reachable from the phone. Inspect the browser network error, backend terminal, `VITE_API_BASE_URL`, and CORS origin. Do not configure the phone to use `localhost`; it names the phone. The frontend's loopback rewrite only helps when the page itself is opened through the PC's LAN address.

## Database/migration errors

Activate the same virtual environment used to run the API, then inspect schema state:

```powershell
cd soulframe-backend
alembic current
alembic upgrade head
```

Confirm `DATABASE_URL` points at the intended database. A missing-column error usually means the database is behind the Alembic migrations or a different database file is being used.

## Pairing fails

Confirm the agent can reach the backend URL, has retained its `device_id`/`device_token`, and is showing a current pairing code. Pairing codes expire after the configured interval. Check the agent/simulator log and API terminal for registration or sync failures. Do not copy a token manually into the dashboard.

## Upload, normalization, or thumbnails fail

Confirm `ffmpeg -version` and `ffprobe -version` work in the backend environment, the source file matches an allowed MIME type, and `MEDIA_STORAGE_PATH` is writable. Read the media item's processing error and the API log. Existing ready videos do not gain thumbnails automatically until backfill runs:

```powershell
cd soulframe-backend
python -m app.scripts.backfill_thumbnails
```

For a missing browser thumbnail/preview, inspect the media response's `thumbnail_available`, request a new asset URL by reloading, and check browser network status. Asset URLs are private and expire after five minutes.

## Pi/simulator video playback fails

Verify `mpv` is installed/on `PATH`, assigned media is `ready`, and the client can reach the backend. Check cache/log paths, playback error telemetry, and mpv output. A broken-pipe or transient network error alone does not prove mpv crashed; correlate it with agent state and logs.

Simulator-specific checks:

- Run `py -m tkinter` to verify Tkinter.
- Check `%LOCALAPPDATA%\SoulFrameSimulator\logs\simulator.log`.
- Remove or edit its local `device.json` only when intentionally resetting/repointing the simulator identity.

## Raspberry Pi diagnostics

```bash
tail -n 50 -f /home/admin/soulframe/logs/agent.log
tail -n 50 -f /home/admin/soulframe/logs/mpv.log
sudo journalctl -u soulframe -f
vcgencmd measure_temp
vcgencmd measure_clock arm
vcgencmd get_throttled
```

The agent can report some values to the dashboard when the OS exposes them. Temperature/throttling still require physical-device investigation; avoid treating overclocking as a default remedy. Also verify `DISPLAY=:0`, the desktop/X11 session, HDMI/display power, and the systemd service user when fullscreen playback is absent.

## Commands or telemetry are stale

Commands are poll-delivered rather than pushed. Check the device polling interval, recent sync/heartbeat time, and whether the client is offline. Runtime values are the latest snapshot, not a time series. A very old “last seen” value normally means the device has not contacted the backend within the offline threshold.

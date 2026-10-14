# SoulFrame Backend

FastAPI + SQLAlchemy backend for SoulFrame.

## Local Development

1. Create and activate virtualenv.
2. Install dependencies.
3. Install `ffmpeg` and `ffprobe` locally; video uploads are normalized with these command-line tools.
4. Run API.

```bash
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Defaults are local-dev friendly:

- `DATABASE_URL=sqlite:///./local_test.db`
- CORS allows `http://localhost:5173` and common localhost variants

## Key Environment Variables

- `DATABASE_URL`
- `SECRET_KEY`
- `WEB_BASE_URL`
- `MEDIA_STORAGE_PATH`
- `DEVICE_DEFAULT_POLL_INTERVAL_SECONDS`
- `DEVICE_DEFAULT_SYNC_INTERVAL_SECONDS`
- `DEVICE_DEFAULT_CACHE_MAX_BYTES`
- `DEVICE_COMMAND_DEFAULT_EXPIRY_SECONDS`

## Media Normalization Lifecycle

SoulFrame stores user uploads as source assets and separately creates device-safe playback assets.

- `upload`: the original file is stored under `original/` and a media row is created.
- `processing`: the backend creates a playback rendition. Videos are converted to MP4/H.264/AAC/yuv420p, capped at 1080p, with `+faststart`. Images are preserved as playback copies for now.
- `ready`: `playback_storage_key`, playback MIME type, playback size, dimensions, duration, and normalization metadata are saved when available.
- `failed`: the original upload remains stored, `processing_error` explains the failure, and the item is blocked from device assignment/playback.

Devices never consume raw uploads. `/device/sync` only returns `ready` media with playback metadata and `/device/media/{media_id}/download` serves `playback_storage_key`.

For the local MVP, processing runs as a FastAPI background task after the upload response. This gives the dashboard a real transfer phase followed by a visible `processing` phase without requiring a separate worker. A production deployment can replace that task with a job queue while reusing the centralized normalization logic in `app/services/media_processing.py`.

## Library thumbnails and previews

When a video normalization succeeds, FFmpeg extracts a modest JPEG thumbnail at roughly 25% of its duration and stores it as `thumbnails/<media-id>.jpg`. Thumbnail failure does not make a media item unavailable for devices. Both thumbnails and normalized browser previews are private: the dashboard first requests short-lived, ownership-checked signed URLs, then the browser loads those URLs without exposing its JWT. Preview responses support HTTP byte ranges for seeking.

After deploying migration `004`, generate thumbnails for older ready videos with:

```bash
python -m app.scripts.backfill_thumbnails
```

The command is safe to rerun; it skips media that already have a thumbnail key and records individual generation errors without changing playback readiness.

## Device API (MVP Contract)

Device auth is fully separate from user auth.

- User auth: JWT bearer tokens (`/auth/*`)
- Device auth: `X-Device-Token: <token>` and optional `X-Device-Id: <uuid>`

### 1. Device registration and claim

- `POST /device/register`
  - Creates permanent `device_id` and `device_token`
- `POST /device/pair/request` (device-auth)
  - Returns pairing code + claim URL
- `POST /devices/claim` (user-auth)
  - Claims device to user account

### 2. Poll/sync

- `POST /device/sync` (device-auth)
  - Supports initial sync and recurring sync
  - Request includes optional telemetry and known revisions:
    - `known_content_revision`
    - `known_config_revision`
  - Response returns:
    - `has_changes`, `content_changed`, `config_changed`
    - `assigned_content` (with file metadata + download URLs)
    - `runtime_config`
    - `pending_commands`
- `POST /device/checkin` is kept as a compatibility alias to `/device/sync`

### 3. Heartbeat

- `POST /device/heartbeat` (device-auth)
  - Updates runtime status: app version, IP, uptime, free space, health, last error, currently playing IDs
  - Returns current state + poll interval hint

### 4. Commands (poll-friendly queue)

- Queue command from dashboard:
  - `POST /devices/{device_id}/commands` (user-auth)
- List recent command statuses:
  - `GET /devices/{device_id}/commands` (user-auth)
- Device receives pending commands in `/device/sync`
- Device acknowledges completion:
  - `POST /device/commands/{command_id}/ack` (device-auth)

Supported command types:

- `refresh_now`
- `restart_playback`
- `clear_cache`
- `reboot_client`
- `unassign_content`
- `run_health_check`
- `debug_message`

### 5. Config retrieval

- `GET /device/config` (device-auth)
- Also included in `/device/sync` response with `config_revision`

### 6. Media download

- `GET /device/media/{media_id}/download` (device-auth)
  - Access is restricted to currently assigned content
  - Includes ETag header for cache validation support

### 7. Device telemetry for dashboard

- `GET /devices/{device_id}/runtime` (user-auth)
  - Returns latest runtime heartbeat/status snapshot

## Phone / LAN development

Run both services on all interfaces, then open the frontend using the computer's LAN address (for example `http://192.168.1.100:5173`). The frontend derives the API host from the page host, so a default `VITE_API_BASE_URL=http://localhost:8000` is safely rewritten to the LAN host when opened from a phone. The backend CORS policy accepts private-LAN frontend origins.

## Notes

- MVP transport is polling; response models are designed to be reused by future long-poll/SSE/websocket delivery.
- Offline playback behavior is device-side; backend supplies stable assignment metadata and checksums so device can keep cached content unless revisions change.

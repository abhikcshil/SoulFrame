# Development guide

This guide uses Windows PowerShell. The backend defaults to SQLite and local media storage, so no database server is required for the normal local workflow.

## Prerequisites

| Tool | Used by | Notes |
| --- | --- | --- |
| Python 3.11 | Backend Docker image; agent/simulator use Python 3 with modern typing | Use a current Python 3 release compatible with the pinned backend packages. |
| Node.js 18+ and npm | Frontend | Declared in the frontend README. |
| FFmpeg and ffprobe on `PATH` | Backend | Required to normalize videos and generate thumbnails. |
| mpv on `PATH` | Pi agent and Windows simulator | Required for media playback. |
| Tkinter | Windows simulator | Normally bundled with standard Windows Python; verify with `py -m tkinter`. |

## Backend

```powershell
cd soulframe-backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000/health` for a simple health response and `http://localhost:8000/docs` for generated OpenAPI documentation. `Base.metadata.create_all()` also runs at API startup, but use `alembic upgrade head` to apply the versioned schema explicitly.

Create `soulframe-backend/.env` locally when defaults are unsuitable. Do not commit it. See [configuration](#configuration-reference).

## Frontend

```powershell
cd soulframe-frontend
npm install
npm run dev:host
```

The host script runs Vite on `0.0.0.0:5173`. Browse to `http://localhost:5173`. `VITE_API_BASE_URL` is optional; by default, or when configured to loopback, the client uses the host serving the page with port `8000`. Copy `.env.example` to a local ignored env file only when an explicit API URL is necessary.

## Windows simulator

Install mpv and make `mpv.exe` discoverable through `PATH`, then:

```powershell
cd soulframe-agent
py -m pip install -r simulator_requirements.txt
$env:SOULFRAME_API_URL = "http://localhost:8000"
py agent.py --simulator
```

`py simulator.py` is equivalent. The first launch creates `%LOCALAPPDATA%\SoulFrameSimulator\device.json`, registers a device, and displays pairing information. Claim it in the dashboard, then assign ready media. Logs are at `%LOCALAPPDATA%\SoulFrameSimulator\logs\simulator.log`.

## Three-terminal workflow

| Terminal | Command | Expected address/output |
| --- | --- | --- |
| API | `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` | API `8000`, docs `/docs` |
| Dashboard | `npm run dev:host` | Vite `5173` |
| Virtual frame | `py agent.py --simulator` | Tkinter simulator window |

Create an account, claim the simulator, upload a supported video, wait for `Ready`, then use **Devices → Assign Content**. The simulator polls; an assignment need not appear instantly.

## LAN and phone testing

Use the development PC's current LAN address in the browser, for example `http://<development-pc-lan-ip>:5173`; do not copy that placeholder into configuration. The phone and PC must be on the same network. Allow TCP ports `5173` and `8000` through Windows Firewall for the **Private** profile if prompted or blocked.

`localhost` always means the device making the request. A phone's `localhost` is not the PC. The backend CORS configuration accepts localhost, `.local`, and private-LAN browser origins. If login fails on a phone, verify that the backend is reachable at `http://<development-pc-lan-ip>:8000/health` from the phone first.

## Configuration reference

### Backend (`soulframe-backend/.env`)

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./local_test.db` | SQLAlchemy database URL. |
| `SECRET_KEY` | development value | JWT/signature secret; replace outside local development. |
| `ALGORITHM` | `HS256` | JWT algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | User JWT lifetime. |
| `WEB_BASE_URL` | `http://localhost:5173` | Base URL used in pairing/claim links. |
| `CORS_ORIGINS` | localhost list | Comma-separated explicit browser origins. |
| `CORS_ORIGIN_REGEX` | private-LAN/local regex | Additional allowed development origins. |
| `MEDIA_STORAGE_PATH` | `./data/media` | Original, normalized, and thumbnail storage root. |
| `MAX_FILE_SIZE_MB` | `50` | Upload size limit. |
| `ALLOWED_MIME_TYPES` | JPEG/PNG/GIF/WebP/MP4/MOV | Comma-separated accepted MIME types. |
| `PAIRING_CODE_LENGTH`, `PAIRING_CODE_EXPIRY_MINUTES` | `8`, `10` | Pairing behavior. |
| `DEVICE_*` | polling/cache defaults | Runtime defaults delivered to devices. |

### Frontend

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | current page host on port 8000 | Overrides the API base URL. Loopback values are rewritten to the page LAN host when opened remotely. |

### Clients

The Pi reads `/home/admin/soulframe/config/device.json`, including `api_base_url`, `device_name`, `app_version`, and optional polling interval. It writes its `device_id` and `device_token` back to that file after registration. The simulator uses `SOULFRAME_API_URL` only when creating a new `%LOCALAPPDATA%\SoulFrameSimulator\device.json`; edit or remove that file to change an existing simulator API destination.

## Tests and verification

```powershell
# Frontend type check and production bundle
cd soulframe-frontend
npm run build

# Backend thumbnail/unit test (requires backend dependencies and ffmpeg)
cd ..\soulframe-backend
python -m unittest tests.test_media_thumbnails

# Simulator unit tests
cd ..\soulframe-agent
python -m unittest tests.test_simulator
```

The repository has no dedicated frontend test script. Also perform manual browser testing for login, upload progress, processing, preview, direct assignment, playlist assignment, and mobile/LAN access. Simulator testing does not replace a physical Pi display, GPU, thermal, or autostart test.

## Raspberry Pi

Use the [agent setup guide](../soulframe-agent/SETUP_DEVICE.md) for Linux/Pi installation, service setup, logs, and diagnostics.

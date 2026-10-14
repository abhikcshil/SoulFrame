# SoulFrame

SoulFrame is a self-hosted platform for putting motion art on connected display frames. Upload media in a web dashboard, assign a ready video directly or through a playlist, and let a Raspberry Pi frame or Windows simulator download, cache, and loop the assigned content.

## Components

| Component | Purpose |
| --- | --- |
| `soulframe-frontend` | React/Vite dashboard for accounts, media, playlists, assignment, and device monitoring. |
| `soulframe-backend` | FastAPI API, SQLAlchemy models, media processing, pairing, sync, and command queue. |
| `soulframe-agent` | Raspberry Pi/Linux polling agent plus the Windows desktop simulator. |

## Current capabilities

- Account signup/login and device claiming with a pairing code/QR claim URL.
- Direct ready-media assignment, Upload and Assign, and playlist assignment.
- Browser upload progress; background normalization states: `uploaded`, `processing`, `ready`, and `failed`.
- FFmpeg-normalized video playback assets, generated video thumbnails, private browser previews, and thumbnail backfill for existing media.
- Poll-based device sync, local media caching, looping playback, runtime telemetry, recent log tails, and dashboard commands.
- A Raspberry Pi/Linux agent and a Windows Tkinter/mpv simulator using the same device protocol.

This is a local-development/MVP codebase. The simulator is useful for integration testing; physical Pi playback and display setup still require hardware verification.

## Quick start

Open three terminals from the repository root.

```powershell
# Terminal 1: API
cd soulframe-backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

```powershell
# Terminal 2: dashboard
cd soulframe-frontend
npm install
npm run dev:host
```

```powershell
# Terminal 3: optional virtual frame
cd soulframe-agent
py -m pip install -r simulator_requirements.txt
$env:SOULFRAME_API_URL = "http://localhost:8000"
py agent.py --simulator
```

Visit `http://localhost:5173`, create an account, claim the simulator's pairing code, upload a video, then choose **Devices → Assign Content**. See the full [development guide](docs/DEVELOPMENT.md) before using a phone or a physical device.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — data flow, media pipeline, device protocol, and offline behavior.
- [Features](docs/FEATURES.md) — user workflows and what each screen reports.
- [Development](docs/DEVELOPMENT.md) — Windows setup, LAN/mobile access, simulator, configuration, and testing.
- [API](docs/API.md) — implemented endpoint groups and authentication model.
- [Troubleshooting](docs/TROUBLESHOOTING.md) — common frontend, backend, media, simulator, and Pi issues.
- [Backend README](soulframe-backend/README.md), [frontend README](soulframe-frontend/README.md), and [agent README](soulframe-agent/README.md) — component-specific reference.

## Repository layout

```text
SoulFrame/
├── soulframe-backend/   FastAPI app, Alembic migrations, media storage, tests
├── soulframe-frontend/  React TypeScript dashboard
├── soulframe-agent/     Pi agent, shared device protocol, Windows simulator
└── docs/                Cross-component documentation
```

## Stack

- React 18, TypeScript, Vite, React Router, Lucide
- Python, FastAPI, SQLAlchemy, Alembic, SQLite by default (PostgreSQL compose file available)
- FFmpeg/ffprobe for video normalization and thumbnails
- mpv for device playback; Tkinter/Pillow for the Windows simulator UI

## Security and local networking

The backend uses JWT bearer tokens for people and a separate persistent device token for frame clients. Browser thumbnail/preview URLs are short-lived, signed URLs after an ownership check. Never commit `.env`, device JSON identity files, database files, or media storage.

For phone testing, `localhost` means the phone itself—not the development PC. Start the API and Vite on all interfaces, open the PC's LAN address, and allow the development ports through the Windows Private-network firewall. The frontend rewrites a configured loopback API host to the page's LAN host when opened remotely.

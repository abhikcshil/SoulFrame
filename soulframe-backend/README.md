# SoulFrame backend

The backend is a FastAPI/SQLAlchemy service for user authentication, device registration/pairing, assignments, media processing, device polling, telemetry, and commands. See the repository [development guide](../docs/DEVELOPMENT.md), [API reference](../docs/API.md), and [architecture](../docs/ARCHITECTURE.md) for cross-component detail.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The normal local default is SQLite at `sqlite:///./local_test.db`; PostgreSQL is available through `docker-compose.yml`. The Docker image installs FFmpeg, but a local Python run requires `ffmpeg` and `ffprobe` on `PATH` for video processing.

Useful local endpoints:

- `GET /health` — basic health response
- `/docs` — generated OpenAPI/interactive documentation
- `/` — service/version response

## Configuration

Settings are loaded from `.env` in this directory. Never commit a real `.env`. Important settings include `DATABASE_URL`, `SECRET_KEY`, `WEB_BASE_URL`, `MEDIA_STORAGE_PATH`, upload limits/MIME types, CORS, pairing expiry, and device polling/cache defaults. Defaults and meanings are documented in the [development guide](../docs/DEVELOPMENT.md#configuration-reference).

## Media pipeline

Uploaded sources are stored separately from device playback assets. Video processing produces normalized MP4/H.264/AAC/yuv420p media, captures metadata, and tries to generate a modest JPEG thumbnail. Processing states are `uploaded`, `processing`, `ready`, and `failed`. Device sync/download only exposes ready playback assets.

Browser thumbnails and previews use short-lived signed URLs after the authenticated caller has passed media ownership checks. Device downloads require device authentication and are restricted to assigned content.

After applying migration `004`, backfill thumbnails for older ready videos:

```powershell
python -m app.scripts.backfill_thumbnails
```

This is idempotent: existing thumbnail files are skipped; individual failures are recorded without changing playback readiness.

## Schema and tests

Alembic migrations are in `alembic/versions`; apply them with `alembic upgrade head`. The API also calls `Base.metadata.create_all()` on startup for local convenience, but migrations are the upgrade mechanism.

```powershell
python -m unittest tests.test_media_thumbnails
```

The thumbnail test requires installed backend dependencies and FFmpeg. Do not run migrations, backfills, or storage cleanup against a shared database merely as a documentation check.

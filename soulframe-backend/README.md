# SoulFrame Backend

This repository contains the FastAPI backend for the SoulFrame / Smart Frame project.

This README explains how to run the service locally, using Docker, required configuration, migrations, and important security notes.

## Overview

- Framework: FastAPI
- Database: PostgreSQL (SQLAlchemy + Alembic)
- Storage: Local filesystem for media files (configurable)

## Requirements

- Python 3.11
- `pip` (or use Docker)
- PostgreSQL (or use the included `docker-compose.yml` service)

Dependencies are listed in `requirements.txt`.

## Important repository notes

- There's a file named `DockerFile` in the repository. Docker expects a file named `Dockerfile` (lowercase 'f'). Either rename `DockerFile` → `Dockerfile` before building, or specify a custom Dockerfile name when running `docker build`.

## Configuration (env vars)

The app uses pydantic-settings and reads from a `.env` file if present. The important environment variables are:

- `DATABASE_URL` - SQLAlchemy connection string (default: `postgresql://smartframe:smartframe@db:5432/smartframe`).
- `SECRET_KEY` - JWT secret. Must be strong and kept secret in production (>= 32 chars recommended).
- `WEB_BASE_URL` - Frontend URL used when generating claim links (e.g. `http://localhost:3000`).
- `MEDIA_STORAGE_PATH` - Path where uploaded media are stored (default: `./data/media`).
- `ACCESS_TOKEN_EXPIRE_MINUTES` - JWT expiry in minutes.

Example `.env` (create a file named `.env` in the project root):

```env
DATABASE_URL=postgresql://smartframe:smartframe@db:5432/smartframe
SECRET_KEY=replace-with-a-long-random-string-of-32-plus-characters
WEB_BASE_URL=http://localhost:3000
MEDIA_STORAGE_PATH=./data/media
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

## Running locally (without Docker)

1. Create and activate a virtual environment:

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows
source .venv/bin/activate  # macOS / Linux
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file as shown above.

4. Ensure PostgreSQL is reachable via `DATABASE_URL` and run migrations (see Alembic section).

5. Start the app:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API root will be available at `http://localhost:8000/` and interactive docs at `http://localhost:8000/docs`.

## Running with Docker Compose (recommended for quick setup)

1. Rename `DockerFile` → `Dockerfile` if you haven't already.

2. Build and start the stack:

```bash
docker compose up --build
```

This `docker-compose.yml` includes a `db` Postgres service and an `api` service. The compose file also mounts `./data/media` into the container; ensure this directory exists and is writable.

## Alembic / Database migrations

Alembic is included in `alembic/`. The project uses `alembic/env.py` which reads `DATABASE_URL` from the app settings.

If you don't have an `alembic.ini` in the repo root, run Alembic commands with an explicit config or create a minimal `alembic.ini` file. Typical commands:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

When running in Docker, you can either run Alembic from the container or run it from your host pointing to the containerized database.

## Storage / media files

- Media files are stored on-disk at the path configured by `MEDIA_STORAGE_PATH` (default `./data/media`).
- The app ensures the directory exists when saving files, and Dockerfile/compose mounts `./data/media` to persist uploads between container restarts.

## API highlights

- Authentication: JWT via `/auth/login` and `/auth/signup` routes.
- Device checkin & media download endpoints are under `/device` and require a device token header (`X-Device-Token`).
- Media upload endpoint: `POST /media/upload` (multipart file upload). Allowed MIME types and max file size are configurable in `app/config.py`.

## Security & production notes

- Replace the default `SECRET_KEY` and keep it secret (use environment variables / secrets manager).
- Use HTTPS and configure proper CORS origins for the frontend domain. The current CORS configuration in `app/main.py` allows only `http://localhost:3000` and `http://localhost:3001`.
- Consider adding rate-limiting (there is a TODO in the upload endpoint), request size limits, and authentication hardening.

## Recommended next steps

1. Rename `DockerFile` → `Dockerfile`.
2. Create a `.env` or inject env vars in your deployment environment with a proper `SECRET_KEY`.
3. Run Alembic migrations to create the DB schema:

```bash
# Example (host machine running alembic against the running DB)
DATABASE_URL=postgresql://smartframe:smartframe@localhost:5432/smartframe alembic upgrade head
```

4. Add monitoring, logging, and backups for storage and database for production.

## Where I looked

- `requirements.txt`
- `DockerFile` (note the capitalization difference)
- `docker-compose.yml`
- `app/main.py`, `app/config.py`, `app/database.py`, `app/deps.py`
- `app/models/`, `app/routers/`, `app/services/`, `app/utils/`
- `alembic/env.py`

If you'd like, I can also:

- Rename `DockerFile` → `Dockerfile` for you and update the todo list.
- Add a `.env.example` file.
- Add a minimal `alembic.ini` template and a script to run migrations in Docker.

---

If you want any of those changes applied now, tell me which one and I will update the repo.

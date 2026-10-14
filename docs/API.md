# API reference

The live, schema-level reference is available from a running backend at `/docs`. This guide groups the implemented endpoints; UUID path parameters are shown as `{id}`.

## Authentication

| Method | Route | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/signup` | None | Create a user from email/password. |
| POST | `/auth/login` | None | Return a bearer access token. |
| GET | `/auth/me` | User JWT | Return the current user. |

## Dashboard device endpoints

| Method | Route | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/devices` | User JWT | List devices owned by the user. |
| PATCH | `/devices/{id}` | User JWT | Rename an owned device. |
| POST | `/devices/claim` | User JWT | Claim a valid `pairing_code`. |
| POST | `/devices/{id}/assign-media/{media_id}` | User JWT | Directly assign ready media. |
| POST | `/devices/{id}/assign/{playlist_id}` | User JWT | Assign a playlist with ready items. |
| GET/POST | `/devices/{id}/commands` | User JWT | List recent commands or queue one. |
| GET | `/devices/{id}/runtime` | User JWT | Return latest runtime telemetry and assignment summary. |

## Media and playlists

| Method | Route | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/media/upload` | User JWT | Multipart upload under field `file`; processing begins in background. |
| GET | `/media` | User JWT | List owned media and processing metadata. |
| GET | `/media/{id}` | User JWT | Read one owned media item. |
| DELETE | `/media/{id}` | User JWT | Delete media and related assets. |
| POST | `/media/{id}/asset-urls` | User JWT | Issue short-lived thumbnail/preview URLs. |
| GET | `/media/{id}/thumbnail?token=…` | Signed URL | Private thumbnail response. |
| GET | `/media/{id}/preview?token=…` | Signed URL | Private normalized-video response with byte ranges. |
| POST/GET | `/playlists` | User JWT | Create or list owned playlists. |
| PUT | `/playlists/{id}` | User JWT | Replace a playlist name/items after readiness/ownership validation. |

`POST /playlists/devices/{device_id}/assign/{playlist_id}` also exists as a playlist-router assignment route; dashboard code uses the `/devices/{id}/assign/{playlist_id}` route.

## Device-agent endpoints

These calls use `X-Device-Token` and may include `X-Device-Id`. Registration is unauthenticated because it creates a new device identity.

| Method | Route | Purpose |
| --- | --- | --- |
| POST | `/device/register` | Create an identity from device name/app version. |
| POST | `/device/pair/request` | Create/refresh a pairing code and claim URL. |
| POST | `/device/sync` | Return assignment/config changes and pending commands. |
| POST | `/device/checkin` | Compatibility alias for sync. |
| POST | `/device/heartbeat` | Send runtime telemetry and get a polling hint. |
| GET | `/device/config` | Read current runtime configuration. |
| GET | `/device/identity` | Read device pairing/state identity. |
| POST | `/device/commands/{id}/ack` | Acknowledge command result. |
| GET | `/device/media/{media_id}/download` | Download assigned ready playback media only. |

`/device/sync` exchanges known content/config revisions. The response's `assigned_content` distinguishes `media`, `playlist`, and no assignment. Device download URLs and checksums support caching.

## Service endpoints

`GET /` returns a small service/version object and `GET /health` returns `{"status":"ok"}`. These routes are unauthenticated local health checks, not a complete operational health assessment.

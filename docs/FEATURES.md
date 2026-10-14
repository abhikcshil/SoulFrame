# Features and workflows

## Accounts

Use the dashboard to sign up, log in, and view the current account. Dashboard routes require a JWT; an expired/invalid token returns the user to login.

## Pair a device

1. Start a Pi agent or Windows simulator. It registers itself and shows a pairing code and claim URL/QR code while unclaimed.
2. Sign in to the dashboard and open **Claim Device**.
3. Enter the pairing code. The claimed device appears under **Devices**.

Pairing codes expire. The persisted device token is not entered in the dashboard.

## Put content on a frame

From **Devices**, open **Assign Content**. Choose one of these supported paths:

- **Assign from Library**: select a ready media item and assign it directly.
- **Upload and Assign**: upload a file, watch transfer/processing status, then assign it when ready.
- **Assign Playlist**: choose a playlist whose items are all ready.

Only media with a normalized playback asset can be assigned. The device applies the change on its next poll/sync.

## Media Library

The library shows upload state, resolution, duration where known, thumbnails, and video previews. Upload progress is transfer progress; after it reaches 100%, the item may still be `processing`. A failed item preserves the original upload and exposes the recorded processing error. Deleting a media item removes its associated storage assets; use the overflow menu's destructive action deliberately.

Ready videos receive FFmpeg-generated thumbnails. Desktop cards can start muted looping previews on hover/focus; tapping a ready video opens a controlled preview. Legacy ready videos need the thumbnail backfill command described in [Architecture](ARCHITECTURE.md#media-pipeline).

## Playlists

Create a playlist, open it, name it, and add/reorder ready media. Playlist assignment validates that every included item is ready. Playlist editing is separate from direct-media assignment; both remain supported.

## Device monitoring

The device detail/runtime view shows the latest reported online state, last seen time, assignment, playback state, application version, storage/cache values, CPU temperature/frequency when supplied, dropped frames, playback errors, latest error, command status, and available log tail. Missing values mean the current client did not report that metric; the Windows simulator intentionally does not fabricate Pi sensor values.

## Windows simulator

The simulator is a virtual device for registration, pairing, sync, cache, download, commands, and desktop mpv playback. Its offline toggle stops its network behavior without deleting identity. It does not validate HDMI, Pi GPU/decoder behavior, thermal readings, or Pi startup services.

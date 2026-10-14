#!/usr/bin/env python3
"""
SoulFrame Device Agent
State-driven device client for Raspberry Pi/Linux devices.
"""

import json
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from PIL import Image, ImageDraw, ImageFont

# Filesystem layout
BASE_DIR = Path("/home/admin/soulframe")
CONFIG_PATH = BASE_DIR / "config" / "device.json"
CACHE_DIR = BASE_DIR / "cache"
MEDIA_DIR = BASE_DIR / "media"
LOG_DIR = BASE_DIR / "logs"
UI_SCREEN_PATH = CACHE_DIR / "ui_screen.png"
PLAYLIST_PATH = CACHE_DIR / "playlist.m3u"
CACHE_INDEX_PATH = CACHE_DIR / "cache_index.json"
MPV_SOCKET_PATH = CACHE_DIR / "mpv.sock"

for path in [CACHE_DIR, MEDIA_DIR, LOG_DIR, CONFIG_PATH.parent]:
    path.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "agent.log"


class DeviceState(str, Enum):
    UNPAIRED = "unpaired"
    PAIRED_IDLE = "paired_idle"
    PLAYING = "playing"
    PLAYBACK_ERROR = "playback_error"


@dataclass
class DebugOverlay:
    device_id: str = "unknown"
    content_revision: str = "none"
    last_sync: str = "never"


@dataclass
class PlaybackContext:
    last_media_filename: Optional[str] = None
    last_error: Optional[str] = None


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def load_font(size: int):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            try:
                return ImageFont.truetype(candidate, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def load_or_init_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        template = {
            "api_base_url": "http://YOUR_BACKEND_IP:8000",
            "device_name": "SoulFrame Device",
            "app_version": "0.2.0",
            "poll_interval_seconds": 15,
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as handle:
            json.dump(template, handle, indent=2)
        log(f"Created config template at {CONFIG_PATH}; set api_base_url and restart.")
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        cfg = json.load(handle)
    if not cfg.get("api_base_url"):
        log("ERROR: config missing api_base_url")
        sys.exit(1)
    return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as handle:
        json.dump(cfg, handle, indent=2)


def headers(token: Optional[str], device_id: Optional[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if token:
        out["X-Device-Token"] = token
    if device_id:
        out["X-Device-Id"] = device_id
    return out


def register_device(api_base: str, device_name: str, app_version: str) -> Dict[str, Any]:
    url = f"{api_base.rstrip('/')}/device/register"
    payload = {"name": device_name, "app_version": app_version}
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def sync_device(
    api_base: str,
    device_token: str,
    device_id: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    url = f"{api_base.rstrip('/')}/device/sync"
    response = requests.post(
        url,
        json=payload,
        headers=headers(device_token, device_id),
        timeout=12,
    )
    response.raise_for_status()
    return response.json()


def ack_command(
    api_base: str,
    device_token: str,
    device_id: str,
    command_id: str,
    status_value: str,
    message: str = "",
) -> None:
    url = f"{api_base.rstrip('/')}/device/commands/{command_id}/ack"
    payload = {"status": status_value, "message": message}
    response = requests.post(
        url,
        json=payload,
        headers=headers(device_token, device_id),
        timeout=8,
    )
    response.raise_for_status()


def get_free_bytes(path: Path) -> int:
    try:
        st = os.statvfs(str(path))
        return st.f_bavail * st.f_frsize
    except Exception:
        return 0


def get_local_ip() -> Optional[str]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except Exception:
        return None


def read_float_file(path: str, divisor: float = 1.0) -> Optional[float]:
    try:
        raw = Path(path).read_text(encoding="utf-8").strip()
        return float(raw) / divisor
    except Exception:
        return None


def get_temperature_c() -> Optional[float]:
    value = read_float_file("/sys/class/thermal/thermal_zone0/temp", 1000.0)
    if value is not None:
        return round(value, 1)
    try:
        result = subprocess.run(["vcgencmd", "measure_temp"], check=True, capture_output=True, text=True, timeout=2)
        text = result.stdout.strip().replace("temp=", "").replace("'C", "")
        return round(float(text), 1)
    except Exception:
        return None


def get_cpu_frequency_mhz() -> Optional[float]:
    value = read_float_file("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq", 1000.0)
    return round(value, 0) if value is not None else None


def tail_log_lines(path: Path, limit: int = 20) -> List[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return lines[-limit:]
    except Exception:
        return []


def safe_filename(media_id: str, original_filename: str) -> str:
    ext = Path(original_filename).suffix.lower()
    if ext not in [".mp4", ".mov", ".webm", ".mkv", ".gif", ".jpg", ".jpeg", ".png", ".webp"]:
        ext = ".bin"
    return f"{media_id}{ext}"


def load_cache_index() -> Dict[str, Any]:
    if not CACHE_INDEX_PATH.exists():
        return {}
    try:
        with open(CACHE_INDEX_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


def save_cache_index(index: Dict[str, Any]) -> None:
    with open(CACHE_INDEX_PATH, "w", encoding="utf-8") as handle:
        json.dump(index, handle, indent=2)


def download_media_item(
    api_base: str,
    token: str,
    device_id: str,
    item: Dict[str, Any],
    index: Dict[str, Any],
) -> Path:
    media_id = item["media_id"]
    checksum = item.get("checksum", "")
    original_filename = item.get("original_filename", f"{media_id}.bin")
    local_name = safe_filename(media_id, original_filename)
    local_path = MEDIA_DIR / local_name

    cached_meta = index.get(media_id)
    if (
        cached_meta
        and cached_meta.get("checksum") == checksum
        and Path(cached_meta.get("path", "")).exists()
        and local_path.exists()
        and local_path.stat().st_size > 0
    ):
        return local_path

    url = item.get("download_url") or f"{api_base.rstrip('/')}/device/media/{media_id}/download"
    log(f"Downloading media {media_id} -> {local_name}")
    tmp_path = local_path.with_suffix(local_path.suffix + ".part")

    with requests.get(url, headers=headers(token, device_id), stream=True, timeout=30) as response:
        response.raise_for_status()
        with open(tmp_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    handle.write(chunk)
    tmp_path.replace(local_path)
    index[media_id] = {"checksum": checksum, "path": str(local_path), "filename": original_filename}
    save_cache_index(index)
    return local_path


def write_playlist(local_paths: List[Path]) -> None:
    with open(PLAYLIST_PATH, "w", encoding="utf-8") as handle:
        handle.write("#EXTM3U\n")
        for media_path in local_paths:
            handle.write(str(media_path) + "\n")


def stop_process(proc: Optional[subprocess.Popen]) -> None:
    if not proc:
        return
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
            proc.wait(timeout=1)
        except Exception:
            pass


def render_screen(title: str, lines: List[str], debug: DebugOverlay, claim_url: Optional[str] = None) -> None:
    width, height = 1920, 1080
    background = (12, 12, 12)
    text = (245, 245, 245)
    accent = (120, 200, 255)
    warning = (255, 145, 145)

    img = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(img)
    font_title = load_font(64)
    font_body = load_font(36)
    font_small = load_font(24)

    draw.text((80, 80), title, fill=warning if "error" in title.lower() else text, font=font_title)
    y = 220
    for line in lines:
        draw.text((80, y), line, fill=text if not line.startswith("Or enter code") else accent, font=font_body)
        y += 60

    if claim_url:
        qr_path = CACHE_DIR / "qr.png"
        try:
            subprocess.run(["qrencode", "-o", str(qr_path), "-s", "10", claim_url], check=True, capture_output=True)
            qr = Image.open(qr_path).convert("RGB").resize((420, 420), Image.Resampling.NEAREST)
            img.paste(qr, (1390, 280))
        except Exception:
            draw.text((80, y + 20), f"Claim URL: {claim_url}", fill=accent, font=font_small)

    # Debug overlay (top-right)
    overlay_x = width - 600
    overlay_y = 30
    draw.rectangle((overlay_x, overlay_y, width - 30, overlay_y + 140), fill=(0, 0, 0))
    draw.rectangle((overlay_x, overlay_y, width - 30, overlay_y + 140), outline=(90, 90, 90), width=2)
    draw.text((overlay_x + 14, overlay_y + 10), f"device_id: {debug.device_id}", fill=(200, 200, 200), font=font_small)
    draw.text(
        (overlay_x + 14, overlay_y + 50),
        f"content_rev: {debug.content_revision}",
        fill=(200, 200, 200),
        font=font_small,
    )
    draw.text((overlay_x + 14, overlay_y + 90), f"last_sync: {debug.last_sync}", fill=(200, 200, 200), font=font_small)

    img.save(UI_SCREEN_PATH)


def start_mpv_image(image_path: Path) -> subprocess.Popen:
    cmd = [
        "mpv",
        "--fs",
        "--no-osc",
        "--no-border",
        "--no-input-default-bindings",
        "--image-display-duration=inf",
        "--loop=inf",
        str(image_path),
    ]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def start_mpv_playlist(playlist_path: Path) -> subprocess.Popen:
    if MPV_SOCKET_PATH.exists():
        MPV_SOCKET_PATH.unlink(missing_ok=True)
    cmd = [
        "mpv",
        "--fs",
        "--no-osc",
        "--no-border",
        "--no-input-default-bindings",
        "--hwdec=rpi",
        "--loop-playlist=inf",
        f"--playlist={playlist_path}",
        f"--input-ipc-server={MPV_SOCKET_PATH}",
        "--osd-level=1",
        "--osd-font-size=20",
        "--osd-align-x=left",
        "--osd-align-y=top",
        "--osd-margin-x=24",
        "--osd-margin-y=24",
        f"--log-file={LOG_DIR / 'mpv.log'}",
    ]
    return subprocess.Popen(cmd)


def show_mpv_debug_overlay(debug: DebugOverlay) -> None:
    if not MPV_SOCKET_PATH.exists():
        return
    message = f"device_id: {debug.device_id}\\ncontent_rev: {debug.content_revision}\\nlast_sync: {debug.last_sync}"
    command = {"command": ["show-text", message, 60000, 1]}
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(str(MPV_SOCKET_PATH))
            client.sendall((json.dumps(command) + "\n").encode("utf-8"))
    except Exception:
        pass


def get_mpv_dropped_frames() -> Optional[int]:
    """Return MPV's cumulative dropped-frame counter when its IPC socket is live."""
    if not MPV_SOCKET_PATH.exists():
        return None
    try:
        command = {"command": ["get_property", "drop-frame-count"]}
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(0.5)
            client.connect(str(MPV_SOCKET_PATH))
            client.sendall((json.dumps(command) + "\n").encode("utf-8"))
            response = client.recv(4096).decode("utf-8", errors="replace")
        value = json.loads(response).get("data")
        return int(value) if value is not None else None
    except Exception:
        # Older MPV versions may not expose the property; report it as unknown.
        return None


class DeviceAgent:
    def __init__(self) -> None:
        self.config = load_or_init_config()
        self.api_base = self.config["api_base_url"]
        self.device_token = self.config.get("device_token")
        self.device_id = self.config.get("device_id")
        self.device_name = self.config.get("device_name", "SoulFrame Device")
        self.app_version = self.config.get("app_version", "0.2.0")
        self.poll_interval = int(self.config.get("poll_interval_seconds", 15))

        self.state = DeviceState.UNPAIRED
        self.debug = DebugOverlay(device_id=self.device_id or "pending")
        self.playback = PlaybackContext()
        self.mpv_proc: Optional[subprocess.Popen] = None
        self.current_content_revision = "none"
        self.current_config_revision = "none"
        self.last_sync_unix = 0.0
        self.process_start_unix = time.time()
        self.current_media_id: Optional[str] = None
        self.current_playlist_id: Optional[str] = None
        self.playback_errors = 0
        self.cache_index = load_cache_index()

    def ensure_registered(self) -> None:
        if self.device_token and self.device_id:
            return
        log("No device credentials found, registering device...")
        registered = register_device(self.api_base, self.device_name, self.app_version)
        self.device_id = registered["device_id"]
        self.device_token = registered["device_token"]
        self.config["device_id"] = self.device_id
        self.config["device_token"] = self.device_token
        save_config(self.config)
        self.debug.device_id = self.device_id
        log(f"Registered device_id={self.device_id}")

    def transition(self, new_state: DeviceState, **kwargs: Any) -> None:
        if self.state != new_state:
            log(f"State transition: {self.state.value} -> {new_state.value}")
        self.state = new_state

        if new_state == DeviceState.UNPAIRED:
            pairing = kwargs.get("pairing") or {}
            code = pairing.get("pairing_code", "----")
            claim_url = pairing.get("claim_url")
            render_screen(
                "Ready to pair",
                [
                    "Scan the QR code to connect this SoulFrame",
                    f"Or enter code: {code}",
                ],
                self.debug,
                claim_url=claim_url,
            )
            stop_process(self.mpv_proc)
            self.mpv_proc = start_mpv_image(UI_SCREEN_PATH)

        elif new_state == DeviceState.PAIRED_IDLE:
            account_name = kwargs.get("account_name", "unknown")
            device_name = kwargs.get("device_name", self.device_name)
            render_screen(
                "SoulFrame connected",
                [
                    f"Account: {account_name}",
                    f"Device: {device_name}",
                    "Waiting for media...",
                ],
                self.debug,
            )
            stop_process(self.mpv_proc)
            self.mpv_proc = start_mpv_image(UI_SCREEN_PATH)

        elif new_state == DeviceState.PLAYBACK_ERROR:
            self.playback_errors += 1
            filename = kwargs.get("filename") or "unknown"
            reason = kwargs.get("reason") or "Unknown playback error"
            render_screen(
                "Playback error",
                [
                    "Unable to play assigned media",
                    f"Media: {filename}",
                    f"Reason: {reason}",
                ],
                self.debug,
            )
            stop_process(self.mpv_proc)
            self.mpv_proc = start_mpv_image(UI_SCREEN_PATH)

        elif new_state == DeviceState.PLAYING:
            local_paths = kwargs.get("local_paths") or []
            if not local_paths:
                self.transition(DeviceState.PLAYBACK_ERROR, filename=None, reason="No playable media after sync")
                return
            write_playlist(local_paths)
            stop_process(self.mpv_proc)
            self.mpv_proc = start_mpv_playlist(PLAYLIST_PATH)
            time.sleep(0.3)
            show_mpv_debug_overlay(self.debug)

    def process_commands(self, sync_data: Dict[str, Any]) -> Dict[str, bool]:
        flags = {"force_refresh": False, "restart_playback": False, "clear_cache": False, "unassign_content": False}
        for command in sync_data.get("pending_commands", []) or []:
            command_id = command["command_id"]
            command_type = command.get("command_type", "")
            try:
                if command_type == "refresh_now":
                    flags["force_refresh"] = True
                elif command_type == "restart_playback":
                    flags["restart_playback"] = True
                elif command_type == "clear_cache":
                    flags["clear_cache"] = True
                elif command_type == "unassign_content":
                    flags["unassign_content"] = True
                elif command_type == "reboot_client":
                    ack_command(self.api_base, self.device_token, self.device_id, command_id, "succeeded", "restarting")
                    os.execv(sys.executable, [sys.executable, __file__])
                elif command_type == "run_health_check":
                    log("Health check command received")
                elif command_type == "debug_message":
                    payload = command.get("payload") or {}
                    log(f"Debug command: {payload.get('message', payload)}")
                ack_command(self.api_base, self.device_token, self.device_id, command_id, "succeeded", "applied")
            except Exception as exc:
                log(f"Command {command_type} failed: {repr(exc)}")
                try:
                    ack_command(self.api_base, self.device_token, self.device_id, command_id, "failed", repr(exc))
                except Exception:
                    pass
        return flags

    def clear_cache(self) -> None:
        for media_file in MEDIA_DIR.glob("*"):
            if media_file.is_file():
                media_file.unlink(missing_ok=True)
        self.cache_index = {}
        save_cache_index(self.cache_index)
        log("Local media cache cleared")

    def build_sync_payload(self) -> Dict[str, Any]:
        uptime = int(time.time() - self.process_start_unix)
        return {
            "app_version": self.app_version,
            "ip": get_local_ip(),
            "storage_free_bytes": get_free_bytes(MEDIA_DIR),
            "cache_free_bytes": get_free_bytes(CACHE_DIR),
            "uptime_seconds": uptime,
            "current_media_id": self.current_media_id,
            "current_playlist_id": self.current_playlist_id,
            "device_state": self.state.value,
            "temperature_c": get_temperature_c(),
            "cpu_frequency_mhz": get_cpu_frequency_mhz(),
            "dropped_frames": get_mpv_dropped_frames(),
            "playback_errors": self.playback_errors,
            "recent_logs": tail_log_lines(LOG_FILE),
            "known_content_revision": self.current_content_revision,
            "known_config_revision": self.current_config_revision,
            "include_commands": True,
            "last_error": self.playback.last_error,
            "health_status": "ok" if self.state != DeviceState.PLAYBACK_ERROR else "degraded",
        }

    def run(self) -> None:
        log("=" * 60)
        log("SoulFrame Device Agent starting")
        log(f"API: {self.api_base}")
        log("=" * 60)

        self.ensure_registered()
        self.debug.device_id = self.device_id or "unknown"

        while True:
            try:
                if self.state == DeviceState.PLAYING and self.mpv_proc and self.mpv_proc.poll() is not None:
                    code = self.mpv_proc.returncode
                    self.playback.last_error = f"mpv exited with code {code}"
                    self.transition(DeviceState.PLAYBACK_ERROR, filename=self.playback.last_media_filename, reason=self.playback.last_error)

                payload = self.build_sync_payload()
                sync_data = sync_device(self.api_base, self.device_token, self.device_id, payload)

                self.last_sync_unix = time.time()
                self.debug.last_sync = time.strftime("%H:%M:%S")

                device = sync_data.get("device") or {}
                self.debug.device_id = device.get("device_id", self.debug.device_id)
                self.debug.content_revision = sync_data.get("assigned_content", {}).get("content_revision", "none")

                self.poll_interval = int(sync_data.get("runtime_config", {}).get("poll_interval_seconds", self.poll_interval))
                self.current_config_revision = sync_data.get("runtime_config", {}).get("config_revision", self.current_config_revision)

                flags = self.process_commands(sync_data)
                if flags["clear_cache"]:
                    self.clear_cache()
                if flags["restart_playback"] and self.state == DeviceState.PLAYING:
                    self.current_content_revision = "force-reload"
                if flags["unassign_content"]:
                    self.transition(
                        DeviceState.PAIRED_IDLE,
                        account_name=sync_data.get("account_name") or "unknown",
                        device_name=device.get("device_name") or self.device_name,
                    )
                    self.current_content_revision = "none"
                    time.sleep(self.poll_interval)
                    continue

                if not device.get("is_claimed", False):
                    self.current_content_revision = "none"
                    self.transition(DeviceState.UNPAIRED, pairing=sync_data.get("pairing") or {})
                    time.sleep(self.poll_interval)
                    continue

                assigned = sync_data.get("assigned_content") or {}
                items = assigned.get("items") or []
                assignment_type = assigned.get("assignment_type", "none")
                content_revision = assigned.get("content_revision", "none")
                has_items = bool(items)
                content_changed = sync_data.get("content_changed", True) or flags["force_refresh"] or (content_revision != self.current_content_revision)

                if not has_items:
                    self.current_media_id = None
                    self.current_playlist_id = None
                    self.current_content_revision = content_revision
                    self.transition(
                        DeviceState.PAIRED_IDLE,
                        account_name=sync_data.get("account_name") or "unknown",
                        device_name=device.get("device_name") or self.device_name,
                    )
                else:
                    self.current_playlist_id = assigned.get("assigned_playlist_id") if assignment_type == "playlist" else None
                    self.current_media_id = assigned.get("assigned_media_id") if assignment_type == "media" else None
                    if content_changed or self.state != DeviceState.PLAYING:
                        try:
                            local_paths: List[Path] = []
                            for item in items:
                                if not self.current_media_id:
                                    self.current_media_id = item.get("media_id")
                                media_path = download_media_item(
                                    self.api_base,
                                    self.device_token,
                                    self.device_id,
                                    item,
                                    self.cache_index,
                                )
                                local_paths.append(media_path)
                                self.playback.last_media_filename = item.get("original_filename")

                            self.playback.last_error = None
                            self.current_content_revision = content_revision
                            self.transition(DeviceState.PLAYING, local_paths=local_paths)
                        except Exception as exc:
                            self.playback.last_error = repr(exc)
                            self.transition(
                                DeviceState.PLAYBACK_ERROR,
                                filename=self.playback.last_media_filename,
                                reason=str(exc),
                            )
                    else:
                        show_mpv_debug_overlay(self.debug)

            except requests.exceptions.RequestException as exc:
                log(f"Network error: {repr(exc)}")
                # Offline behavior: keep current playback/screen running.
            except Exception as exc:
                log(f"Unhandled error: {repr(exc)}")
                self.playback.last_error = repr(exc)
                if self.state == DeviceState.PLAYING:
                    # Keep playing current cached content if possible.
                    pass
                else:
                    self.transition(DeviceState.PLAYBACK_ERROR, filename=self.playback.last_media_filename, reason=str(exc))

            time.sleep(max(3, self.poll_interval))


def main() -> None:
    agent = DeviceAgent()
    agent.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Shutting down")
    except Exception as fatal:
        log(f"FATAL: {repr(fatal)}")
        sys.exit(1)

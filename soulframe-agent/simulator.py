#!/usr/bin/env python3
"""Windows desktop simulator for a SoulFrame device.

Run ``python agent.py --simulator`` or ``python simulator.py``.  The simulator
uses the real device API, but deliberately stores its identity and media outside
the Raspberry Pi agent's /home/admin/soulframe directory.
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests
import tkinter as tk
from PIL import Image, ImageDraw, ImageFont, ImageTk

from device_protocol import ack_command, headers, register_device, safe_filename, sync_device


class DeviceState(str, Enum):
    UNPAIRED = "unpaired"
    PAIRED_IDLE = "paired_idle"
    PLAYING = "playing"
    PLAYBACK_ERROR = "playback_error"


@dataclass(frozen=True)
class SimulatorPaths:
    root: Path
    config: Path
    cache: Path
    media: Path
    logs: Path

    @classmethod
    def default(cls) -> "SimulatorPaths":
        # LOCALAPPDATA is stable across launches and never overlaps the Pi path.
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".soulframe")) / "SoulFrameSimulator"
        paths = cls(root, root / "device.json", root / "cache", root / "media", root / "logs")
        for path in (paths.root, paths.cache, paths.media, paths.logs):
            path.mkdir(parents=True, exist_ok=True)
        return paths


class SimulatorAgent:
    """Polling device client with simulator-specific storage and playback."""

    def __init__(self, paths: SimulatorPaths, on_screen: Callable[[str, Dict[str, Any]], None]) -> None:
        self.paths = paths
        self.on_screen = on_screen
        self.config = self._load_config()
        self.api_base = self.config["api_base_url"]
        self.device_name = self.config["device_name"]
        self.app_version = self.config["app_version"]
        self.device_id: Optional[str] = self.config.get("device_id")
        self.device_token: Optional[str] = self.config.get("device_token")
        self.poll_interval = int(self.config.get("poll_interval_seconds", 5))
        self.state = DeviceState.UNPAIRED
        self.current_content_revision = "none"
        self.current_config_revision = "none"
        self.current_media_id: Optional[str] = None
        self.current_playlist_id: Optional[str] = None
        self.last_error: Optional[str] = None
        self.playback_errors = 0
        self.started_at = time.time()
        self.cache_index = self._load_cache_index()
        self.mpv: Optional[subprocess.Popen] = None
        self.network_enabled = True
        self.force_sync = threading.Event()
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None

    def _load_config(self) -> Dict[str, Any]:
        if self.paths.config.exists():
            try:
                return json.loads(self.paths.config.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        config = {
            "api_base_url": os.environ.get("SOULFRAME_API_URL", "http://localhost:8000"),
            "device_name": "SoulFrame Simulator - Windows",
            "app_version": "simulator-0.1.0",
            "poll_interval_seconds": 5,
            "platform": "simulator_windows",
        }
        self._save_config(config)
        return config

    def _save_config(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.paths.config.write_text(json.dumps(config or self.config, indent=2), encoding="utf-8")

    def _log(self, message: str) -> None:
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        print(line, flush=True)
        with (self.paths.logs / "simulator.log").open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def _tail_logs(self, limit: int = 20) -> List[str]:
        try:
            return (self.paths.logs / "simulator.log").read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
        except OSError:
            return []

    def _load_cache_index(self) -> Dict[str, Any]:
        path = self.paths.cache / "cache_index.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_cache_index(self) -> None:
        (self.paths.cache / "cache_index.json").write_text(json.dumps(self.cache_index, indent=2), encoding="utf-8")

    def start(self) -> None:
        self.thread = threading.Thread(target=self._run, name="soulframe-simulator", daemon=True)
        self.thread.start()

    def shutdown(self) -> None:
        self.stop_event.set()
        self._stop_mpv()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3)

    def toggle_network(self) -> bool:
        self.network_enabled = not self.network_enabled
        self._log(f"Network simulation {'enabled' if self.network_enabled else 'disabled'}")
        return self.network_enabled

    def clear_cache(self) -> None:
        self._stop_mpv()
        for media_file in self.paths.media.glob("*"):
            if media_file.is_file():
                media_file.unlink(missing_ok=True)
        self.cache_index = {}
        self._save_cache_index()
        self._log("Simulator media cache cleared")
        self.force_sync.set()

    def _ensure_registered(self) -> None:
        if self.device_id and self.device_token:
            return
        self._log("Registering isolated Windows simulator device")
        registration = register_device(self.api_base, self.device_name, self.app_version)
        self.device_id = registration["device_id"]
        self.device_token = registration["device_token"]
        self.config["device_id"] = self.device_id
        self.config["device_token"] = self.device_token
        self._save_config()

    def _download_item(self, item: Dict[str, Any]) -> Path:
        media_id = item["media_id"]
        filename = safe_filename(media_id, item.get("original_filename", media_id))
        path = self.paths.media / filename
        cached = self.cache_index.get(media_id)
        if cached and cached.get("checksum") == item.get("checksum") and path.exists() and path.stat().st_size:
            return path
        url = item.get("download_url") or f"{self.api_base.rstrip('/')}/device/media/{media_id}/download"
        self._log(f"Downloading {filename}")
        temporary = path.with_suffix(path.suffix + ".part")
        with requests.get(url, headers=headers(self.device_token, self.device_id), stream=True, timeout=30) as response:
            response.raise_for_status()
            with temporary.open("wb") as output:
                for chunk in response.iter_content(1024 * 256):
                    if chunk:
                        output.write(chunk)
        temporary.replace(path)
        self.cache_index[media_id] = {"checksum": item.get("checksum"), "path": str(path)}
        self._save_cache_index()
        return path

    def _stop_mpv(self) -> None:
        if not self.mpv:
            return
        try:
            self.mpv.terminate()
            self.mpv.wait(timeout=2)
        except Exception:
            try:
                self.mpv.kill()
            except Exception:
                pass
        self.mpv = None

    def _start_playback(self, paths: List[Path]) -> None:
        self._stop_mpv()
        self.on_screen("playback", {"paths": paths})

    def start_embedded_mpv(self, window_id: int, paths: List[Path]) -> None:
        """Called by the Tk thread once the display canvas has a native HWND."""
        self._stop_mpv()
        playlist = self.paths.cache / "playlist.m3u"
        playlist.write_text("#EXTM3U\n" + "\n".join(str(path) for path in paths) + "\n", encoding="utf-8")
        try:
            self.mpv = subprocess.Popen([
                "mpv", f"--wid={window_id}", "--no-osc", "--no-border", "--loop-playlist=inf",
                "--keep-open=yes", f"--playlist={playlist}", f"--log-file={self.paths.logs / 'mpv.log'}",
            ])
            self._log("Started embedded mpv playback")
        except FileNotFoundError:
            self.last_error = "mpv was not found on PATH. Install mpv to play assigned media."
            self.playback_errors += 1
            self.on_screen("error", {"reason": self.last_error})

    def _runtime_payload(self) -> Dict[str, Any]:
        usage = shutil.disk_usage(self.paths.root)
        return {
            "app_version": self.app_version,
            "uptime_seconds": int(time.time() - self.started_at),
            "storage_free_bytes": usage.free,
            "cache_free_bytes": usage.free,
            "current_media_id": self.current_media_id,
            "current_playlist_id": self.current_playlist_id,
            "device_state": self.state.value,
            "playback_errors": self.playback_errors,
            "recent_logs": self._tail_logs(),
            "known_content_revision": self.current_content_revision,
            "known_config_revision": self.current_config_revision,
            "include_commands": True,
            "last_error": self.last_error,
            "health_status": "degraded" if self.last_error else "ok",
        }

    def _process_commands(self, commands: List[Dict[str, Any]]) -> Dict[str, bool]:
        flags = {"refresh": False, "restart": False, "clear": False, "unassign": False}
        for command in commands:
            command_id = command["command_id"]
            kind = command.get("command_type")
            try:
                if kind == "refresh_now": flags["refresh"] = True
                elif kind == "restart_playback": flags["restart"] = True
                elif kind == "clear_cache": flags["clear"] = True
                elif kind == "unassign_content": flags["unassign"] = True
                elif kind == "reboot_client": flags["restart"] = True
                elif kind == "debug_message": self._log(f"Dashboard debug message: {command.get('payload')}")
                ack_command(self.api_base, self.device_token or "", self.device_id or "", command_id, "succeeded", "applied by simulator")
            except Exception as exc:
                self._log(f"Command {kind} failed: {exc!r}")
        return flags

    def _sync_once(self) -> None:
        if not self.network_enabled:
            return
        data = sync_device(self.api_base, self.device_token or "", self.device_id or "", self._runtime_payload())
        self.poll_interval = int(data.get("runtime_config", {}).get("poll_interval_seconds", self.poll_interval))
        self.current_config_revision = data.get("runtime_config", {}).get("config_revision", self.current_config_revision)
        flags = self._process_commands(data.get("pending_commands", []))
        if flags["clear"]: self.clear_cache()
        content = data.get("assigned_content") or {}
        device = data.get("device") or {}
        if not device.get("is_claimed"):
            self.state = DeviceState.UNPAIRED
            self.current_content_revision = "none"
            self.on_screen("pairing", data.get("pairing") or {})
            return
        items = content.get("items") or []
        revision = content.get("content_revision", "none")
        if flags["unassign"] or not items:
            self._stop_mpv()
            self.state = DeviceState.PAIRED_IDLE
            self.current_media_id = None
            self.current_playlist_id = None
            self.current_content_revision = revision
            self.on_screen("idle", {"account": data.get("account_name", "unknown")})
            return
        assignment_type = content.get("assignment_type")
        self.current_playlist_id = content.get("assigned_playlist_id") if assignment_type == "playlist" else None
        self.current_media_id = content.get("assigned_media_id") if assignment_type == "media" else items[0].get("media_id")
        changed = flags["refresh"] or flags["restart"] or revision != self.current_content_revision
        if changed or self.state != DeviceState.PLAYING:
            paths = [self._download_item(item) for item in items]
            self.current_content_revision = revision
            self.last_error = None
            self.state = DeviceState.PLAYING
            self._start_playback(paths)

    def _run(self) -> None:
        self._log(f"SoulFrame simulator starting; API={self.api_base}")
        try:
            self._ensure_registered()
            while not self.stop_event.is_set():
                try:
                    self._sync_once()
                except requests.RequestException as exc:
                    self._log(f"Network error; retaining cached playback: {exc!r}")
                except Exception as exc:
                    self.last_error = repr(exc)
                    self.playback_errors += 1
                    self.state = DeviceState.PLAYBACK_ERROR
                    self.on_screen("error", {"reason": self.last_error})
                self.force_sync.wait(max(3, self.poll_interval))
                self.force_sync.clear()
        finally:
            self._log("SoulFrame simulator stopped")


class SimulatorWindow:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("SoulFrame Device Simulator")
        self.root.geometry("1100x760")
        self.events: queue.Queue[tuple[str, Dict[str, Any]]] = queue.Queue()
        self.paths = SimulatorPaths.default()
        self.agent = SimulatorAgent(self.paths, lambda state, payload: self.events.put((state, payload)))
        self.image_ref: Optional[ImageTk.PhotoImage] = None
        self.playing_paths: List[Path] = []
        self.last_screen: tuple[str, List[str], Optional[str]] = ("SoulFrame Simulator", ["Connecting to backend…"], None)
        self.fullscreen = False
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<F11>", lambda _event: self.toggle_fullscreen())
        self.root.after(100, self._drain_events)

    def _build_ui(self) -> None:
        controls = tk.Frame(self.root, padx=8, pady=8)
        controls.pack(fill=tk.X)
        self.status = tk.StringVar(value="Starting simulator…")
        tk.Label(controls, textvariable=self.status, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(controls, text="Sync now", command=self.agent.force_sync.set).pack(side=tk.RIGHT, padx=3)
        tk.Button(controls, text="Clear cache", command=self.agent.clear_cache).pack(side=tk.RIGHT, padx=3)
        tk.Button(controls, text="Fullscreen", command=self.toggle_fullscreen).pack(side=tk.RIGHT, padx=3)
        self.network_button = tk.Button(controls, text="Disconnect", command=self.toggle_network)
        self.network_button.pack(side=tk.RIGHT, padx=3)
        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_resize)

    def start(self) -> None:
        self.agent.start()
        self.root.mainloop()

    def toggle_network(self) -> None:
        enabled = self.agent.toggle_network()
        self.network_button.configure(text="Disconnect" if enabled else "Reconnect")
        if enabled: self.agent.force_sync.set()

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)

    def _drain_events(self) -> None:
        try:
            while True:
                state, payload = self.events.get_nowait()
                if state == "pairing":
                    self.playing_paths = []
                    self.status.set(f"Waiting for claim — device {self.agent.device_id}")
                    code = payload.get("pairing_code", "----")
                    self._render_message("Ready to pair", ["Scan the QR code or enter this code in SoulFrame:", code], payload.get("claim_url"))
                elif state == "idle":
                    self.playing_paths = []
                    self.status.set(f"Paired — {self.agent.device_id}")
                    self._render_message("SoulFrame connected", [f"Account: {payload.get('account', 'unknown')}", "Waiting for media…"])
                elif state == "playback":
                    self.status.set(f"Playing — {self.agent.device_id}")
                    self.playing_paths = payload["paths"]
                    self.canvas.delete("all")
                    self.agent.start_embedded_mpv(self.canvas.winfo_id(), self.playing_paths)
                elif state == "error":
                    self.playing_paths = []
                    self.status.set("Playback error")
                    self._render_message("Playback error", [payload.get("reason", "Unknown playback error")])
        except queue.Empty:
            pass
        if not self.agent.stop_event.is_set(): self.root.after(100, self._drain_events)

    def _on_resize(self, _event: tk.Event) -> None:
        if not self.playing_paths:
            self._render_message(*self.last_screen)

    def _render_message(self, title: str, lines: List[str], claim_url: Optional[str] = None) -> None:
        self.last_screen = (title, lines, claim_url)
        canvas_width, canvas_height = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        width = min(canvas_width, int(canvas_height * 16 / 9))
        height = int(width * 9 / 16)
        image = Image.new("RGB", (width, height), (10, 10, 10))
        draw = ImageDraw.Draw(image)
        title_font = ImageFont.load_default()
        draw.text((40, 40), title, fill=(245, 245, 245), font=title_font)
        y = 110
        for line in lines:
            draw.text((40, y), line, fill=(120, 200, 255) if line == lines[-1] and title == "Ready to pair" else (235, 235, 235), font=title_font)
            y += 34
        if claim_url:
            try:
                import qrcode  # Optional: installed only for the simulator.
                qr = qrcode.make(claim_url).convert("RGB").resize((220, 220))
                image.paste(qr, (max(20, width - 260), 45))
            except ImportError:
                draw.text((40, y + 18), f"Claim URL: {claim_url}", fill=(120, 200, 255), font=title_font)
        self.image_ref = ImageTk.PhotoImage(image)
        self.canvas.delete("all")
        self.canvas.create_image((canvas_width - width) // 2, (canvas_height - height) // 2, image=self.image_ref, anchor=tk.NW)

    def close(self) -> None:
        self.agent.shutdown()
        self.root.destroy()


def main() -> None:
    if sys.platform != "win32":
        print("The desktop simulator is intended for Windows. Use the Pi agent normally on Raspberry Pi OS.", file=sys.stderr)
    SimulatorWindow().start()


if __name__ == "__main__":
    main()

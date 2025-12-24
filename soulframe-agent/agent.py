#!/usr/bin/env python3
"""
SoulFrame Device Agent
Runs on Linux devices (e.g., Raspberry Pi) to display media from the SoulFrame backend.
"""

import json
import os
import sys
import time
import hashlib
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from PIL import Image, ImageDraw, ImageFont

# Configuration
BASE_DIR = Path("/home/admin/soulframe")
CONFIG_PATH = BASE_DIR / "config" / "device.json"
CACHE_DIR = BASE_DIR / "cache"
MEDIA_DIR = BASE_DIR / "media"
LOG_DIR = BASE_DIR / "logs"
PAIR_SCREEN_PATH = CACHE_DIR / "pair_screen.png"
PLAYLIST_PATH = CACHE_DIR / "playlist.m3u"

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "agent.log"


def log(msg: str) -> None:
    """Log message to console and file"""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_config() -> Dict[str, Any]:
    """Load device configuration"""
    if not CONFIG_PATH.exists():
        log("ERROR: Configuration file not found!")
        log(f"Please create {CONFIG_PATH} with the following structure:")
        log(json.dumps({
            "api_base_url": "http://YOUR_BACKEND_IP:8000",
            "device_token": "YOUR_DEVICE_TOKEN",
            "checkin_interval_seconds": 20
        }, indent=2))
        sys.exit(1)
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def headers(device_token: str) -> Dict[str, str]:
    """Generate request headers with device token"""
    return {"X-Device-Token": device_token}


def safe_filename(media_id: str, original_filename: str) -> str:
    """Generate safe local filename for media"""
    ext = Path(original_filename).suffix.lower()
    if ext not in [".mp4", ".mov", ".webm", ".mkv", ".gif", ".jpg", ".jpeg", ".png", ".webp"]:
        ext = ".mp4"
    return f"{media_id}{ext}"


def sha1_of_obj(obj: Any) -> str:
    """Generate hash of object for change detection"""
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def get_free_bytes(path: str) -> int:
    """Get free disk space in bytes"""
    try:
        st = os.statvfs(path)
        return st.f_bavail * st.f_frsize
    except Exception:
        return 0


def checkin(api_base: str, token: str, app_version: str = "0.1.0") -> Dict[str, Any]:
    """Check in with backend and get current state"""
    url = f"{api_base.rstrip('/')}/device/checkin"
    payload = {
        "app_version": app_version,
        "storage_free_bytes": get_free_bytes(str(MEDIA_DIR)),
    }
    r = requests.post(url, json=payload, headers=headers(token), timeout=10)
    r.raise_for_status()
    return r.json()


def download_media(api_base: str, token: str, media_id: str, original_filename: str) -> Path:
    """Download media file from backend if not cached"""
    local_name = safe_filename(media_id, original_filename)
    local_path = MEDIA_DIR / local_name
    
    # Skip if already downloaded
    if local_path.exists() and local_path.stat().st_size > 0:
        log(f"Media {media_id} already cached: {local_path.name}")
        return local_path

    url = f"{api_base.rstrip('/')}/device/media/{media_id}/download"
    log(f"Downloading media {media_id} -> {local_path.name}")
    
    try:
        with requests.get(url, headers=headers(token), stream=True, timeout=30) as r:
            r.raise_for_status()
            tmp_path = local_path.with_suffix(local_path.suffix + ".part")
            
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
            
            tmp_path.replace(local_path)
            log(f"Downloaded {local_path.name} ({local_path.stat().st_size} bytes)")
    except Exception as e:
        log(f"ERROR downloading {media_id}: {repr(e)}")
        raise

    return local_path


def build_playlist_file(items: List[Dict[str, Any]], manifest: List[Dict[str, Any]], api_base: str, token: str) -> List[Path]:
    """Build M3U playlist file from backend data"""
    # Create manifest lookup
    manifest_by_id = {m["media_id"]: m for m in manifest}
    
    # Sort items by position
    sorted_items = sorted(items, key=lambda x: x.get("position", 0))

    local_paths: List[Path] = []
    for it in sorted_items:
        mid = it["media_id"]
        meta = manifest_by_id.get(mid, {})
        original_filename = meta.get("original_filename", f"{mid}.mp4")
        
        try:
            p = download_media(
                api_base=api_base,
                token=token,
                media_id=mid,
                original_filename=original_filename,
            )
            local_paths.append(p)
        except Exception as e:
            log(f"ERROR: Failed to download {mid}, skipping: {repr(e)}")
            continue

    if not local_paths:
        log("WARNING: No media files available for playlist")
        return local_paths

    # Write M3U playlist
    with open(PLAYLIST_PATH, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for p in local_paths:
            f.write(str(p) + "\n")
    
    log(f"Built playlist with {len(local_paths)} items")
    return local_paths


def generate_pairing_screen(claim_url: str, pairing_code: str) -> None:
    """Generate pairing screen image with QR code and pairing code"""
    W, H = 1920, 1080
    bg = (10, 10, 10)
    fg = (245, 245, 245)
    accent = (120, 200, 255)

    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    # Load fonts
    def load_font(size: int):
        for p in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size=size)
                except Exception:
                    continue
        return ImageFont.load_default()

    font_title = load_font(56)
    font_code = load_font(96)
    font_body = load_font(34)

    # Title
    title = "Pair your SoulFrame"
    draw.text((80, 70), title, fill=fg, font=font_title)

    # Generate QR code if qrencode is available
    qr_png = CACHE_DIR / "qr.png"
    try:
        subprocess.run(
            ["qrencode", "-o", str(qr_png), "-s", "10", claim_url],
            check=True,
            capture_output=True
        )
        
        qr = Image.open(qr_png).convert("RGB")
        qr_size = 520
        qr = qr.resize((qr_size, qr_size), Image.Resampling.NEAREST)
        img.paste(qr, (120, 220))
        
        # Instructions with QR
        draw.text((720, 240), "Scan to claim:", fill=fg, font=font_body)
        draw.text((720, 310), claim_url, fill=accent, font=font_body)
        draw.text((720, 460), "Or enter this code:", fill=fg, font=font_body)
        draw.text((720, 540), pairing_code, fill=fg, font=font_code)
        
    except Exception as e:
        log(f"Could not generate QR code (qrencode not installed?): {repr(e)}")
        # Fallback: just show pairing code large
        draw.text((W // 2 - 300, H // 2 - 150), "Pairing Code:", fill=fg, font=font_body, anchor="mm")
        draw.text((W // 2, H // 2), pairing_code, fill=accent, font=font_code, anchor="mm")
        draw.text((W // 2, H // 2 + 120), claim_url, fill=fg, font=font_body, anchor="mm")

    # Footer
    draw.text((80, 930), "Keep this screen open until paired.", fill=(180, 180, 180), font=font_body)

    img.save(PAIR_SCREEN_PATH)
    log(f"Generated pairing screen: {PAIR_SCREEN_PATH}")


def start_mpv_for_pairing() -> subprocess.Popen:
    """Start MPV to display pairing screen"""
    cmd = [
        "mpv",
        "--fs",
        "--no-osc",
        "--no-border",
        "--no-input-default-bindings",
        "--image-display-duration=inf",
        "--loop=inf",
        str(PAIR_SCREEN_PATH),
    ]
    log("Starting MPV (pairing screen)")
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def start_mpv_for_playlist() -> subprocess.Popen:
    """Start MPV to play playlist"""
    cmd = [
        "mpv",
        "--fs",
        "--no-osc",
        "--no-border",
        "--no-input-default-bindings",
        "--hwdec=auto",
        "--loop-playlist=inf",
        "--playlist",
        str(PLAYLIST_PATH),
        "--log-file",
        str(LOG_DIR / "mpv.log"),
    ]
    log("Starting MPV (playlist)")
    return subprocess.Popen(cmd)


def stop_process(p: Optional[subprocess.Popen]) -> None:
    """Stop a subprocess gracefully"""
    if not p:
        return
    try:
        p.terminate()
        p.wait(timeout=3)
    except Exception:
        try:
            p.kill()
            p.wait(timeout=1)
        except Exception:
            pass


def main():
    """Main agent loop"""
    # Load configuration
    config = load_config()
    api = config["api_base_url"]
    token = config["device_token"]
    interval = int(config.get("checkin_interval_seconds", 20))

    current_mode = None  # "paired" or "unpaired"
    current_hash = None  # detect changes in playlist/manifest/settings
    mpv_proc: Optional[subprocess.Popen] = None

    log("=" * 60)
    log("SoulFrame Device Agent Starting")
    log(f"API: {api}")
    log(f"Checkin interval: {interval}s")
    log("=" * 60)

    while True:
        try:
            # Check in with backend
            resp = checkin(api, token)
            paired = bool(resp.get("paired", False))

            if not paired:
                # UNPAIRED MODE: Show pairing screen
                pairing = resp.get("pairing") or {}
                code = pairing.get("pairing_code", "------")
                claim_url = pairing.get("claim_url", "http://localhost/claim")

                desired_hash = sha1_of_obj({
                    "paired": False,
                    "code": code,
                    "claim_url": claim_url
                })
                
                if current_mode != "unpaired" or current_hash != desired_hash:
                    log("State: UNPAIRED - Showing pairing screen")
                    generate_pairing_screen(claim_url, code)
                    stop_process(mpv_proc)
                    mpv_proc = start_mpv_for_pairing()
                    current_mode = "unpaired"
                    current_hash = desired_hash

            else:
                # PAIRED MODE: Play playlist
                manifest = resp.get("media_manifest") or []
                items = resp.get("playlist_items") or []
                settings = resp.get("settings") or {}
                assigned_playlist_id = resp.get("assigned_playlist_id")

                desired_hash = sha1_of_obj({
                    "paired": True,
                    "assigned_playlist_id": assigned_playlist_id,
                    "settings": settings,
                    "manifest_ids": [m.get("media_id") for m in manifest],
                    "items": items,
                })

                if current_mode != "paired" or current_hash != desired_hash:
                    log(f"State: PAIRED (playlist_id={assigned_playlist_id})")
                    
                    if not items:
                        log("No playlist items assigned - showing placeholder")
                        # Show "waiting for content" screen
                        generate_pairing_screen(" ", "Waiting for playlist...")
                        stop_process(mpv_proc)
                        mpv_proc = start_mpv_for_pairing()
                    else:
                        # Download media and play playlist
                        log(f"Building playlist with {len(items)} items")
                        paths = build_playlist_file(items, manifest, api, token)
                        
                        if paths:
                            stop_process(mpv_proc)
                            mpv_proc = start_mpv_for_playlist()
                        else:
                            log("ERROR: No valid media files, showing error screen")
                            generate_pairing_screen(" ", "Error loading media")
                            stop_process(mpv_proc)
                            mpv_proc = start_mpv_for_pairing()
                    
                    current_mode = "paired"
                    current_hash = desired_hash

        except requests.exceptions.RequestException as e:
            log(f"Network error: {repr(e)}")
        except Exception as e:
            log(f"ERROR in main loop: {repr(e)}")
            import traceback
            log(traceback.format_exc())

        time.sleep(interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Shutting down (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        log(f"FATAL ERROR: {repr(e)}")
        sys.exit(1)
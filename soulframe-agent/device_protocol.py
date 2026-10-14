"""Small, platform-neutral helpers for SoulFrame device API calls.

Both the Raspberry Pi agent and the Windows simulator use this module.  It has
no display, filesystem-layout, or platform-specific imports.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import requests


def headers(token: Optional[str], device_id: Optional[str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if token:
        result["X-Device-Token"] = token
    if device_id:
        result["X-Device-Id"] = device_id
    return result


def register_device(api_base: str, device_name: str, app_version: str) -> Dict[str, Any]:
    response = requests.post(
        f"{api_base.rstrip('/')}/device/register",
        json={"name": device_name, "app_version": app_version},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def sync_device(api_base: str, device_token: str, device_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.post(
        f"{api_base.rstrip('/')}/device/sync",
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
    response = requests.post(
        f"{api_base.rstrip('/')}/device/commands/{command_id}/ack",
        json={"status": status_value, "message": message},
        headers=headers(device_token, device_id),
        timeout=8,
    )
    response.raise_for_status()


def safe_filename(media_id: str, original_filename: str) -> str:
    extension = Path(original_filename).suffix.lower()
    if extension not in {".mp4", ".mov", ".webm", ".mkv", ".gif", ".jpg", ".jpeg", ".png", ".webp"}:
        extension = ".bin"
    return f"{media_id}{extension}"

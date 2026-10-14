import shutil
import subprocess
import sys
import unittest
import uuid
import asyncio
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException

from app.config import settings
from app.routers.media import _asset_token, _require_asset_token, preview_media
from app.services.media_processing import generate_video_thumbnail
from app.utils.storage import get_file_path


class ThumbnailPipelineTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent / ".tmp" / self._testMethodName
        shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True)
        self.original_storage = settings.MEDIA_STORAGE_PATH
        settings.MEDIA_STORAGE_PATH = str(self.root)
        self.media = SimpleNamespace(
            id=uuid.uuid4(), owner_user_id=uuid.uuid4(), playback_storage_key=f"normalized/{uuid.uuid4()}.mp4",
            duration_seconds=4.0, thumbnail_storage_key=None, thumbnail_generated_at=None, thumbnail_error=None,
        )
        source = Path(get_file_path(self.media.playback_storage_key))
        source.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=640x360:d=4", "-pix_fmt", "yuv420p", str(source)], check=True, capture_output=True)

    def tearDown(self):
        settings.MEDIA_STORAGE_PATH = self.original_storage
        shutil.rmtree(self.root, ignore_errors=True)

    def test_generates_stable_modest_jpeg_thumbnail(self):
        generate_video_thumbnail(self.media)
        self.assertEqual(self.media.thumbnail_storage_key, f"thumbnails/{self.media.id}.jpg")
        self.assertTrue(Path(get_file_path(self.media.thumbnail_storage_key)).is_file())

    def test_signed_asset_token_is_bound_to_media_owner_and_kind(self):
        token, _ = _asset_token(self.media, "preview")
        _require_asset_token(self.media, "preview", token)
        with self.assertRaises(HTTPException):
            _require_asset_token(self.media, "thumbnail", token)
        another_media = SimpleNamespace(id=uuid.uuid4(), owner_user_id=self.media.owner_user_id)
        with self.assertRaises(HTTPException):
            _require_asset_token(another_media, "preview", token)

    def test_preview_response_advertises_byte_ranges(self):
        token, _ = _asset_token(self.media, "preview")
        self.media.mime_type = "video/mp4"
        self.media.playback_mime_type = "video/mp4"
        db = type("Db", (), {"query": lambda *_: type("Query", (), {"filter": lambda *_: type("Result", (), {"first": lambda *_: self.media})()})()})()
        response = asyncio.run(preview_media(self.media.id, token, db))
        self.assertEqual(response.headers["accept-ranges"], "bytes")


if __name__ == "__main__":
    unittest.main()

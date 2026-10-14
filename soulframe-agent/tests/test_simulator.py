import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from device_protocol import safe_filename
from simulator import DeviceState, SimulatorAgent, SimulatorPaths


class SimulatorAgentTests(unittest.TestCase):
    def setUp(self):
        temp_root = Path(__file__).resolve().parent / ".tmp"
        temp_root.mkdir(exist_ok=True)
        self.tempdir = temp_root / self._testMethodName
        shutil.rmtree(self.tempdir, ignore_errors=True)
        self.tempdir.mkdir()
        root = self.tempdir
        self.paths = SimulatorPaths(root, root / "device.json", root / "cache", root / "media", root / "logs")
        for path in (self.paths.cache, self.paths.media, self.paths.logs):
            path.mkdir(parents=True)
        self.events = []
        self.agent = SimulatorAgent(self.paths, lambda state, payload: self.events.append((state, payload)))

    def tearDown(self):
        self.agent.shutdown()
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_identity_and_storage_are_isolated(self):
        self.assertEqual(self.agent.device_name, "SoulFrame Simulator - Windows")
        self.assertNotIn("/home/admin/soulframe", str(self.paths.root))
        self.assertTrue(self.paths.config.exists())

    def test_network_toggle_does_not_change_identity(self):
        self.agent.device_id = "simulator-id"
        self.agent.device_token = "simulator-token"
        self.assertFalse(self.agent.toggle_network())
        self.assertEqual(self.agent.device_id, "simulator-id")
        self.assertEqual(self.agent.device_token, "simulator-token")

    def test_direct_media_assignment_updates_playback_state(self):
        self.agent.device_id = "device"
        self.agent.device_token = "token"
        response = {
            "device": {"is_claimed": True},
            "runtime_config": {"poll_interval_seconds": 5, "config_revision": "cfg"},
            "pending_commands": [],
            "assigned_content": {
                "assignment_type": "media",
                "assigned_media_id": "media-1",
                "assigned_playlist_id": None,
                "content_revision": "one",
                "items": [{"media_id": "media-1", "original_filename": "clip.mp4", "checksum": "abc"}],
            },
        }
        with patch("simulator.sync_device", return_value=response), patch.object(self.agent, "_download_item", return_value=self.paths.media / "clip.mp4"):
            self.agent._sync_once()
        self.assertEqual(self.agent.state, DeviceState.PLAYING)
        self.assertEqual(self.agent.current_media_id, "media-1")
        self.assertEqual(self.events[-1][0], "playback")

    def test_playlist_assignment_tracks_playlist_id(self):
        self.agent.device_id = "device"
        self.agent.device_token = "token"
        response = {
            "device": {"is_claimed": True}, "runtime_config": {}, "pending_commands": [],
            "assigned_content": {
                "assignment_type": "playlist", "assigned_media_id": None, "assigned_playlist_id": "playlist-1",
                "content_revision": "one", "items": [{"media_id": "media-1", "original_filename": "clip.mp4"}],
            },
        }
        with patch("simulator.sync_device", return_value=response), patch.object(self.agent, "_download_item", return_value=self.paths.media / "clip.mp4"):
            self.agent._sync_once()
        self.assertEqual(self.agent.current_playlist_id, "playlist-1")

    def test_unclaimed_response_shows_pairing_screen(self):
        self.agent.device_id = "device"
        self.agent.device_token = "token"
        response = {"device": {"is_claimed": False}, "runtime_config": {}, "pending_commands": [], "pairing": {"pairing_code": "ABCDEFGH"}}
        with patch("simulator.sync_device", return_value=response):
            self.agent._sync_once()
        self.assertEqual(self.agent.state, DeviceState.UNPAIRED)
        self.assertEqual(self.events[-1][0], "pairing")

    def test_embedded_mpv_uses_the_simulator_playlist(self):
        clip = self.paths.media / "clip.mp4"
        clip.write_bytes(b"test")
        process = Mock()
        with patch("simulator.subprocess.Popen", return_value=process) as popen:
            self.agent.start_embedded_mpv(4242, [clip])
        command = popen.call_args.args[0]
        self.assertIn("--wid=4242", command)
        self.assertIn("--loop-playlist=inf", command)
        self.assertIn(str(clip), (self.paths.cache / "playlist.m3u").read_text(encoding="utf-8"))

    def test_shutdown_stops_the_playback_process(self):
        process = Mock()
        self.agent.mpv = process
        self.agent.shutdown()
        process.terminate.assert_called_once()

    def test_safe_filenames_are_shared_with_pi_agent(self):
        self.assertEqual(safe_filename("media", "video.mp4"), "media.mp4")
        self.assertEqual(safe_filename("media", "unknown.exe"), "media.bin")

    def test_pi_entrypoint_keeps_its_original_platform_contract(self):
        source = (Path(__file__).resolve().parents[1] / "agent.py").read_text(encoding="utf-8")
        self.assertIn('BASE_DIR = Path("/home/admin/soulframe")', source)
        self.assertIn('"--hwdec=rpi"', source)
        self.assertIn('"--fs"', source)
        self.assertNotIn("import tkinter", source)


if __name__ == "__main__":
    unittest.main()

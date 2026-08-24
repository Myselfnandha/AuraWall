"""
Tests for awall.dynamic_pack
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from PIL import Image

from awall.dynamic_pack import get_pack_frames, select_dynamic_frame


class TestDynamicPack(unittest.TestCase):
    def test_dynamic_pack_selection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p_dir = Path(tmpdir)
            # Create 4 frames
            for i in range(4):
                Image.new("RGB", (100, 100), color="white").save(p_dir / f"frame_{i:02d}.jpg", "JPEG")

            frames = get_pack_frames(p_dir)
            self.assertEqual(len(frames), 4)

            # Noon (12:00 -> 50% progress -> frame 2)
            dt_noon = datetime(2026, 6, 21, 12, 0)
            chosen = select_dynamic_frame(p_dir, dt=dt_noon)
            self.assertEqual(chosen.name, "frame_02.jpg")

            # Morning (06:00 -> 25% progress -> frame 1)
            dt_morning = datetime(2026, 6, 21, 6, 0)
            chosen_m = select_dynamic_frame(p_dir, dt=dt_morning)
            self.assertEqual(chosen_m.name, "frame_01.jpg")


if __name__ == "__main__":
    unittest.main()

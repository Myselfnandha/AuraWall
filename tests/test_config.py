"""
Tests for awall.config
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from awall.config import (
    ALL_TOPICS,
    DEFAULT_CONFIG,
    _deep_merge,
    get_default_config,
    load_config,
    save_config,
)


class TestConfig(unittest.TestCase):
    def test_default_config_structure(self):
        cfg = get_default_config()
        self.assertEqual(cfg["version"], 1)
        self.assertFalse(cfg["paused"])
        self.assertIn("sources", cfg)
        self.assertIn("topics", cfg)
        self.assertIn("schedule", cfg)
        self.assertIn("display", cfg)
        self.assertIn("cache", cfg)
        self.assertEqual(len(cfg["topics"]["enabled"]), len(ALL_TOPICS))

    def test_deep_merge(self):
        target = {"a": 1, "sub": {"x": 10, "y": 20}}
        source = {"a": 2, "sub": {"y": 99, "z": 100}, "new": "val"}
        merged = _deep_merge(target, source)
        self.assertEqual(merged["a"], 2)
        self.assertEqual(merged["sub"]["x"], 10)
        self.assertEqual(merged["sub"]["y"], 99)
        self.assertEqual(merged["sub"]["z"], 100)
        self.assertEqual(merged["new"], "val")

    def test_save_and_load_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            with patch("awall.config.get_config_path", return_value=config_file), \
                 patch("awall.config.get_config_dir", return_value=Path(tmpdir)):
                
                custom_cfg = get_default_config()
                custom_cfg["schedule"]["interval_minutes"] = 42
                custom_cfg["paused"] = True
                save_config(custom_cfg)

                self.assertTrue(config_file.exists())

                loaded = load_config()
                self.assertEqual(loaded["schedule"]["interval_minutes"], 42)
                self.assertTrue(loaded["paused"])


if __name__ == "__main__":
    unittest.main()

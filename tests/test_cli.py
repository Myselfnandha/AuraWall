"""
Tests for awall CLI commands
"""

import unittest
from unittest.mock import MagicMock, patch

from awall.cli import main


class TestCli(unittest.TestCase):
    @patch("awall.cli.cmd_status")
    def test_cli_status(self, mock_cmd):
        mock_cmd.return_value = 0
        code = main(["status"])
        self.assertEqual(code, 0)
        mock_cmd.assert_called_once()

    @patch("awall.cli.cmd_next")
    def test_cli_next(self, mock_cmd):
        mock_cmd.return_value = 0
        code = main(["next", "--topic", "nature"])
        self.assertEqual(code, 0)
        mock_cmd.assert_called_once()

    @patch("awall.cli.cmd_pause")
    def test_cli_pause(self, mock_cmd):
        mock_cmd.return_value = 0
        code = main(["pause"])
        self.assertEqual(code, 0)
        mock_cmd.assert_called_once()

    @patch("awall.cli.cmd_fav")
    def test_cli_fav(self, mock_cmd):
        mock_cmd.return_value = 0
        code = main(["fav"])
        self.assertEqual(code, 0)
        mock_cmd.assert_called_once()

    @patch("awall.cli.cmd_tray")
    def test_cli_tray(self, mock_cmd):
        mock_cmd.return_value = 0
        code = main(["tray"])
        self.assertEqual(code, 0)
        mock_cmd.assert_called_once()


if __name__ == "__main__":
    unittest.main()

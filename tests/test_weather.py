"""
Tests for awall.weather
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from awall.weather import (
    calculate_solar_phase,
    get_live_weather,
    synthesize_dynamic_query,
)


class TestWeather(unittest.TestCase):
    def test_solar_phase_calculation(self):
        # Noon in London (lat 51.5, lon 0.0, 12:00 UTC on day 172 ~ summer solstice)
        dt_noon = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
        phase, elevation = calculate_solar_phase(51.5, 0.0, dt_noon)
        self.assertGreater(elevation, 50.0)
        self.assertEqual(phase, "noon")

        # Night in London (00:00 UTC)
        dt_night = datetime(2026, 6, 21, 0, 0, 0, tzinfo=timezone.utc)
        phase_night, elevation_night = calculate_solar_phase(51.5, 0.0, dt_night)
        self.assertLess(elevation_night, -10.0)
        self.assertEqual(phase_night, "night")

    def test_synthesize_dynamic_query(self):
        q1 = synthesize_dynamic_query("nature", "sunset", "clear")
        self.assertIn("nature", q1)
        self.assertIn("sunset", q1)

        q2 = synthesize_dynamic_query("city", "noon", "rainy")
        self.assertIn("city", q2)
        self.assertIn("rain", q2)

    @patch("requests.get")
    def test_live_weather_mock(self, mock_get):
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {
            "current": {
                "temperature_2m": 25.4,
                "weather_code": 0,
                "is_day": 1,
            }
        }
        mock_get.return_value = mock_res

        wtr = get_live_weather(28.6, 77.2)
        self.assertEqual(wtr["temperature"], 25.4)
        self.assertEqual(wtr["description"], "Clear Sky")


if __name__ == "__main__":
    unittest.main()

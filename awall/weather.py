"""
Solar position, astronomical time-of-day, and live weather module for awall.
Calculates solar elevation, queries Open-Meteo, and generates dynamic search tags.
"""

from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import requests

from awall.cache import get_default_cache_dir

# WMO Weather Code Mapping (Open-Meteo)
WMO_CODE_MAP = {
    0: ("Clear Sky", "clear", "☀️"),
    1: ("Mainly Clear", "clear", "🌤"),
    2: ("Partly Cloudy", "cloudy", "⛅"),
    3: ("Overcast", "overcast", "☁️"),
    45: ("Foggy", "foggy", "🌫"),
    48: ("Depositing Rime Fog", "foggy", "🌫"),
    51: ("Light Drizzle", "rainy", "🌦"),
    53: ("Moderate Drizzle", "rainy", "🌧"),
    55: ("Dense Drizzle", "rainy", "🌧"),
    61: ("Slight Rain", "rainy", "🌧"),
    63: ("Moderate Rain", "rainy", "🌧"),
    65: ("Heavy Rain", "rainy", "🌧"),
    71: ("Slight Snow", "snowy", "🌨"),
    73: ("Moderate Snow", "snowy", "🌨"),
    75: ("Heavy Snow", "snowy", "❄️"),
    77: ("Snow Grains", "snowy", "❄️"),
    80: ("Slight Rain Showers", "rainy", "🌦"),
    81: ("Moderate Rain Showers", "rainy", "🌧"),
    82: ("Violent Rain Showers", "rainy", "⛈"),
    85: ("Slight Snow Showers", "snowy", "🌨"),
    86: ("Heavy Snow Showers", "snowy", "❄️"),
    95: ("Thunderstorm", "thunderstorm", "⚡"),
    96: ("Thunderstorm with Slight Hail", "thunderstorm", "⛈"),
    99: ("Thunderstorm with Heavy Hail", "thunderstorm", "⛈"),
}


def get_location(config: Dict[str, Any]) -> Tuple[float, float, str]:
    """
    Returns (latitude, longitude, city_name).
    Uses manual config if provided, otherwise detects via IP geolocation with local caching.
    """
    dyn_cfg = config.get("dynamic", {})
    if dyn_cfg.get("latitude") and dyn_cfg.get("longitude"):
        return (
            float(dyn_cfg["latitude"]),
            float(dyn_cfg["longitude"]),
            dyn_cfg.get("city", "Custom Location"),
        )

    # Check cache
    cache_file = get_default_cache_dir() / "location_cache.json"
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if time.time() - data.get("timestamp", 0) < 86400:  # 24h cache
                return data["lat"], data["lon"], data.get("city", "Unknown")
        except Exception:
            pass

    # Query IP geolocation
    try:
        res = requests.get("https://ipapi.co/json/", timeout=5)
        if res.status_code == 200:
            data = res.json()
            lat = float(data.get("latitude", 0.0))
            lon = float(data.get("longitude", 0.0))
            city = data.get("city", "Local")
            cache_file.write_text(
                json.dumps({"lat": lat, "lon": lon, "city": city, "timestamp": time.time()}),
                encoding="utf-8",
            )
            return lat, lon, city
    except Exception:
        pass

    # Fallback to ip-api.com
    try:
        res = requests.get("http://ip-api.com/json/", timeout=5)
        if res.status_code == 200:
            data = res.json()
            lat = float(data.get("lat", 0.0))
            lon = float(data.get("lon", 0.0))
            city = data.get("city", "Local")
            cache_file.write_text(
                json.dumps({"lat": lat, "lon": lon, "city": city, "timestamp": time.time()}),
                encoding="utf-8",
            )
            return lat, lon, city
    except Exception:
        pass

    return 20.0, 77.0, "India"  # Default global fallback


def calculate_solar_phase(lat: float, lon: float, dt: Optional[datetime] = None) -> Tuple[str, float]:
    """
    Computes approximate solar elevation angle and returns (solar_phase_name, elevation_degrees).
    Phases: 'night', 'dawn', 'sunrise', 'morning', 'noon', 'afternoon', 'golden_hour', 'sunset', 'dusk'
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    else:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

    # Day of the year
    day_of_year = dt.timetuple().tm_yday
    hour_utc = dt.hour + dt.minute / 60.0 + dt.second / 3600.0

    # Approximate solar declination
    declination = 23.45 * math.sin(math.radians((360 / 365.0) * (day_of_year - 81)))

    # Solar hour angle
    time_offset = (lon * 4.0) / 60.0  # hours from UTC based on longitude
    solar_time = (hour_utc + time_offset) % 24.0
    hour_angle = (solar_time - 12.0) * 15.0

    # Solar elevation
    lat_rad = math.radians(lat)
    dec_rad = math.radians(declination)
    ha_rad = math.radians(hour_angle)

    sin_elevation = math.sin(lat_rad) * math.sin(dec_rad) + math.cos(lat_rad) * math.cos(dec_rad) * math.cos(ha_rad)
    elevation = math.degrees(math.asin(max(-1.0, min(1.0, sin_elevation))))

    is_morning = solar_time < 12.0

    if elevation < -12.0:
        phase = "night"
    elif -12.0 <= elevation < -0.83:
        phase = "dawn" if is_morning else "dusk"
    elif -0.83 <= elevation < 6.0:
        phase = "sunrise" if is_morning else "sunset"
    elif 6.0 <= elevation < 15.0 and not is_morning:
        phase = "golden_hour"
    elif 6.0 <= elevation < 35.0:
        phase = "morning" if is_morning else "afternoon"
    else:
        phase = "noon"

    return phase, elevation


def get_live_weather(lat: float, lon: float) -> Dict[str, Any]:
    """
    Queries Open-Meteo for current temperature, weather code, and condition.
    Caches results locally for 15 minutes.
    """
    cache_file = get_default_cache_dir() / "weather_cache.json"
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if time.time() - data.get("timestamp", 0) < 900:  # 15m
                return data
        except Exception:
            pass

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code,is_day",
        "timezone": "auto",
    }

    try:
        res = requests.get(url, params=params, timeout=6)
        if res.status_code == 200:
            data = res.json()
            curr = data.get("current", {})
            temp_c = curr.get("temperature_2m", 22.0)
            code = int(curr.get("weather_code", 0))
            is_day = bool(curr.get("is_day", 1))

            desc, mood, icon = WMO_CODE_MAP.get(code, ("Clear", "clear", "☀️"))
            result = {
                "temperature": round(temp_c, 1),
                "weather_code": code,
                "description": desc,
                "mood": mood,
                "icon": icon,
                "is_day": is_day,
                "timestamp": time.time(),
            }
            cache_file.write_text(json.dumps(result), encoding="utf-8")
            return result
    except Exception as e:
        print(f"[awall] Weather fetch notice ({e}). Using default climate.")

    return {
        "temperature": 22.0,
        "weather_code": 0,
        "description": "Clear Sky",
        "mood": "clear",
        "icon": "☀️",
        "is_day": True,
        "timestamp": time.time(),
    }


def synthesize_dynamic_query(
    base_topic: str,
    solar_phase: str,
    weather_mood: str,
) -> str:
    """
    Blends the user's category with solar time and weather mood for intelligent dynamic search.
    """
    solar_tags = {
        "night": "night sky starry dark",
        "dawn": "early dawn morning mist twilight",
        "sunrise": "sunrise golden morning landscape",
        "morning": "bright morning sunny clear",
        "noon": "vibrant daylight sun landscape",
        "afternoon": "sunny afternoon scenic",
        "golden_hour": "golden hour sunset glow",
        "sunset": "sunset dramatic clouds evening",
        "dusk": "dusk twilight blue hour city",
    }

    weather_tags = {
        "clear": "clear crisp",
        "cloudy": "cloudy atmospheric",
        "overcast": "overcast moody clouds",
        "rainy": "rainy rain reflections moody",
        "snowy": "snow winter frost white",
        "foggy": "foggy misty mysterious",
        "thunderstorm": "thunderstorm lightning dramatic",
    }

    s_tag = solar_tags.get(solar_phase, "")
    w_tag = weather_tags.get(weather_mood, "")

    clean_topic = base_topic.replace("_", " ")

    # Build harmonious search keywords
    if weather_mood in ("rainy", "snowy", "thunderstorm", "foggy"):
        return f"{clean_topic} {w_tag}"
    else:
        return f"{clean_topic} {s_tag}"

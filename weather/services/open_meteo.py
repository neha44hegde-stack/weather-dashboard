"""
Thin client for the Open-Meteo API (free, no API key required).

Docs: https://open-meteo.com/en/docs
"""

import requests
from django.conf import settings
from django.core.cache import cache


class OpenMeteoClient:
    def __init__(self, timeout=10):
        self.timeout = timeout
        self.base_url = settings.OPEN_METEO_BASE_URL
        self.geocoding_url = settings.OPEN_METEO_GEOCODING_URL

    # --- Geocoding -------------------------------------------------

    def geocode_city(self, city_name, count=5):
        """City name -> list of matching locations with lat/lon."""
        cache_key = f"geocode:{city_name.lower()}:{count}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        resp = requests.get(
            f"{self.geocoding_url}/search",
            params={"name": city_name, "count": count, "language": "en", "format": "json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        cache.set(cache_key, results, settings.WEATHER_CACHE_TTL_SECONDS)
        return results

    def reverse_geocode(self, latitude, longitude):
        """
        Coordinates -> nearest real place name, using geopy's Nominatim
        (OpenStreetMap, free, no API key). Falls back to None if the
        lookup fails for any reason (network issue, rate limit, no match)
        so callers can gracefully fall back to showing coordinates.
        """
        cache_key = f"reverse_geocode:{round(latitude, 4)}:{round(longitude, 4)}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached if cached != "" else None

        try:
            from geopy.geocoders import Nominatim

            geolocator = Nominatim(user_agent="weather_dashboard_app", timeout=self.timeout)
            location = geolocator.reverse((latitude, longitude), language="en", exactly_one=True)
            if location is None:
                cache.set(cache_key, "", settings.WEATHER_CACHE_TTL_SECONDS)
                return None

            address = location.raw.get("address", {})
            name = (
                address.get("village")
                or address.get("town")
                or address.get("city")
                or address.get("suburb")
                or address.get("county")
                or location.address.split(",")[0]
            )
            result = {"name": name, "full_address": location.address}
            cache.set(cache_key, result, settings.WEATHER_CACHE_TTL_SECONDS)
            return result
        except Exception:
            # Any failure here (network, rate limit, geopy not installed
            # correctly, etc.) should never break the page — just skip it.
            cache.set(cache_key, "", settings.WEATHER_CACHE_TTL_SECONDS)
            return None

    # --- Weather -------------------------------------------------

    def get_current_weather(self, latitude, longitude):
        cache_key = f"current:{latitude}:{longitude}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        resp = requests.get(
            f"{self.base_url}/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "apparent_temperature",
                    "precipitation",
                    "weather_code",
                    "wind_speed_10m",
                    "uv_index",
                ],
                "timezone": "auto",
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        cache.set(cache_key, data, settings.WEATHER_CACHE_TTL_SECONDS)
        return data

    def get_forecast(self, latitude, longitude, days=7):
        cache_key = f"forecast:{latitude}:{longitude}:{days}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        resp = requests.get(
            f"{self.base_url}/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "daily": [
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "precipitation_probability_max",
                    "weather_code",
                    "uv_index_max",
                    "sunrise",
                    "sunset",
                ],
                "forecast_days": days,
                "timezone": "auto",
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        cache.set(cache_key, data, settings.WEATHER_CACHE_TTL_SECONDS)
        return data

    def get_air_quality(self, latitude, longitude):
        cache_key = f"aqi:{latitude}:{longitude}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        resp = requests.get(
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": ["us_aqi", "pm2_5", "pm10", "ozone"],
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        cache.set(cache_key, data, settings.WEATHER_CACHE_TTL_SECONDS)
        return data
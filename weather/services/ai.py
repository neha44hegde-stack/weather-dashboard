"""
AI-powered features: weather summaries, clothing/travel/farming/activity
recommendations. Uses the Anthropic API (Claude) with one prompt template
per feature so callers just pass in weather data and get back plain text.
"""

import json

import requests
from django.conf import settings
from django.core.cache import cache

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-5"  # swap for a smaller model if you want lower latency/cost


class AIWeatherAssistant:
    def __init__(self, timeout=20):
        self.timeout = timeout
        self.api_key = settings.ANTHROPIC_API_KEY

    def _call(self, prompt, max_tokens=300):
        if not self.api_key:
            return None  # feature silently disabled if no key is configured

        try:
            resp = requests.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": MODEL,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return "".join(
                block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
            ).strip()
        except requests.RequestException:
            # Bad/missing/expired key, rate limit, or network issue: degrade
            # gracefully rather than breaking the whole page.
            return None

    def _weather_context(self, current, forecast):
        """Boil the raw API payloads down to a compact summary the model can reason over."""
        cur = current.get("current", {})
        today = {}
        if forecast.get("daily", {}).get("time"):
            today = {
                "max_c": forecast["daily"]["temperature_2m_max"][0],
                "min_c": forecast["daily"]["temperature_2m_min"][0],
                "rain_chance_pct": forecast["daily"]["precipitation_probability_max"][0],
                "uv_max": forecast["daily"]["uv_index_max"][0],
            }
        return {
            "temperature_c": cur.get("temperature_2m"),
            "feels_like_c": cur.get("apparent_temperature"),
            "humidity_pct": cur.get("relative_humidity_2m"),
            "wind_kmh": cur.get("wind_speed_10m"),
            "precipitation_mm": cur.get("precipitation"),
            "uv_index": cur.get("uv_index"),
            "today_forecast": today,
        }

    def _cached_or_call(self, cache_key, prompt, max_tokens=300):
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        result = self._call(prompt, max_tokens=max_tokens)
        if result:
            cache.set(cache_key, result, settings.WEATHER_CACHE_TTL_SECONDS)
        return result

    def summary(self, city_name, current, forecast):
        ctx = self._weather_context(current, forecast)
        prompt = (
            f"Weather data for {city_name}: {json.dumps(ctx)}. "
            "Write a friendly 2-sentence plain-language weather summary for a "
            "dashboard. No headers, no markdown, no preamble."
        )
        return self._cached_or_call(f"ai:summary:{city_name}:{ctx.get('temperature_c')}", prompt)

    def clothing_recommendation(self, city_name, current, forecast):
        ctx = self._weather_context(current, forecast)
        prompt = (
            f"Weather data for {city_name}: {json.dumps(ctx)}. "
            "In 1-2 sentences, recommend what to wear today. No preamble."
        )
        return self._cached_or_call(f"ai:clothing:{city_name}:{ctx.get('temperature_c')}", prompt)

    def travel_suggestion(self, city_name, current, forecast):
        ctx = self._weather_context(current, forecast)
        prompt = (
            f"Weather data for {city_name}: {json.dumps(ctx)}. "
            "In 1-2 sentences, suggest whether today is good for outdoor "
            "travel/sightseeing and why. No preamble."
        )
        return self._cached_or_call(f"ai:travel:{city_name}:{ctx.get('temperature_c')}", prompt)

    def farming_recommendation(self, city_name, current, forecast):
        ctx = self._weather_context(current, forecast)
        prompt = (
            f"Weather data for {city_name}: {json.dumps(ctx)}. "
            "In 1-2 sentences, give a practical recommendation for farmers "
            "(irrigation, spraying, harvesting) based on today's conditions. "
            "No preamble."
        )
        return self._cached_or_call(f"ai:farming:{city_name}:{ctx.get('temperature_c')}", prompt)

    def activity_recommendation(self, city_name, current, forecast):
        ctx = self._weather_context(current, forecast)
        prompt = (
            f"Weather data for {city_name}: {json.dumps(ctx)}. "
            "In 1-2 sentences, say whether today is good for outdoor activities "
            "like jogging or cricket, and suggest a good time window if not now. "
            "No preamble."
        )
        return self._cached_or_call(f"ai:activity:{city_name}:{ctx.get('temperature_c')}", prompt)
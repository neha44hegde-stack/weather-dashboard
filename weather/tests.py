from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import FavoriteCity
from .views import (
    clothing_advice,
    comfort_score,
    crop_advice,
    food_advice,
    storm_alert,
    sunscreen_advice,
    weather_code_description,
)

# Sample API responses used to mock OpenMeteoClient, so tests don't depend
# on network access or the real Open-Meteo service being up.
FAKE_CURRENT_WEATHER = {
    "current": {
        "temperature_2m": 30.9,
        "apparent_temperature": 33.0,
        "relative_humidity_2m": 45,
        "wind_speed_10m": 16.6,
        "uv_index": 8.4,
        "weather_code": 1,
        "precipitation": 0,
    }
}

FAKE_FORECAST = {
    "daily": {
        "time": ["2026-07-12", "2026-07-13"],
        "temperature_2m_max": [31.9, 31.8],
        "temperature_2m_min": [20.6, 19.6],
        "precipitation_probability_max": [4, 6],
        "weather_code": [1, 2],
        "uv_index_max": [8, 7],
    }
}

FAKE_AIR_QUALITY = {"current": {"us_aqi": 51, "pm2_5": 12.6}}


class RuleBasedAdviceTests(TestCase):
    """These functions are pure logic (no API/network calls), so they're
    tested directly and exhaustively for each branch."""

    def test_sunscreen_advice_ranges(self):
        self.assertIsNone(sunscreen_advice(None))
        self.assertIn("Low UV", sunscreen_advice(1))
        self.assertIn("Moderate UV", sunscreen_advice(4))
        self.assertIn("High UV", sunscreen_advice(7))
        self.assertIn("Very high UV", sunscreen_advice(10))
        self.assertIn("Extreme UV", sunscreen_advice(12))

    def test_clothing_advice_hot_with_rain(self):
        tip = clothing_advice(36, 60, 10)
        self.assertIn("Very hot", tip)
        self.assertIn("umbrella", tip)

    def test_clothing_advice_cold(self):
        tip = clothing_advice(2, 0, 5)
        self.assertIn("Cold", tip)

    def test_crop_advice_high_rain_and_bad_aqi(self):
        tip = crop_advice(70, 20, 250)
        self.assertIn("irrigation", tip)
        self.assertIn("Poor air quality", tip)

    def test_food_advice_hot(self):
        tip = food_advice(36, 50)
        self.assertIn("hydrating foods", tip)

    def test_comfort_score_ideal_conditions(self):
        result = comfort_score(18, 40, 5, 2, 20)
        self.assertEqual(result["score"], 10)
        self.assertIn("Great", result["label"])

    def test_comfort_score_penalizes_bad_air_quality(self):
        result = comfort_score(30, 50, 10, 5, 500)
        self.assertLessEqual(result["score"], 6)

    def test_storm_alert_active_thunderstorm(self):
        alert = storm_alert(95, [95, 1, 2])
        self.assertEqual(alert["level"], "active")

    def test_storm_alert_upcoming_thunderstorm(self):
        alert = storm_alert(1, [1, 96, 3])
        self.assertEqual(alert["level"], "upcoming")

    def test_storm_alert_none_when_clear(self):
        self.assertIsNone(storm_alert(1, [1, 2, 3]))

    def test_weather_code_description_known_and_unknown(self):
        self.assertEqual(weather_code_description(0), "Clear sky")
        self.assertIn("Unknown", weather_code_description(9999))


class AuthenticationTests(TestCase):
    def test_dashboard_redirects_when_logged_out(self):
        response = self.client.get(reverse("weather:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_loads_when_logged_in(self):
        User.objects.create_user(username="tester", password="testpass123")
        self.client.login(username="tester", password="testpass123")
        response = self.client.get(reverse("weather:dashboard"))
        self.assertEqual(response.status_code, 200)


class FavoriteCityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="testpass123")
        self.client.login(username="tester", password="testpass123")

    def test_add_and_remove_favorite(self):
        response = self.client.post(
            reverse("weather:add_favorite"),
            {"name": "Bengaluru", "country": "India", "latitude": 12.97, "longitude": 77.59},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FavoriteCity.objects.filter(user=self.user).count(), 1)

        city = FavoriteCity.objects.get(user=self.user)
        response = self.client.post(reverse("weather:remove_favorite", args=[city.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FavoriteCity.objects.filter(user=self.user).count(), 0)

    def test_cannot_remove_another_users_favorite(self):
        other_user = User.objects.create_user(username="other", password="testpass123")
        other_city = FavoriteCity.objects.create(
            user=other_user, name="Delhi", latitude=28.65, longitude=77.23
        )
        response = self.client.post(reverse("weather:remove_favorite", args=[other_city.pk]))
        self.assertEqual(response.status_code, 404)


@patch("weather.api.client")
class WeatherAPITests(TestCase):
    """Mocks the Open-Meteo client so these tests run offline/deterministically."""

    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="testpass123")
        self.client.login(username="tester", password="testpass123")

    def test_api_weather_detail_requires_login(self, mock_client):
        self.client.logout()
        response = self.client.get(reverse("weather:api_weather_detail", args=[12.97, 77.59]))
        self.assertEqual(response.status_code, 403)

    def test_api_weather_detail_returns_expected_fields(self, mock_client):
        mock_client.get_current_weather.return_value = FAKE_CURRENT_WEATHER
        mock_client.get_forecast.return_value = FAKE_FORECAST
        mock_client.get_air_quality.return_value = FAKE_AIR_QUALITY

        response = self.client.get(reverse("weather:api_weather_detail", args=[12.97, 77.59]))
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["current"]["temperature_c"], 30.9)
        self.assertEqual(data["air_quality"]["us_aqi"], 51)
        self.assertEqual(len(data["forecast_7day"]), 2)
        self.assertIn("sunscreen", data["advice"])
        self.assertIn("score", data["comfort_score"])

    def test_api_favorites_returns_users_cities(self, mock_client):
        FavoriteCity.objects.create(user=self.user, name="Bengaluru", latitude=12.97, longitude=77.59)
        response = self.client.get(reverse("weather:api_favorites"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["favorites"][0]["name"], "Bengaluru")

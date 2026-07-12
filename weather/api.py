"""
REST API for the weather dashboard. Same underlying data as the HTML views,
but returned as JSON so other apps/services (or Thunder Client, or a future
mobile app) can consume it directly.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .services.ai import AIWeatherAssistant
from .services.open_meteo import OpenMeteoClient
from .views import comfort_score, crop_advice, clothing_advice, food_advice, storm_alert, sunscreen_advice

client = OpenMeteoClient()
ai_assistant = AIWeatherAssistant()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_weather_detail(request, lat, lon):
    """
    GET /api/weather/<lat>/<lon>/

    Returns current conditions, forecast, air quality, and all rule-based
    advice (sunscreen, clothing, crop, food, comfort score, storm alert)
    for the given coordinates, as JSON.
    """
    current = client.get_current_weather(lat, lon)
    forecast = client.get_forecast(lat, lon)
    air_quality = client.get_air_quality(lat, lon)

    cur = current.get("current", {})
    daily = forecast.get("daily", {})

    data = {
        "coordinates": {"latitude": lat, "longitude": lon},
        "current": {
            "temperature_c": cur.get("temperature_2m"),
            "feels_like_c": cur.get("apparent_temperature"),
            "humidity_pct": cur.get("relative_humidity_2m"),
            "wind_kmh": cur.get("wind_speed_10m"),
            "uv_index": cur.get("uv_index"),
            "weather_code": cur.get("weather_code"),
        },
        "air_quality": {
            "us_aqi": air_quality.get("current", {}).get("us_aqi"),
            "pm2_5": air_quality.get("current", {}).get("pm2_5"),
        },
        "forecast_7day": [
            {
                "date": daily.get("time", [])[i],
                "max_c": daily.get("temperature_2m_max", [])[i],
                "min_c": daily.get("temperature_2m_min", [])[i],
                "rain_chance_pct": daily.get("precipitation_probability_max", [])[i],
            }
            for i in range(len(daily.get("time", [])))
        ],
        "advice": {
            "sunscreen": sunscreen_advice(cur.get("uv_index")),
            "clothing": clothing_advice(
                cur.get("temperature_2m"),
                daily.get("precipitation_probability_max", [None])[0],
                cur.get("wind_speed_10m"),
            ),
            "crop": crop_advice(
                daily.get("precipitation_probability_max", [None])[0],
                cur.get("temperature_2m"),
                air_quality.get("current", {}).get("us_aqi"),
            ),
            "food": food_advice(cur.get("temperature_2m"), cur.get("relative_humidity_2m")),
        },
        "comfort_score": comfort_score(
            cur.get("temperature_2m"),
            cur.get("relative_humidity_2m"),
            cur.get("wind_speed_10m"),
            cur.get("uv_index"),
            air_quality.get("current", {}).get("us_aqi"),
        ),
        "storm_alert": storm_alert(cur.get("weather_code"), daily.get("weather_code", [])),
    }
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_favorites(request):
    """
    GET /api/favorites/

    Returns the logged-in user's saved favorite cities as JSON.
    """
    favorites = request.user.favorite_cities.all()
    data = [
        {
            "id": city.id,
            "name": city.name,
            "country": city.country,
            "latitude": city.latitude,
            "longitude": city.longitude,
        }
        for city in favorites
    ]
    return Response({"count": len(data), "favorites": data})

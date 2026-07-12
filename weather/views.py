from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .exports import excel_response, pdf_response
from .models import FavoriteCity, SearchHistory
from .services.ai import AIWeatherAssistant
from .services.open_meteo import OpenMeteoClient

client = OpenMeteoClient()
ai_assistant = AIWeatherAssistant()


def sunscreen_advice(uv_index):
    """Rule-based sunscreen guidance from UV index. No API key needed."""
    if uv_index is None:
        return None
    if uv_index < 3:
        return "Low UV — no sunscreen needed for most skin types."
    if uv_index < 6:
        return "Moderate UV — wear SPF 30+ and a hat if outside for long."
    if uv_index < 8:
        return "High UV — SPF 30+ required, seek shade during midday hours."
    if uv_index < 11:
        return "Very high UV — SPF 50+, minimize sun exposure 10am–4pm."
    return "Extreme UV — SPF 50+, avoid sun exposure as much as possible."


def clothing_advice(temp_c, rain_chance_pct, wind_kmh):
    """Rule-based clothing suggestion. No API key needed."""
    if temp_c is None:
        return None
    if temp_c >= 35:
        tip = "Very hot — wear light, loose, breathable fabrics (cotton/linen), light colors."
    elif temp_c >= 28:
        tip = "Warm — light clothing, short sleeves are comfortable."
    elif temp_c >= 18:
        tip = "Mild — a light jacket or long sleeves should be comfortable."
    elif temp_c >= 8:
        tip = "Cool — wear a warm jacket or sweater, layer up."
    else:
        tip = "Cold — heavy coat, gloves, and layers recommended."

    if rain_chance_pct and rain_chance_pct >= 40:
        tip += " High rain chance — carry an umbrella or raincoat."
    if wind_kmh and wind_kmh >= 30:
        tip += " Windy conditions — a windbreaker helps."
    return tip


def crop_advice(rain_chance_pct, temp_c, us_aqi):
    """Rule-based farming/crop guidance. No API key needed."""
    tips = []
    if rain_chance_pct is not None:
        if rain_chance_pct >= 60:
            tips.append("High rain chance — hold off on irrigation and avoid spraying pesticides today.")
        elif rain_chance_pct <= 15:
            tips.append("Low rain chance — a good day for irrigation if soil is dry.")
    if temp_c is not None and temp_c >= 35:
        tips.append("High heat — water early morning or evening to reduce evaporation loss.")
    if us_aqi is not None and us_aqi >= 200:
        tips.append("Poor air quality — avoid unnecessary outdoor field work if possible.")
    return " ".join(tips) if tips else "Conditions look normal — proceed with regular farm activities."


def food_advice(temp_c, humidity_pct):
    """Rule-based food/hydration tip. No API key needed."""
    if temp_c is None:
        return None
    if temp_c >= 35:
        return "Very hot — drink extra water, favor light meals, fruits, and hydrating foods; avoid heavy/oily food."
    if temp_c >= 28 and humidity_pct and humidity_pct >= 60:
        return "Hot and humid — stay hydrated, eat light, avoid excess caffeine/alcohol."
    if temp_c <= 10:
        return "Cold — warm soups, hot beverages, and hearty meals are a good idea today."
    return "Comfortable conditions — no special food precautions needed."


# WMO weather codes used by Open-Meteo. Reference: https://open-meteo.com/en/docs
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

# Codes that indicate active or imminent thunderstorm activity.
THUNDERSTORM_CODES = {95, 96, 99}


def weather_code_description(code):
    """Human-readable label for an Open-Meteo/WMO weather code."""
    if code is None:
        return None
    return WMO_CODES.get(code, f"Unknown conditions (code {code})")


def storm_alert(current_code, forecast_codes):
    """
    Rule-based thunderstorm/severe weather alert using WMO weather codes
    already returned by Open-Meteo. No extra API key needed.

    Checks the current condition first, then scans the next few days of
    the forecast for upcoming storm risk.
    """
    if current_code in THUNDERSTORM_CODES:
        return {
            "level": "active",
            "message": f"⛈️ Active thunderstorm right now ({weather_code_description(current_code)}). Avoid open areas and unplug sensitive electronics.",
        }

    if forecast_codes:
        for i, code in enumerate(forecast_codes[:3]):  # look at next 3 days
            if code in THUNDERSTORM_CODES:
                when = "today" if i == 0 else ("tomorrow" if i == 1 else f"in {i} days")
                return {
                    "level": "upcoming",
                    "message": f"⚡ Thunderstorms expected {when} ({weather_code_description(code)}). Plan outdoor activities accordingly.",
                }

    return None


def comfort_score(temp_c, humidity_pct, wind_kmh, uv_index, us_aqi):
    """
    Rule-based 'comfort score' out of 10, combining temperature, humidity,
    wind, UV, and air quality into one number for outdoor activity (e.g.
    running, walking, cycling). No API key needed.

    Scoring approach: start at 10 and subtract penalties for each factor
    that's outside a comfortable range. This is a simple, transparent
    heuristic, not a scientific index — easy to explain and easy to tune.
    """
    if temp_c is None:
        return None

    score = 10.0

    # Temperature: ideal ~15-22C for outdoor activity, penalize further away
    if temp_c < 5 or temp_c > 38:
        score -= 4
    elif temp_c < 10 or temp_c > 33:
        score -= 2.5
    elif temp_c < 15 or temp_c > 28:
        score -= 1

    # Humidity: above 70% makes heat feel worse and activity harder
    if humidity_pct is not None:
        if humidity_pct >= 85:
            score -= 2
        elif humidity_pct >= 70:
            score -= 1

    # Wind: very strong wind is unpleasant; a light breeze is fine/neutral
    if wind_kmh is not None and wind_kmh >= 35:
        score -= 1.5

    # UV: high UV makes prolonged outdoor activity riskier
    if uv_index is not None:
        if uv_index >= 9:
            score -= 1.5
        elif uv_index >= 6:
            score -= 0.75

    # Air quality: poor AQI is a significant health factor for outdoor exertion
    if us_aqi is not None:
        if us_aqi >= 150:
            score -= 3
        elif us_aqi >= 100:
            score -= 1.5
        elif us_aqi >= 50:
            score -= 0.5

    score = max(0, min(10, round(score, 1)))

    if score >= 8:
        label = "Great day to be outside"
    elif score >= 6:
        label = "Decent — fine for most outdoor activity"
    elif score >= 4:
        label = "Okay, but take precautions"
    else:
        label = "Not ideal — consider indoor alternatives"

    return {"score": score, "label": label}


@login_required
def dashboard(request):
    favorites = request.user.favorite_cities.all()
    weather_by_city = {}
    storm_by_city = {}
    for city in favorites:
        weather_by_city[city.id] = client.get_current_weather(city.latitude, city.longitude)
        code = weather_by_city[city.id].get("current", {}).get("weather_code")
        if code in THUNDERSTORM_CODES:
            storm_by_city[city.id] = "⛈️ Thunderstorm right now"

    return render(
        request,
        "weather/dashboard.html",
        {"favorites": favorites, "weather_by_city": weather_by_city, "storm_by_city": storm_by_city},
    )


@login_required
def search_city(request):
    query = request.GET.get("q", "").strip()
    results = client.geocode_city(query) if query else []

    if query:
        # Log to search history using the first geocoded match, if any.
        if results:
            top = results[0]
            SearchHistory.objects.create(
                user=request.user,
                query=query,
                latitude=top["latitude"],
                longitude=top["longitude"],
            )

    return render(request, "weather/search_results.html", {"query": query, "results": results})


def _city_display_name(request, lat, lon):
    """Best-effort city label for a coordinate pair: checks favorites and
    search history first (fast, no network call), then falls back to
    real reverse geocoding (geopy/Nominatim), then finally coordinates."""
    match = request.user.favorite_cities.filter(latitude=lat, longitude=lon).first()
    if match:
        return match.name
    match = request.user.search_history.filter(latitude=lat, longitude=lon).first()
    if match:
        return match.query

    reverse = client.reverse_geocode(lat, lon)
    if reverse and reverse.get("name"):
        return reverse["name"]

    return f"{lat}, {lon}"


@login_required
def city_detail(request, lat, lon):
    current = client.get_current_weather(lat, lon)
    forecast = client.get_forecast(lat, lon)
    air_quality = client.get_air_quality(lat, lon)
    city_name = _city_display_name(request, lat, lon)

    ai_insights = {
        "summary": ai_assistant.summary(city_name, current, forecast),
        "clothing": ai_assistant.clothing_recommendation(city_name, current, forecast),
        "travel": ai_assistant.travel_suggestion(city_name, current, forecast),
        "farming": ai_assistant.farming_recommendation(city_name, current, forecast),
        "activity": ai_assistant.activity_recommendation(city_name, current, forecast),
    }
    sunscreen_tip = sunscreen_advice(current.get("current", {}).get("uv_index"))
    clothing_tip = clothing_advice(
        current.get("current", {}).get("temperature_2m"),
        forecast.get("daily", {}).get("precipitation_probability_max", [None])[0],
        current.get("current", {}).get("wind_speed_10m"),
    )
    crop_tip = crop_advice(
        forecast.get("daily", {}).get("precipitation_probability_max", [None])[0],
        current.get("current", {}).get("temperature_2m"),
        air_quality.get("current", {}).get("us_aqi"),
    )
    food_tip = food_advice(
        current.get("current", {}).get("temperature_2m"),
        current.get("current", {}).get("relative_humidity_2m"),
    )
    comfort = comfort_score(
        current.get("current", {}).get("temperature_2m"),
        current.get("current", {}).get("relative_humidity_2m"),
        current.get("current", {}).get("wind_speed_10m"),
        current.get("current", {}).get("uv_index"),
        air_quality.get("current", {}).get("us_aqi"),
    )
    storm = storm_alert(
        current.get("current", {}).get("weather_code"),
        forecast.get("daily", {}).get("weather_code", []),
    )
    condition = weather_code_description(current.get("current", {}).get("weather_code"))

    return render(
        request,
        "weather/city_detail.html",
        {
            "latitude": lat,
            "longitude": lon,
            "city_name": city_name,
            "current": current,
            "forecast": forecast,
            "air_quality": air_quality,
            "ai_insights": ai_insights,
            "sunscreen_tip": sunscreen_tip,
            "clothing_tip": clothing_tip,
            "crop_tip": crop_tip,
            "food_tip": food_tip,
            "comfort": comfort,
            "storm": storm,
            "condition": condition,
        },
    )


@login_required
def export_pdf(request, lat, lon):
    current = client.get_current_weather(lat, lon)
    forecast = client.get_forecast(lat, lon)
    city_name = _city_display_name(request, lat, lon)
    return pdf_response(city_name, current, forecast)


@login_required
def export_excel(request, lat, lon):
    current = client.get_current_weather(lat, lon)
    forecast = client.get_forecast(lat, lon)
    city_name = _city_display_name(request, lat, lon)
    return excel_response(city_name, current, forecast)


@login_required
def add_favorite(request):
    if request.method == "POST":
        FavoriteCity.objects.get_or_create(
            user=request.user,
            latitude=request.POST["latitude"],
            longitude=request.POST["longitude"],
            defaults={
                "name": request.POST.get("name", "Unknown"),
                "country": request.POST.get("country", ""),
            },
        )
    return redirect("weather:dashboard")


@login_required
def remove_favorite(request, pk):
    city = get_object_or_404(FavoriteCity, pk=pk, user=request.user)
    city.delete()
    return redirect("weather:dashboard")


@login_required
def history(request):
    entries = request.user.search_history.all()[:50]
    return render(request, "weather/history.html", {"entries": entries})

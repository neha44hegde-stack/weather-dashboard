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


@login_required
def dashboard(request):
    favorites = request.user.favorite_cities.all()
    weather_by_city = {}
    for city in favorites:
        weather_by_city[city.id] = client.get_current_weather(city.latitude, city.longitude)

    return render(
        request,
        "weather/dashboard.html",
        {"favorites": favorites, "weather_by_city": weather_by_city},
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
    """Best-effort city label for a coordinate pair, using a matching
    favorite/history entry if one exists, else falling back to coordinates."""
    match = request.user.favorite_cities.filter(latitude=lat, longitude=lon).first()
    if match:
        return match.name
    match = request.user.search_history.filter(latitude=lat, longitude=lon).first()
    if match:
        return match.query
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

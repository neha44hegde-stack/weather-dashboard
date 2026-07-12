"""Celery background tasks: scheduled weather refresh + alert emails."""

from celery import shared_task
from django.core.cache import cache
from django.core.mail import send_mail

from .models import FavoriteCity, WeatherAlertSubscription
from .services.open_meteo import OpenMeteoClient

client = OpenMeteoClient()


@shared_task
def refresh_favorite_city_weather():
    """Periodic task: re-fetch weather for all favorited cities to keep
    the cache warm ahead of user requests."""
    for city in FavoriteCity.objects.all().distinct():
        client.get_current_weather(city.latitude, city.longitude)


@shared_task
def check_weather_alerts():
    """Periodic task: check active subscriptions and email users if their
    subscribed condition (rain/storm/etc.) is currently forecast."""
    subs = WeatherAlertSubscription.objects.filter(is_active=True).select_related("user", "city")
    for sub in subs:
        current = client.get_current_weather(sub.city.latitude, sub.city.longitude)
        precipitation = current.get("current", {}).get("precipitation", 0)

        triggered = precipitation and precipitation > 0
        if triggered and sub.user.email:
            send_mail(
                subject=f"Weather alert for {sub.city.name}",
                message=f"Precipitation of {precipitation}mm detected in {sub.city.name}.",
                from_email=None,
                recipient_list=[sub.user.email],
                fail_silently=True,
            )

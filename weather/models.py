from django.conf import settings
from django.db import models


class FavoriteCity(models.Model):
    """A city a user has saved for quick access on their dashboard."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_cities"
    )
    name = models.CharField(max_length=120)
    country = models.CharField(max_length=120, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "latitude", "longitude")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class SearchHistory(models.Model):
    """Log of cities a user has looked up, for the search-history feature."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="search_history"
    )
    query = models.CharField(max_length=120)
    latitude = models.FloatField()
    longitude = models.FloatField()
    searched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-searched_at"]
        verbose_name_plural = "Search history"

    def __str__(self):
        return f"{self.query} @ {self.searched_at:%Y-%m-%d %H:%M}"


class WeatherAlertSubscription(models.Model):
    """Tracks which cities a user wants email/push alerts for (rain, storms, etc.)."""

    ALERT_TYPES = [
        ("rain", "Rain"),
        ("storm", "Storm"),
        ("extreme_heat", "Extreme heat"),
        ("extreme_cold", "Extreme cold"),
        ("any", "Any severe alert"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alert_subscriptions"
    )
    city = models.ForeignKey(FavoriteCity, on_delete=models.CASCADE, related_name="alert_subscriptions")
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES, default="any")
    is_active = models.BooleanField(default=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "city", "alert_type")

    def __str__(self):
        return f"{self.user.username} - {self.city.name} - {self.alert_type}"

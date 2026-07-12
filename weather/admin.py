from django.contrib import admin

from .models import FavoriteCity, SearchHistory, WeatherAlertSubscription


@admin.register(FavoriteCity)
class FavoriteCityAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "user", "latitude", "longitude", "created_at")
    search_fields = ("name", "country", "user__username")


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ("query", "user", "searched_at")
    list_filter = ("searched_at",)
    search_fields = ("query", "user__username")


@admin.register(WeatherAlertSubscription)
class WeatherAlertSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "city", "alert_type", "is_active", "last_notified_at")
    list_filter = ("alert_type", "is_active")

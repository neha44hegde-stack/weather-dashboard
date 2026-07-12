from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "theme", "default_city", "email_alerts_enabled", "push_alerts_enabled")
    list_filter = ("theme", "email_alerts_enabled", "push_alerts_enabled")
    search_fields = ("user__username", "user__email", "default_city")

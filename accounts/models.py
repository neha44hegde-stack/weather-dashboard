from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """Extra per-user settings that don't belong on the built-in User model."""

    THEME_CHOICES = [
        ("light", "Light"),
        ("dark", "Dark"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default="light")
    default_city = models.CharField(max_length=120, blank=True)
    email_alerts_enabled = models.BooleanField(default=False)
    push_alerts_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile({self.user.username})"

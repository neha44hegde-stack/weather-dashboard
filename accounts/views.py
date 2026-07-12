from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render

from .models import UserProfile


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            return redirect("weather:dashboard")
    else:
        form = UserCreationForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile_obj.theme = request.POST.get("theme", profile_obj.theme)
        profile_obj.default_city = request.POST.get("default_city", profile_obj.default_city)
        profile_obj.email_alerts_enabled = "email_alerts_enabled" in request.POST
        profile_obj.push_alerts_enabled = "push_alerts_enabled" in request.POST
        profile_obj.save()
        return redirect("accounts:profile")

    return render(request, "accounts/profile.html", {"profile": profile_obj})

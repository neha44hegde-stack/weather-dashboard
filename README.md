# Weather Dashboard (Django)

A Django-based weather dashboard: current conditions, forecasts, AQI, UV index,
sunrise/sunset, favorites, search history, dark/light mode, and hooks for AI
summaries, email/push alerts, PDF/Excel export, and background jobs.

## Quick start (Docker, recommended)

```bash
cp .env.example .env
docker-compose up --build
```

Then in another terminal:

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

App: http://localhost:8000
Admin: http://localhost:8000/admin

## Quick start (local, no Docker — uses sqlite)

```bash
python -m venv venv
source venv/bin/activate       # venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env            # then remove/comment out DB_ENGINE=postgres to use sqlite
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Project layout

```
config/          Django project settings, root urls, celery app
accounts/        Registration, login, user profile (theme, default city, alert prefs)
weather/         Favorites, search history, alert subscriptions, Open-Meteo client, views
weather/services/open_meteo.py   API client (current, forecast, air quality, geocoding), Redis-cached
weather/tasks.py                 Celery background tasks (cache warming, alert emails)
templates/       HTML templates (base + accounts + weather)
static/css/      Base stylesheet with light/dark theme via CSS variables
```

## What's wired up already

- Current weather, 7-day forecast, AQI, UV index, sunrise/sunset — via Open-Meteo (free, no key)
- Forward geocoding (city name -> coordinates) via Open-Meteo geocoding API
- Favorites, search history, dashboard, dark/light mode (per-user, stored in DB)
- Django admin registered for all models
- Redis caching on every external API call (`WEATHER_CACHE_TTL_SECONDS`, default 600s)
- Celery + Celery Beat services in docker-compose, with two example tasks
- Docker Compose: web, db (Postgres), redis, celery worker, celery beat

## What's stubbed / next steps

- **Weather alerts (severe weather)**: Open-Meteo doesn't provide alerts; wire in
  OPENWEATHERMAP_API_KEY or WEATHERAPI_API_KEY (fields already in `.env.example`
  and `settings.py`) and add a fetch method to a new client class.
- **Reverse geocoding (coords -> city name)**: Open-Meteo doesn't offer this
  directly; either switch to OpenWeatherMap/WeatherAPI for this call, or use a
  separate reverse-geocoding API.
- **Push notifications**: needs a service worker + VAPID keys (web push) or FCM;
  not included yet.
- **AI features** (summaries, clothing/travel/farming/activity suggestions):
  `ANTHROPIC_API_KEY` is already read into settings; add a `weather/services/ai.py`
  that sends current + forecast JSON to the API and templates prompts per feature.
- **PDF export / Excel export**: `reportlab` and `openpyxl` are in requirements.txt,
  not yet wired to a view.
- **Charts**: no frontend charting library included yet (e.g. Chart.js via CDN).
- **GitHub Actions / CI/CD, Render/AWS deploy configs**: not included yet.

## Tech stack

Django 5, PostgreSQL, Redis, Celery, Docker, Open-Meteo API, DRF (for future API endpoints).

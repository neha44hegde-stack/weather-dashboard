# Weather Dashboard (Django)

A full-featured Django weather dashboard: hyperlocal weather (works for any
coordinates on Earth, not just major cities), forecasts, AQI, UV index,
comfort scoring, storm alerts, AI-powered summaries, rule-based clothing/crop/
food advice, PDF/Excel export, a REST API, and a passing test suite with CI.

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
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Running tests

```bash
python manage.py test
```

18 tests covering rule-based advice logic, authentication, favorites CRUD,
and the REST API. Also runs automatically on every push via GitHub Actions
(`.github/workflows/tests.yml`).

## Project layout
```
config/          Django project settings, root urls, celery app
accounts/        Registration, login, user profile (theme, default city, alert prefs)
weather/         Views, models, REST API, rule-based advice logic
weather/api.py                    REST API endpoints (JSON, testable via Thunder Client/Postman)
weather/services/open_meteo.py    Open-Meteo client: current/forecast/AQI/geocoding, Redis-cached
weather/services/ai.py            Anthropic API client for AI summaries/recommendations
weather/exports.py                PDF and Excel report generation
weather/tasks.py                  Celery background tasks (cache warming, alert emails)
weather/tests.py                  Test suite (18 tests)
templates/       HTML templates (base + accounts + weather), Chart.js trend charts
static/          CSS (light/dark theme), PWA manifest + service worker + icons
.github/workflows/tests.yml       CI: runs the test suite on every push/PR
```
## Features

**Hyperlocal location support** (the main thing that sets this apart from a
typical city-search weather app):
- Search by city name (Open-Meteo geocoding)
- Add any location manually by exact latitude/longitude
- "Use my current location" via browser geolocation
- Reverse geocoding (geopy/Nominatim) automatically names any coordinate,
  even small villages not in city-search databases

**Weather data:**
- Current conditions, 7-day forecast, AQI, UV index, weather condition text
- 7-day temperature/rain trend chart (Chart.js)
- Storm/thunderstorm alerts, detected from WMO weather codes (no extra API key)

**Recommendations** (rule-based, instant, no API key required):
- Sunscreen advice (from UV index)
- Clothing advice (temperature, rain chance, wind)
- Crop/farming advice (rain chance, temperature, AQI)
- Food & hydration advice (temperature, humidity)
- Comfort score (0-10, combining temperature, humidity, wind, UV, and AQI
  into a single number for outdoor activity)

**AI-powered** (needs `ANTHROPIC_API_KEY` in `.env`; degrades gracefully to
skip this section if not set):
- Plain-language weather summary
- Clothing, travel, farming, and activity recommendations

**Account features:**
- Registration/login, favorites, search history, dashboard
- Dark/light mode (per-user, stored in DB)
- Django admin registered for all models

**Export & API:**
- PDF report download (current conditions + 7-day forecast)
- Excel report download
- REST API: `GET /api/weather/<lat>/<lon>/` and `GET /api/favorites/`
  (session-authenticated JSON, for testing in Thunder Client/Postman or
  building a future mobile/frontend client)

**Progressive Web App (PWA):**
- Installable on mobile/desktop ("Add to Home Screen")
- Basic offline caching via service worker

**Infrastructure:**
- Redis caching on every external API call (falls back to in-memory cache
  automatically if `REDIS_URL` is unset, so local dev works without Redis)
- Celery + Celery Beat services in docker-compose, with example tasks
  (cache warming, alert emails) — needs Redis running to actually fire
- Docker Compose: web, db (Postgres), redis, celery worker, celery beat

## Known limitations / possible next steps

- **Real severe weather alerts** (cyclone/flood warnings from a government
  or weather service): currently only thunderstorm detection via weather
  codes. Wiring in `OPENWEATHERMAP_API_KEY` or `WEATHERAPI_API_KEY` (fields
  already in `.env.example`) would add proper alert feeds.
- **Push notifications** (browser push for rain/storms): not implemented;
  would need VAPID keys + a push subscription flow on top of the existing
  service worker.
- **Celery/email alerts**: the task code exists (`weather/tasks.py`) but
  needs Redis + a running Celery worker (via `docker-compose up`) to
  actually fire on a schedule.
- **Cloud deployment** (Render/AWS/etc.): not deployed yet; the Dockerfile
  and docker-compose setup are deployment-ready but untested on a live host.

## Tech stack

Django 5, Django REST Framework, PostgreSQL, Redis, Celery, Docker, Open-Meteo
API, geopy/Nominatim, Anthropic API (Claude), Chart.js, reportlab, openpyxl.
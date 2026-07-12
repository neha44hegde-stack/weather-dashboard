from django.urls import path

from . import views

app_name = "weather"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("search/", views.search_city, name="search"),
    path("favorites/add/", views.add_favorite, name="add_favorite"),
    path("favorites/<int:pk>/remove/", views.remove_favorite, name="remove_favorite"),
    path("history/", views.history, name="history"),
    path("city/<float:lat>/<float:lon>/", views.city_detail, name="city_detail"),
    path("city/<float:lat>/<float:lon>/export/pdf/", views.export_pdf, name="export_pdf"),
    path("city/<float:lat>/<float:lon>/export/excel/", views.export_excel, name="export_excel"),
]

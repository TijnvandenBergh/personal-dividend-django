from django.urls import path

from . import views

app_name = "dividends"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("contributions/", views.save_contribution, name="save_contribution"),
]

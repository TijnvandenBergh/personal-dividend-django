from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("prefs/theme/", views.set_theme, name="set_theme"),
    path("prefs/currency/", views.set_currency, name="set_currency"),
]

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST
from django_ratelimit.decorators import ratelimit

User = get_user_model()


@require_http_methods(["GET", "POST"])
@ratelimit(key="ip", rate="20/15m", method="POST", block=False)
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dividends:dashboard")

    error = None
    if request.method == "POST":
        if getattr(request, "limited", False):
            error = _("Too many login attempts, please try again later.")
        else:
            email = (request.POST.get("email") or "").strip().lower()
            password = request.POST.get("password") or ""
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect("dividends:dashboard")
            error = _("Invalid credentials")
    return render(request, "accounts/login.html", {"error": error})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect("dividends:dashboard")

    error = None
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""
        if "@" not in email:
            error = _("Invalid email")
        elif len(password) < 8:
            error = _("Password must be at least 8 characters")
        elif User.objects.filter(username=email).exists():
            error = _("Email already registered")
        else:
            user = User.objects.create_user(username=email, email=email, password=password)
            login(request, user)
            return redirect("dividends:dashboard")
    return render(request, "accounts/register.html", {"error": error})


@require_POST
def set_theme(request):
    theme = request.POST.get("theme")
    if theme in {"dark", "light"}:
        request.session["theme"] = theme
    next_url = request.POST.get("next") or reverse("dividends:dashboard")
    if request.headers.get("X-Requested-With") == "fetch":
        return JsonResponse({"theme": request.session["theme"]})
    return HttpResponseRedirect(next_url)


@require_POST
def set_currency(request):
    code = (request.POST.get("currency") or "").upper()
    if code in settings.SUPPORTED_CURRENCIES:
        request.session["currency"] = code
    next_url = request.POST.get("next") or reverse("dividends:dashboard")
    return HttpResponseRedirect(next_url)

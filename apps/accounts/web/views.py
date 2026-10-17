from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST


@require_http_methods(["GET"])
def home_view(request):
    return redirect("login")


@require_http_methods(["GET", "POST"])
def login_view(request):
    return render(request, "accounts/login.html")


@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")


@require_http_methods(["GET", "POST"])
def activate_view(request):
    return render(request, "accounts/activate.html")


@require_http_methods(["GET"])
def passkey_management(request):
    return render(request, "accounts/passkeys.html")

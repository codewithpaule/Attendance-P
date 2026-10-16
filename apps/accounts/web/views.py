from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User


@require_http_methods(["GET"])
def home_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if request.user.role == User.Role.TEACHER:
        return redirect("classroom_map")
    if request.user.role == User.Role.STUDENT:
        return redirect("student_checkin")
    if request.user.is_staff:
        return redirect("admin:index")
    return redirect("passkey_management")


@require_http_methods(["GET", "POST"])
def login_view(request):
    return render(request, "accounts/login.html")


@require_http_methods(["GET", "POST"])
def activate_view(request):
    return render(request, "accounts/activate.html")


@require_http_methods(["GET"])
@login_required(login_url="login")
def passkey_management(request):
    return render(request, "accounts/passkeys.html")

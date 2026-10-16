from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
@login_required(login_url="login")
def teacher_qr_view(request, session_id):
    return render(request, "attendance/teacher_qr.html", {"session_id": session_id})


@login_required(login_url="login")
@require_http_methods(["GET"])
def student_checkin_view(request):
    return render(request, "attendance/checkin.html")

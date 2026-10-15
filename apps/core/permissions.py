from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, _view):
        return request.user and request.user.is_authenticated and request.user.role == "ADMIN"


class IsTeacher(permissions.BasePermission):
    def has_permission(self, request, _view):
        return request.user and request.user.is_authenticated and request.user.role == "TEACHER"


class IsStudent(permissions.BasePermission):
    def has_permission(self, request, _view):
        return request.user and request.user.is_authenticated and request.user.role == "STUDENT"


class IsAdvisor(permissions.BasePermission):
    def has_permission(self, request, _view):
        return request.user and request.user.is_authenticated and request.user.role == "ADVISOR"


class IsAdminOrTeacher(permissions.BasePermission):
    def has_permission(self, request, _view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ("ADMIN", "TEACHER")
        )


class IsAdminOrAdvisor(permissions.BasePermission):
    def has_permission(self, request, _view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ("ADMIN", "ADVISOR")
        )

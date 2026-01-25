# -*- coding: utf-8 -*-
"""
Роли: admin (полный доступ), operator (проверки, шаблоны, статистика), user (свои проверки).
Группы Django: admin, operator, user.
"""
from functools import wraps

from django.conf import settings
from django.http import HttpResponseForbidden
from django.shortcuts import redirect


def get_user_role(user):
    """Возвращает роль: 'admin' | 'operator' | 'user' | None. Приоритет: admin > operator > user."""
    if not user or not user.is_authenticated:
        return None
    names = [g.name for g in user.groups.all()]
    if "admin" in names:
        return "admin"
    if "operator" in names:
        return "operator"
    if "user" in names:
        return "user"
    return None


def is_admin(user):
    return (get_user_role(user) == "admin") or (user and getattr(user, "is_superuser", False))


def is_operator(user):
    r = get_user_role(user)
    return r in ("admin", "operator") or (user and getattr(user, "is_superuser", False))


def is_user(user):
    """Может видеть свои проверки (user, operator, admin)."""
    r = get_user_role(user)
    return r in ("admin", "operator", "user")


def can_edit_templates(user):
    """Редактировать шаблоны (типы ссылок) — только admin."""
    return is_admin(user)


def can_see_all_checks(user):
    """Видеть все проверки — operator, admin и is_staff (is_staff без доступа в админку)."""
    return is_operator(user) or (user and getattr(user, "is_staff", False))


def can_see_templates(user):
    """Видеть шаблоны (просмотр) — operator и admin."""
    return is_operator(user)


def login_required(view):
    """Редирект на login, если не авторизован."""
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = settings.LOGIN_URL
            next_url = request.get_full_path()
            return redirect(f"{login_url}?next={next_url}")
        return view(request, *args, **kwargs)
    return _wrapped


def role_required(*roles):
    """Доступ только для перечисленных ролей. is_admin всегда проходит."""
    def decorator(view):
        @wraps(view)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{settings.LOGIN_URL}?next={request.get_full_path()}")
            if is_admin(request.user):
                return view(request, *args, **kwargs)
            if get_user_role(request.user) in roles:
                return view(request, *args, **kwargs)
            return HttpResponseForbidden("Доступ запрещён.")
        return _wrapped
    return decorator

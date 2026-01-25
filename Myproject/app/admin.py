# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import ReferenceType, ReferenceField, Reference, ReferenceIssue, ReferenceText


# Роли хранятся в группах: admin, operator, user. Добавление пользователей — в /admin/, группу выбрать в форме.
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "get_roles")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")

    def get_roles(self, obj):
        return ", ".join(g.name for g in obj.groups.all()) or "—"

    get_roles.short_description = "Роли (admin / operator / user)"


class ReferenceFieldInline(admin.TabularInline):
    model = ReferenceField
    extra = 0
    fields = ("name", "label", "required", "order_index", "separator_before", "separator_after", "comment")


@admin.register(ReferenceType)
class ReferenceTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    inlines = [ReferenceFieldInline]


@admin.register(ReferenceText)
class ReferenceTextAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "status", "created_at")
    list_filter = ("status", "user")
    search_fields = ("title", "input_text")


# is_staff видит все проверки в приложении, но в админку — только is_superuser или группа admin
def _admin_has_permission(request):
    if not request.user.is_active or not request.user.is_staff:
        return False
    from .auth_utils import get_user_role
    return request.user.is_superuser or get_user_role(request.user) == "admin"


admin.site.has_permission = _admin_has_permission


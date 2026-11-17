from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "full_name", "role", "is_staff", "is_active")
    search_fields = ("username", "email", "full_name")
    ordering = ("username",)
    fieldsets = UserAdmin.fieldsets + (
        ("Profile", {"fields": ("full_name", "role")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Profile", {"fields": ("full_name", "role")}),
    )

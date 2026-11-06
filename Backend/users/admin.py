from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, UserRole


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'is_superuser', 'is_active', 'created_at']
    list_filter = ['is_superuser', 'is_active', 'created_at']
    search_fields = ['username', 'email']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal info', {'fields': ('avatar_url',)}),
        ('Permissions', {'fields': ('is_active', 'is_superuser', 'groups', 'user_permissions')},),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_login']
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['user__username', 'user__email']
    raw_id_fields = ['user']

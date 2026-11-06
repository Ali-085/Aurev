from django.contrib import admin
from .models import Server, ServerMember


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner_user', 'platform', 'is_verified', 'suspended', 'created_at']
    list_filter = ['platform', 'is_verified', 'suspended', 'created_at']
    search_fields = ['name', 'description', 'owner_user__username']
    raw_id_fields = ['owner_user']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('owner_user', 'name', 'description')
        }),
        ('Platform', {
            'fields': ('platform', 'invite_link')
        }),
        ('Status', {
            'fields': ('is_verified', 'suspended', 'suspension_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ServerMember)
class ServerMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'server', 'total_verified_payouts', 'total_submissions', 'joined_at']
    list_filter = ['joined_at']
    search_fields = ['user__username', 'server__name']
    raw_id_fields = ['server', 'user']
    readonly_fields = ['joined_at', 'total_verified_payouts', 'total_submissions', 'last_submission_at']

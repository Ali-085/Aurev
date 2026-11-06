from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['actor_user', 'action_type', 'target_table', 'target_id', 'created_at']
    list_filter = ['action_type', 'target_table', 'created_at']
    search_fields = ['actor_user__username', 'target_table', 'target_id']
    raw_id_fields = ['actor_user']
    readonly_fields = ['actor_user', 'action_type', 'target_table', 'target_id', 'metadata', 'created_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        # Prevent manual creation of audit logs
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of audit logs
        return False

from django.contrib import admin
from .models import CertificateRecord, ActivityLog, DashboardStats


@admin.register(CertificateRecord)
class CertificateRecordAdmin(admin.ModelAdmin):
    list_display = [
        'index_number', 
        'name', 
        'programme', 
        'department', 
        'status', 
        'upload_date',
        'uploaded_by',
        'collected_by'
    ]
    list_filter = ['status', 'department', 'programme', 'upload_date']
    search_fields = ['index_number', 'name', 'programme', 'department']
    readonly_fields = ['upload_date', 'collected_at']
    list_per_page = 50
    date_hierarchy = 'upload_date'
    
    fieldsets = (
        ('Student Information', {
            'fields': ('name', 'index_number', 'programme', 'department')
        }),
        ('Certificate Details', {
            'fields': ('slip_number', 'status', 'collected_at')
        }),
        ('Tracking Information', {
            'fields': ('upload_date', 'uploaded_by', 'collected_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'action',
        'description',
        'timestamp',
        'ip_address'
    ]
    list_filter = ['action', 'timestamp', 'user']
    search_fields = ['user__username', 'description', 'ip_address']
    readonly_fields = ['user', 'action', 'description', 'timestamp', 'ip_address', 'certificate']
    list_per_page = 100
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        # Don't allow manual creation
        return False
    
    def has_change_permission(self, request, obj=None):
        # Don't allow editing
        return False


@admin.register(DashboardStats)
class DashboardStatsAdmin(admin.ModelAdmin):
    list_display = [
        'date',
        'total_certificates',
        'collected_certificates',
        'pending_certificates',
        'total_uploads_today',
        'total_collections_today',
        'active_users',
        'last_updated'
    ]
    readonly_fields = [
        'date',
        'total_certificates',
        'collected_certificates', 
        'pending_certificates',
        'total_uploads_today',
        'total_collections_today',
        'active_users',
        'last_updated'
    ]
    list_per_page = 30
    
    def has_add_permission(self, request):
        return False

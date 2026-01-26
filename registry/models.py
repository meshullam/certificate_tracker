from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class CertificateRecord(models.Model):
    """
    Model to store certificate/result slip records for students.
    """
    STATUS_CHOICES = [
        ('Not Collected', 'Not Collected'),
        ('Collected', 'Collected'),
    ]

    name = models.CharField(max_length=255, help_text="Student's full name")
    index_number = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Student's index/admission number"
    )
    programme = models.CharField(max_length=255, help_text="Programme/Course name")
    slip_number = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Certificate/slip number"
    )
    department = models.CharField(max_length=255, help_text="Department/Faculty")
    upload_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='Not Collected'
    )
    collected_at = models.DateTimeField(null=True, blank=True)
    
    # Track who uploaded/collected
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_certificates',
        help_text="User who uploaded this record"
    )
    collected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='collected_certificates',
        help_text="User who marked this as collected"
    )

    class Meta:
        ordering = ['-upload_date']
        indexes = [
            models.Index(fields=['index_number']),
            models.Index(fields=['status']),
            models.Index(fields=['-upload_date']),
        ]
        verbose_name = 'Certificate Record'
        verbose_name_plural = 'Certificate Records'

    def __str__(self):
        return f"{self.name} - {self.index_number}"

    def mark_collected(self, user):
        """Mark certificate as collected by a specific user"""
        self.status = 'Collected'
        self.collected_at = timezone.now()
        self.collected_by = user
        self.save()

    def is_collected(self):
        """Check if certificate has been collected"""
        return self.status == 'Collected'

    @property
    def days_since_upload(self):
        """Calculate days since upload"""
        delta = timezone.now() - self.upload_date
        return delta.days


class ActivityLog(models.Model):
    """
    Model to track all user activities in the system.
    """
    ACTION_CHOICES = [
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('UPLOAD', 'Upload Certificates'),
        ('COLLECT', 'Collect Certificate'),
        ('DOWNLOAD_REPORT', 'Download Report'),
        ('CREATE_USER', 'Create User'),
        ('EDIT_USER', 'Edit User'),
        ('DELETE_USER', 'Delete User'),
        ('RESET_PASSWORD', 'Reset Password'),
        ('SEARCH', 'Search Records'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activities',
        help_text="User who performed the action"
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        help_text="Type of action performed"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the action"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the user"
    )
    
    # Optional: Link to related certificate record
    certificate = models.ForeignKey(
        CertificateRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        help_text="Related certificate record (if applicable)"
    )

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'

    def __str__(self):
        return f"{self.user.username} - {self.get_action_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    @classmethod
    def log_activity(cls, user, action, description='', certificate=None, ip_address=None):
        """
        Convenience method to log an activity.
        
        Usage:
            ActivityLog.log_activity(
                user=request.user,
                action='UPLOAD',
                description='Uploaded 50 certificate records'
            )
        """
        return cls.objects.create(
            user=user,
            action=action,
            description=description,
            certificate=certificate,
            ip_address=ip_address
        )

    @classmethod
    def get_recent_activities(cls, limit=10):
        """Get recent activities across all users"""
        return cls.objects.select_related('user', 'certificate').all()[:limit]

    @classmethod
    def get_user_activities(cls, user, limit=20):
        """Get activities for a specific user"""
        return cls.objects.filter(user=user).select_related('certificate')[:limit]

    @classmethod
    def get_today_activities(cls):
        """Get today's activities"""
        today = timezone.now().date()
        return cls.objects.filter(timestamp__date=today).select_related('user', 'certificate')


class DashboardStats(models.Model):
    """
    Model to cache dashboard statistics for performance.
    Updates periodically or on significant events.
    """
    date = models.DateField(unique=True, default=timezone.now)
    total_certificates = models.IntegerField(default=0)
    collected_certificates = models.IntegerField(default=0)
    pending_certificates = models.IntegerField(default=0)
    total_uploads_today = models.IntegerField(default=0)
    total_collections_today = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Dashboard Statistics'
        verbose_name_plural = 'Dashboard Statistics'

    def __str__(self):
        return f"Stats for {self.date}"

    @classmethod
    def get_or_create_today_stats(cls):
        """Get or create today's statistics"""
        today = timezone.now().date()
        stats, created = cls.objects.get_or_create(date=today)
        if created or (timezone.now() - stats.last_updated).seconds > 300:  # Update every 5 minutes
            stats.update_stats()
        return stats

    def update_stats(self):
        """Update statistics from database"""
        from django.contrib.auth.models import User
        
        # Certificate stats
        self.total_certificates = CertificateRecord.objects.count()
        self.collected_certificates = CertificateRecord.objects.filter(status='Collected').count()
        self.pending_certificates = CertificateRecord.objects.filter(status='Not Collected').count()
        
        # Today's activities
        today = timezone.now().date()
        self.total_uploads_today = ActivityLog.objects.filter(
            timestamp__date=today,
            action='UPLOAD'
        ).count()
        self.total_collections_today = ActivityLog.objects.filter(
            timestamp__date=today,
            action='COLLECT'
        ).count()
        
        # Active users (logged in within last 24 hours)
        from datetime import timedelta
        yesterday = timezone.now() - timedelta(days=1)
        self.active_users = ActivityLog.objects.filter(
            timestamp__gte=yesterday,
            action='LOGIN'
        ).values('user').distinct().count()
        
        self.save()
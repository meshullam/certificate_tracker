from django.db import models

class CertificateRecord(models.Model):
    STATUS_CHOICES = [
        ('Not Collected', 'Not Collected'),
        ('Collected', 'Collected'),
    ]

    name = models.CharField(max_length=255)
    index_number = models.CharField(max_length=100, unique=True)
    programme = models.CharField(max_length=255)
    slip_number = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=255)
    upload_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Not Collected')
    collected_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.index_number}"



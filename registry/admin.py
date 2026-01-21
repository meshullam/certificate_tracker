from django.contrib import admin
from django.contrib import admin
from django.contrib import admin
from django.contrib.admin import AdminSite

# Custom AdminSite class to inject your CSS
class CustomAdminSite(AdminSite):
    site_header = "Certificate Tracker Administration"
    site_title = "Certificate Tracker Admin"
    index_title = "Welcome to the Registry Dashboard"

    # Attach your custom CSS
    class Media:
        css = {
            'all': ('registry/css/admin_theme.css',)
        }

# Replace Django's default admin site with your custom one
admin.site = CustomAdminSite()


# Customizing the admin site
admin.site.site_header = "Certificate Tracker Administration"
admin.site.site_title = "Certificate Tracker Admin Portal"
admin.site.index_title = "Welcome to the Certificate Tracker System"

# Register your models here.

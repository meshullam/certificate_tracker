from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('login')),  # Redirect root `/` to login
    path('', include('accounts.urls')),
    path('registry/', include('registry.urls')),
    path('adminpanel/', include('admin_panel.urls')),

]

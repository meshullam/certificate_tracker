from django.urls import path
from django.contrib.auth import views as auth_views

# ==================================================================
# Accounts App URL Configuration
# ==================================================================
# Handles user authentication (login/logout)
# All URLs are prefixed with '' (root level in main urls.py)
# Examples:
#   - /login/
#   - /logout/
# ==================================================================

urlpatterns = [
    # ==================================================================
    # AUTHENTICATION
    # ==================================================================
    
    # Login page - Uses Django's built-in LoginView
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='accounts/login.html'),
        name='login'
    ),
    
    # Logout - Redirects to login page after logout
    path(
        'logout/',
        auth_views.LogoutView.as_view(next_page='login'),
        name='logout'
    ),
]

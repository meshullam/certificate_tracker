from django.urls import path
from . import views

# ==================================================================
# Admin Panel URL Configuration
# ==================================================================
# All URLs are prefixed with 'adminpanel/' (defined in main urls.py)
# Examples:
#   - /adminpanel/login/
#   - /adminpanel/dashboard/
#   - /adminpanel/manage-users/
# ==================================================================

urlpatterns = [
    # ==================================================================
    # AUTHENTICATION
    # ==================================================================
    path('login/', views.admin_login, name='adminpanel_login'),
    path('logout/', views.admin_logout, name='adminpanel_logout'),
    
    # ==================================================================
    # DASHBOARD
    # ==================================================================
    path('dashboard/', views.dashboard, name='admin_dashboard'),
    
    # ==================================================================
    # USER MANAGEMENT
    # ==================================================================
    # List and search users
    path('manage-users/', views.manage_users, name='manage_users'),
    
    # Create new user
    path('add-user/', views.add_user, name='add_user'),
    
    # Edit existing user
    path('edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    
    # Reset user password
    path('reset-password/<int:user_id>/', views.reset_password, name='reset_password'),
    
    # Delete user
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
]

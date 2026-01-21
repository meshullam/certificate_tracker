from django.urls import path
from . import views


urlpatterns = [
    path('login/', views.admin_login, name='adminpanel_login'),
    path('logout/', views.admin_logout, name='adminpanel_logout'),
    path('dashboard/', views.dashboard, name='admin_dashboard'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('add-user/', views.add_user, name='add_user'),
    path('edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('reset-password/<int:user_id>/', views.reset_password, name='reset_password'),

    path('add-user/', views.add_user, name='add_user'),
    path('edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('reset-password/<int:user_id>/', views.reset_password, name='reset_password'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
]


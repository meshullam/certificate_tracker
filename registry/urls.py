from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_excel, name='upload_excel'),
    path('collect/<int:pk>/', views.collect_certificate, name='collect_certificate'),
    path('generate_report/', views.generate_report, name='generate_report'),
    path('dashboard/', views.dashboard, name='dashboard'),
]

from django.urls import path
from . import views
from .public_search_api import public_certificate_search

urlpatterns = [
    path('upload/', views.upload_excel, name='upload_excel'),
    path('collect/<int:pk>/', views.collect_certificate, name='collect_certificate'),
    path('generate_report/', views.generate_report, name='generate_report'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('api/certificate-search/', public_certificate_search, name='public_certificate_search'),
]

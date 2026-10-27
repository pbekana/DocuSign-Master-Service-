"""URL routing for maintenance operations."""
from django.urls import path
from apps.jobs.maintenance_views import (
    MaintenanceCleanupView,
    DetectCrashedView,
)

urlpatterns = [
    path('cleanup', MaintenanceCleanupView.as_view(), name='maintenance-cleanup'),
    path('detect-crashed', DetectCrashedView.as_view(), name='detect-crashed'),
]

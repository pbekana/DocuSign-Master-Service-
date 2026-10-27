"""URL routing for job management."""
from django.urls import path
from apps.jobs.views import (
    StartScanView,
    ScanStatusView,
    CancelScanView,
    ResumeScanView,
    ListScansView,
    ScanStatisticsView,
    RemoveScanView,
)

urlpatterns = [
    path('start', StartScanView.as_view(), name='start-scan'),
    path('<str:scan_id>/status', ScanStatusView.as_view(), name='scan-status'),
    path('<str:scan_id>/cancel', CancelScanView.as_view(), name='cancel-scan'),
    path('<str:scan_id>/resume', ResumeScanView.as_view(), name='resume-scan'),
    path('list', ListScansView.as_view(), name='list-scans'),
    path('statistics', ScanStatisticsView.as_view(), name='scan-statistics'),
    path('<str:scan_id>/remove', RemoveScanView.as_view(), name='remove-scan'),
]

"""URL routing for common endpoints."""
from django.urls import path
from common.views import HealthView, StatsView

urlpatterns = [
    path('', HealthView.as_view(), name='health'),
]

# Note: /api/stats is routed directly from config/urls.py to StatsView

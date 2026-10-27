"""URL Configuration for DocuSign Master Service"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from common.views import HealthView, StatsView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include([
        path('scan/', include('apps.jobs.urls')),
        path('normalization/', include('apps.normalization.urls')),
        path('validate-credentials', include('apps.authentication.urls')),
        path('maintenance/', include('apps.jobs.maintenance_urls')),
        path('audit/', include('apps.audit.urls')),
        path('health', HealthView.as_view(), name='health'),
        path('stats', StatsView.as_view(), name='stats'),
    ])),
]

if settings.DEBUG:
    urlpatterns += [
        path('api-auth/', include('rest_framework.urls')),
    ]

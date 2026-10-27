"""URL routing for authentication endpoints."""
from django.urls import path
from apps.authentication.views import ValidateCredentialsView

urlpatterns = [
    path('', ValidateCredentialsView.as_view(), name='validate-credentials'),
]

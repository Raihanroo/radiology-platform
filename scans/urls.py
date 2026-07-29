from django.urls import path
from .views import ScanAnalyzeView

urlpatterns = [
    path("analyze/", ScanAnalyzeView.as_view(), name="scan-analyze"),
]

from django.urls import path
from .views import ScanAnalyzeView, ReviewQueueListView, ScanReviewCreateView

urlpatterns = [
    path("analyze/", ScanAnalyzeView.as_view(), name="scan-analyze"),
    path("review-queue/", ReviewQueueListView.as_view(), name="scan-review-queue"),
    path(
        "<int:scan_id>/review/",
        ScanReviewCreateView.as_view(),
        name="scan-review-create",
    ),
]

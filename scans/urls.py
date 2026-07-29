from django.urls import path
from .views import (
    ScanAnalyzeView,
    ReviewQueueListView,
    ScanReviewCreateView,
    MyScansListView,
    ReviewedByMeListView,
)

urlpatterns = [
    path("analyze/", ScanAnalyzeView.as_view(), name="scan-analyze"),
    path("my-scans/", MyScansListView.as_view(), name="scan-my-list"),
    path("review-queue/", ReviewQueueListView.as_view(), name="scan-review-queue"),
    path("reviewed-by-me/", ReviewedByMeListView.as_view(), name="scan-reviewed-by-me"),
    path(
        "<int:scan_id>/review/",
        ScanReviewCreateView.as_view(),
        name="scan-review-create",
    ),
]

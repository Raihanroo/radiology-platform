from django.urls import path
from .views import (
    ScanAnalyzeView,
    ReviewQueueListView,
    ScanReviewCreateView,
    MyScansListView,
    ReviewedByMeListView,
    ConsultationQueueListView,
    ScanConsultCreateView,
    GenerateReportView,
    ApproveReportView,
)

urlpatterns = [
    path("analyze/", ScanAnalyzeView.as_view(), name="scan-analyze"),
    path("my-scans/", MyScansListView.as_view(), name="scan-my-list"),
    path("review-queue/", ReviewQueueListView.as_view(), name="scan-review-queue"),
    path("reviewed-by-me/", ReviewedByMeListView.as_view(), name="scan-reviewed-by-me"),
    path(
        "consultation-queue/",
        ConsultationQueueListView.as_view(),
        name="scan-consultation-queue",
    ),
    path(
        "<int:scan_id>/review/",
        ScanReviewCreateView.as_view(),
        name="scan-review-create",
    ),
    path(
        "<int:scan_id>/consult/",
        ScanConsultCreateView.as_view(),
        name="scan-consult-create",
    ),
    path(
        "<int:scan_id>/generate-report/",
        GenerateReportView.as_view(),
        name="scan-generate-report",
    ),
    path(
        "<int:scan_id>/approve-report/",
        ApproveReportView.as_view(),
        name="scan-approve-report",
    ),
]

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
    ClinicalSummaryView,
    InterpretResultView,
    DraftReportView,
    CompareProgressionView,
    AskMedicalQuestionView,
    FollowUpRecommendationsView,
    PatientExplanationView,
    AdminDashboardStatsView,
    BookAppointmentView,
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
    # ---- LLM Clinical Assistant endpoints ----
    path(
        "<int:scan_id>/clinical-summary/",
        ClinicalSummaryView.as_view(),
        name="scan-clinical-summary",
    ),
    path(
        "<int:scan_id>/interpret-result/",
        InterpretResultView.as_view(),
        name="scan-interpret-result",
    ),
    path(
        "<int:scan_id>/draft-report/",
        DraftReportView.as_view(),
        name="scan-draft-report",
    ),
    path(
        "<int:scan_id>/compare/<int:other_scan_id>/",
        CompareProgressionView.as_view(),
        name="scan-compare-progression",
    ),
    path(
        "<int:scan_id>/ask/",
        AskMedicalQuestionView.as_view(),
        name="scan-ask-question",
    ),
    path(
        "<int:scan_id>/follow-up-recommendations/",
        FollowUpRecommendationsView.as_view(),
        name="scan-follow-up-recommendations",
    ),
    path(
        "<int:scan_id>/explanation/",
        PatientExplanationView.as_view(),
        name="scan-patient-explanation",
    ),
    # <--- ২. নিচের লাইনটি নতুন যুক্ত করা হয়েছে
    path("admin-stats/", AdminDashboardStatsView.as_view(), name="admin-stats"),
    
    path(
        "<int:scan_id>/book-appointment/",
        BookAppointmentView.as_view(),
        name="book-appointment",
    ),
]

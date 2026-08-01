from rest_framework import serializers
from .models import (
    MRIScan,
    AIAnalysisResult,
    RadiologistReview,
    DoctorConsultation,
    FinalReport,
    Appointment,
)


class AIAnalysisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnalysisResult
        fields = [
            "id",
            "classification",
            "confidence_score",
            "segmentation_mask",
            "segmented_overlay",
            "tumor_area_pixels",
            "tumor_area_percentage",
            "needs_review",
            "processed_at",
        ]


class RadiologistReviewSerializer(serializers.ModelSerializer):
    radiologist = serializers.CharField(source="radiologist.username", read_only=True)

    class Meta:
        model = RadiologistReview
        fields = [
            "id",
            "radiologist",
            "status",
            "observations",
            "corrected_classification",
            "reviewed_at",
        ]


class RadiologistReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RadiologistReview
        fields = ["status", "observations", "corrected_classification"]


class DoctorConsultationSerializer(serializers.ModelSerializer):
    doctor = serializers.CharField(source="doctor.username", read_only=True)

    class Meta:
        model = DoctorConsultation
        fields = [
            "id",
            "doctor",
            "clinical_assessment",
            "treatment_recommendation",
            "consulted_at",
        ]


class DoctorConsultationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorConsultation
        fields = ["clinical_assessment", "treatment_recommendation"]


class FinalReportSerializer(serializers.ModelSerializer):
    generated_by = serializers.CharField(source="generated_by.username", read_only=True)
    approved_by = serializers.CharField(
        source="approved_by.username", read_only=True, allow_null=True
    )

    class Meta:
        model = FinalReport
        fields = [
            "id",
            "final_diagnosis",
            "summary",
            "status",
            "generated_by",
            "approved_by",
            "generated_at",
            "approved_at",
        ]


class FinalReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinalReport
        fields = ["summary"]


class MRIScanSerializer(serializers.ModelSerializer):
    analysis = AIAnalysisResultSerializer(read_only=True)
    radiologist_review = RadiologistReviewSerializer(read_only=True)
    doctor_consultation = DoctorConsultationSerializer(read_only=True)
    final_report = serializers.SerializerMethodField()

    # পেশেন্ট এবং আপলোডারের আইডির বদলে ইউজারনেম দেখানোর জন্য
    patient = serializers.CharField(source="patient.username", read_only=True)
    uploaded_by = serializers.CharField(source="uploaded_by.username", read_only=True)

    class Meta:
        model = MRIScan
        fields = [
            "id",
            "patient",
            "uploaded_by",
            "original_image",
            "scan_type",
            "uploaded_at",
            "analysis",
            "radiologist_review",
            "doctor_consultation",
            "final_report",
        ]
        read_only_fields = ["uploaded_by"]

    def get_final_report(self, obj):
        report = getattr(obj, "final_report", None)
        if report is None:
            return None

        request = self.context.get("request")
        if (
            request is not None
            and getattr(request.user, "role", None) == "patient"
            and report.status != "approved"
        ):
            return None

        return FinalReportSerializer(report).data


class ScanUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = MRIScan
        fields = ["original_image", "scan_type"]


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = "__all__"
        read_only_fields = ["status", "created_at"]

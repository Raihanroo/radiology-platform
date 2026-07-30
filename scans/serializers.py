from rest_framework import serializers
from .models import (
    MRIScan,
    AIAnalysisResult,
    RadiologistReview,
    DoctorConsultation,
    FinalReport,
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
        
from .models import Appointment 


class RadiologistReviewSerializer(serializers.ModelSerializer):
    """
    Review দেখানোর জন্য (read) -- radiologist-এর username দেখানো হয়,
    পুরো User object না (privacy/simplicity)।
    """

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
    """
    Radiologist review জমা দেওয়ার জন্য (write)। scan ও radiologist এখানে
    client থেকে নেওয়া হয় না -- view থেকে সেট হয় (URL-এর scan_id + request.user)।
    """

    class Meta:
        model = RadiologistReview
        fields = ["status", "observations", "corrected_classification"]


class DoctorConsultationSerializer(serializers.ModelSerializer):
    """Doctor consultation দেখানোর জন্য (read)।"""

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
    """
    Doctor consultation জমা দেওয়ার জন্য (write)। scan ও doctor client থেকে
    নেওয়া হয় না -- view থেকে সেট হয় (URL-এর scan_id + request.user)।
    """

    class Meta:
        model = DoctorConsultation
        fields = ["clinical_assessment", "treatment_recommendation"]


class FinalReportSerializer(serializers.ModelSerializer):
    """Final Report দেখানোর জন্য (read)।"""

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
    """
    Final Report generate করার জন্য (write)। শুধু doctor-এর লেখা summary নেওয়া হয়;
    final_diagnosis, scan, generated_by, status -- সবকিছু view-তে নির্ধারিত হয়।
    """

    class Meta:
        model = FinalReport
        fields = ["summary"]


class MRIScanSerializer(serializers.ModelSerializer):
    analysis = AIAnalysisResultSerializer(read_only=True)
    radiologist_review = RadiologistReviewSerializer(read_only=True)
    doctor_consultation = DoctorConsultationSerializer(read_only=True)
    final_report = serializers.SerializerMethodField()

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
        """
        গুরুত্বপূর্ণ নিরাপত্তা নিয়ম: patient শুধু 'approved' status-এর report দেখবে।
        Draft report radiologist/doctor/staff সবসময় দেখতে পারবে (context-এর request
        থেকে role চেক করা হয়), কিন্তু patient-এর কাছে draft report null হিসেবে দেখাবে
        -- ঠিক infographic-এর নিয়ম অনুযায়ী ("Only the Final Approved Report is
        delivered to the Patient")।
        """
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
    """
    patient ফিল্ড ইচ্ছাকৃতভাবে বাদ দেওয়া হয়েছে -- client কে নিজের patient ID
    বেছে নিতে দিলে সে অন্য patient-এর নামে scan আপলোড করে দিতে পারতো (security risk)।
    View-তে patient=request.user সেট করা হয়।
    """

    class Meta:
        model = MRIScan
        fields = ["original_image", "scan_type"]

class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = '__all__'
        read_only_fields = ['status', 'created_at']
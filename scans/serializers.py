from rest_framework import serializers
from .models import MRIScan, AIAnalysisResult, RadiologistReview


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


class MRIScanSerializer(serializers.ModelSerializer):
    analysis = AIAnalysisResultSerializer(read_only=True)
    radiologist_review = RadiologistReviewSerializer(read_only=True)

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
        ]
        read_only_fields = ["uploaded_by"]


class ScanUploadSerializer(serializers.ModelSerializer):
    """
    patient ফিল্ড ইচ্ছাকৃতভাবে বাদ দেওয়া হয়েছে -- client কে নিজের patient ID
    বেছে নিতে দিলে সে অন্য patient-এর নামে scan আপলোড করে দিতে পারতো (security risk)।
    View-তে patient=request.user সেট করা হয়।
    """

    class Meta:
        model = MRIScan
        fields = ["original_image", "scan_type"]

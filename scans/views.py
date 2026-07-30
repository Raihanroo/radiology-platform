import os
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.parsers import MultiPartParser, FormParser
from accounts.permissions import IsPatient, IsRadiologist, IsDoctor

from .models import MRIScan, AIAnalysisResult, RadiologistReview, DoctorConsultation
from .serializers import (
    MRIScanSerializer,
    ScanUploadSerializer,
    RadiologistReviewCreateSerializer,
    DoctorConsultationCreateSerializer,
)
from .inference import predict_tumor, predict_segmentation


class ScanAnalyzeView(APIView):
    """
    শুধু patient role-এর ইউজার নিজের scan আপলোড ও analyze করতে পারবে
    (infographic workflow ধাপ ১ অনুযায়ী)।
    """

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsPatient]

    def post(self, request):
        upload_serializer = ScanUploadSerializer(data=request.data)
        if not upload_serializer.is_valid():
            return Response(
                upload_serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        scan = upload_serializer.save(patient=request.user, uploaded_by=request.user)

        # ১. Classification
        try:
            result = predict_tumor(scan.original_image.path)
        except Exception as e:
            return Response(
                {"error": f"Classification failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ২. Segmentation (সবসময় চালানো হয় — classification যাই বলুক না কেন।
        # কারণ: দুটো model independent, classification ভুল করলেও segmentation
        # প্রকৃত tumor ধরতে পারে (cross-check হিসেবে কাজ করে))
        seg_result = None
        try:
            mask_dir = os.path.join(settings.MEDIA_ROOT, "scans", "masks")
            os.makedirs(mask_dir, exist_ok=True)
            seg_result = predict_segmentation(scan.original_image.path, mask_dir)
        except Exception as e:
            # Segmentation ব্যর্থ হলেও classification result তো আছে, তাই পুরো request fail করাচ্ছি না
            seg_result = None

        # ৩. Review প্রয়োজন কিনা যাচাই করি
        # Classifier "notumor" বলল, কিন্তু segmentation উল্লেখযোগ্য tumor area পেলে
        # (থ্রেশহোল্ড: 1%) — এটা দুই মডেলের মধ্যে দ্বন্দ্ব, তাই ম্যানুয়াল review দরকার
        REVIEW_THRESHOLD_PERCENT = 1.0
        needs_review = (
            result["classification"] == "notumor"
            and seg_result is not None
            and seg_result["tumor_area_percentage"] > REVIEW_THRESHOLD_PERCENT
        )

        # ৪. Analysis result সেভ করি
        analysis = AIAnalysisResult.objects.create(
            scan=scan,
            classification=result["classification"],
            confidence_score=result["confidence"],
            tumor_area_pixels=seg_result["tumor_area_pixels"] if seg_result else None,
            tumor_area_percentage=(
                seg_result["tumor_area_percentage"] if seg_result else None
            ),
            needs_review=needs_review,
        )

        if seg_result:
            analysis.segmentation_mask = f"scans/masks/{seg_result['mask_filename']}"
            analysis.segmented_overlay = f"scans/masks/{seg_result['overlay_filename']}"
            analysis.save()

        # ৫. Response পাঠানো
        response_serializer = MRIScanSerializer(scan)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class MyScansListView(generics.ListAPIView):
    """
    GET /api/scans/my-scans/
    শুধু patient -- নিজের আপলোড করা সব scan-এর history দেখতে পারবে
    (সবচেয়ে নতুন scan আগে)।
    """

    serializer_class = MRIScanSerializer
    permission_classes = [IsPatient]

    def get_queryset(self):
        return MRIScan.objects.filter(patient=self.request.user).order_by(
            "-uploaded_at"
        )


class ReviewedByMeListView(generics.ListAPIView):
    """
    GET /api/scans/reviewed-by-me/
    শুধু radiologist -- সে নিজে যেসব scan review করেছে তার history দেখতে পারবে।
    """

    serializer_class = MRIScanSerializer
    permission_classes = [IsRadiologist]

    def get_queryset(self):
        return MRIScan.objects.filter(
            radiologist_review__radiologist=self.request.user
        ).order_by("-radiologist_review__reviewed_at")


class ReviewQueueListView(generics.ListAPIView):
    """
    GET /api/scans/review-queue/
    শুধু radiologist দেখতে পারবে -- এমন সব scan যেগুলোর needs_review=True
    এবং এখনো কোনো radiologist review হয়নি (pending queue)।
    """

    serializer_class = MRIScanSerializer
    permission_classes = [IsRadiologist]

    def get_queryset(self):
        return MRIScan.objects.filter(
            analysis__needs_review=True, radiologist_review__isnull=True
        ).order_by("uploaded_at")


class ScanReviewCreateView(APIView):
    """
    POST /api/scans/<scan_id>/review/
    Radiologist একটা নির্দিষ্ট scan-এর জন্য review জমা দেয়
    (approved/rejected/modified + observations + corrected_classification)।
    """

    permission_classes = [IsRadiologist]

    def post(self, request, scan_id):
        scan = get_object_or_404(MRIScan, id=scan_id)

        # একটা scan-এ ইতিমধ্যে review থাকলে দ্বিতীয়বার review করা যাবে না
        # (OneToOneField constraint অনুযায়ী -- ভবিষ্যতে চাইলে "update" endpoint আলাদা বানানো যাবে)
        if hasattr(scan, "radiologist_review"):
            return Response(
                {"error": "এই scan-টা ইতিমধ্যে review করা হয়ে গেছে।"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RadiologistReviewCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(scan=scan, radiologist=request.user)

        response_serializer = MRIScanSerializer(scan)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ConsultationQueueListView(generics.ListAPIView):
    """
    GET /api/scans/consultation-queue/
    শুধু doctor দেখতে পারবে -- এমন সব scan যেগুলোর radiologist review
    হয়ে গেছে কিন্তু এখনো doctor consultation হয়নি (workflow ধাপ ৪ -> ৫)।
    """

    serializer_class = MRIScanSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        return MRIScan.objects.filter(
            radiologist_review__isnull=False, doctor_consultation__isnull=True
        ).order_by("radiologist_review__reviewed_at")


class ScanConsultCreateView(APIView):
    """
    POST /api/scans/<scan_id>/consult/
    Doctor একটা নির্দিষ্ট scan-এর জন্য চূড়ান্ত ক্লিনিক্যাল মূল্যায়ন ও
    চিকিৎসা পরামর্শ জমা দেয়।
    """

    permission_classes = [IsDoctor]

    def post(self, request, scan_id):
        scan = get_object_or_404(MRIScan, id=scan_id)

        # Radiologist review ছাড়া doctor consultation করা যাবে না
        # (workflow-এর ক্রম মেনে চলার জন্য)
        if not hasattr(scan, "radiologist_review"):
            return Response(
                {"error": "এই scan-টার radiologist review এখনো হয়নি।"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # একটা scan-এ ইতিমধ্যে consultation থাকলে দ্বিতীয়বার করা যাবে না
        if hasattr(scan, "doctor_consultation"):
            return Response(
                {"error": "এই scan-টা ইতিমধ্যে consult করা হয়ে গেছে।"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DoctorConsultationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(scan=scan, doctor=request.user)

        response_serializer = MRIScanSerializer(scan)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
import os
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from accounts.permissions import IsPatient

from .models import MRIScan, AIAnalysisResult
from .serializers import MRIScanSerializer, ScanUploadSerializer
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

import os
from PIL import Image
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from accounts.permissions import (
    IsPatient,
    IsRadiologist,
    IsDoctor,
    IsRadiologistOrDoctor,
    IsAdminRole,
)
from accounts.models import User

from .models import (
    MRIScan,
    AIAnalysisResult,
    RadiologistReview,
    DoctorConsultation,
    FinalReport,
    Appointment,
    AuditLog,
)
from .serializers import (
    MRIScanSerializer,
    ScanUploadSerializer,
    RadiologistReviewCreateSerializer,
    DoctorConsultationCreateSerializer,
    FinalReportCreateSerializer,
    AppointmentSerializer,
)
from .inference import predict_tumor, predict_segmentation
from . import llm_service


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

        # --- অটো-কনভার্সন লজিক (.tif থেকে .png তে কনভার্ট) ---
        img_path = scan.original_image.path
        try:
            if img_path.lower().endswith(".tif") or img_path.lower().endswith(".tiff"):
                img = Image.open(img_path)
                if img.mode != "RGB":
                    img = img.convert("RGB")

                new_path = img_path.rsplit(".", 1)[0] + ".png"
                img.save(new_path, "PNG")

                os.remove(img_path)

                scan.original_image.name = (
                    scan.original_image.name.rsplit(".", 1)[0] + ".png"
                )
                scan.save()
                img_path = new_path
        except Exception as e:
            return Response(
                {"error": f"Image conversion failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ১. Classification
        try:
            result = predict_tumor(img_path)
        except Exception as e:
            return Response(
                {"error": f"Classification failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ২. Segmentation
        seg_result = None
        try:
            mask_dir = os.path.join(settings.MEDIA_ROOT, "scans", "masks")
            os.makedirs(mask_dir, exist_ok=True)
            seg_result = predict_segmentation(img_path, mask_dir)
        except Exception as e:
            seg_result = None

        # ৩. Review প্রয়োজন কিনা যাচাই করি
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
        response_serializer = MRIScanSerializer(scan, context={"request": request})
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
    """

    permission_classes = [IsRadiologist]

    def post(self, request, scan_id):
        scan = get_object_or_404(MRIScan, id=scan_id)

        if hasattr(scan, "radiologist_review"):
            return Response(
                {"error": "এই scan-টা ইতিমধ্যে review করা হয়ে গেছে।"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RadiologistReviewCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(scan=scan, radiologist=request.user)

        response_serializer = MRIScanSerializer(scan, context={"request": request})
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

        if not hasattr(scan, "radiologist_review"):
            return Response(
                {"error": "এই scan-টার radiologist review এখনো হয়নি।"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if hasattr(scan, "doctor_consultation"):
            return Response(
                {"error": "এই scan-টা ইতিমধ্যে consult করা হয়ে গেছে।"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DoctorConsultationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(scan=scan, doctor=request.user)

        response_serializer = MRIScanSerializer(scan, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class GenerateReportView(APIView):
    """
    POST /api/scans/<scan_id>/generate-report/
    Doctor consultation হয়ে যাওয়ার পর, doctor এখান থেকে চূড়ান্ত রিপোর্ট তৈরি করে
    (status='draft' -- এখনো patient দেখতে পাবে না, আগে approve করতে হবে)।
    """

    permission_classes = [IsDoctor]

    def post(self, request, scan_id):
        scan = get_object_or_404(MRIScan, id=scan_id)

        if not hasattr(scan, "doctor_consultation"):
            return Response(
                {"error": "এই scan-টার doctor consultation এখনো হয়নি।"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if hasattr(scan, "final_report"):
            return Response(
                {"error": "এই scan-এর জন্য final report ইতিমধ্যে তৈরি হয়ে গেছে।"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = FinalReportCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        radiologist_review = getattr(scan, "radiologist_review", None)
        if radiologist_review and radiologist_review.corrected_classification:
            final_diagnosis = radiologist_review.corrected_classification
        else:
            final_diagnosis = scan.analysis.classification

        serializer.save(
            scan=scan,
            generated_by=request.user,
            final_diagnosis=final_diagnosis,
            status="draft",
        )

        response_serializer = MRIScanSerializer(scan, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ApproveReportView(APIView):
    """
    POST /api/scans/<scan_id>/approve-report/
    Draft report-কে approve করে -- এর পরেই শুধু patient এই report দেখতে পারবে।
    """

    permission_classes = [IsDoctor]

    def post(self, request, scan_id):
        scan = get_object_or_404(MRIScan, id=scan_id)

        if not hasattr(scan, "final_report"):
            return Response(
                {"error": "এই scan-এর জন্য এখনো কোনো final report তৈরি হয়নি।"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        report = scan.final_report
        if report.status == "approved":
            return Response(
                {"error": "এই report ইতিমধ্যে approved।"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        report.status = "approved"
        report.approved_by = request.user
        report.approved_at = timezone.now()
        report.save()

        AuditLog.objects.create(
            user=request.user,
            scan=scan,
            action="approve_report",
            details=f"Report approved for scan {scan.id} with diagnosis {report.final_diagnosis}",
        )

        response_serializer = MRIScanSerializer(scan, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)


# ===========================================================================
# LLM Clinical Assistant endpoints (Gemini-powered)
# ===========================================================================


class ClinicalSummaryView(APIView):
    permission_classes = [IsRadiologistOrDoctor]

    def get(self, request, scan_id):
        scan = get_object_or_404(MRIScan, id=scan_id)
        if not hasattr(scan, "analysis"):
            return Response(
                {"error": "এই scan-এর জন্য এখনো কোনো AI analysis নেই।"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            summary = llm_service.generate_clinical_summary(scan)
        except Exception as e:
            return Response(
                {"error": f"Clinical summary তৈরি করা যায়নি: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"summary": summary}, status=status.HTTP_200_OK)


class InterpretResultView(APIView):
    permission_classes = [IsRadiologistOrDoctor]

    def get(self, request, scan_id):
        scan = get_object_or_404(MRIScan, id=scan_id)
        if not hasattr(scan, "analysis"):
            return Response(
                {"error": "এই scan-এর জন্য এখনো কোনো AI analysis নেই।"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            interpretation = llm_service.interpret_ai_result(scan)
        except Exception as e:
            return Response(
                {"error": f"Result interpretation তৈরি করা যায়নি: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"interpretation": interpretation}, status=status.HTTP_200_OK)


class DraftReportView(APIView):
    permission_classes = [IsDoctor]

    def get(self, request, scan_id):
        scan = get_object_or_404(MRIScan, id=scan_id)
        if not hasattr(scan, "doctor_consultation"):
            return Response(
                {"error": "এই scan-টার doctor consultation এখনো হয়নি।"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            draft = llm_service.draft_final_report_text(scan)
        except Exception as e:
            return Response(
                {"error": f"Draft report তৈরি করা যায়নি: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"draft": draft}, status=status.HTTP_200_OK)


class CompareProgressionView(APIView):
    permission_classes = [IsRadiologistOrDoctor]

    def get(self, request, scan_id, other_scan_id):
        current_scan = get_object_or_404(MRIScan, id=scan_id)
        previous_scan = get_object_or_404(MRIScan, id=other_scan_id)

        if current_scan.patient_id != previous_scan.patient_id:
            return Response(
                {"error": "দুইটা scan একই patient-এর না -- তুলনা করা যাবে না।"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not hasattr(current_scan, "analysis") or not hasattr(
            previous_scan, "analysis"
        ):
            return Response(
                {"error": "দুইটা scan-এরই AI analysis থাকা দরকার তুলনার জন্য।"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if current_scan.uploaded_at < previous_scan.uploaded_at:
            current_scan, previous_scan = previous_scan, current_scan

        try:
            comparison = llm_service.compare_scan_progression(
                current_scan, previous_scan
            )
        except Exception as e:
            return Response(
                {"error": f"Comparison তৈরি করা যায়নি: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"comparison": comparison}, status=status.HTTP_200_OK)


class AskMedicalQuestionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, scan_id):
        scan = get_object_or_404(MRIScan, id=scan_id)

        if request.user.role == "patient":
            if scan.patient_id != request.user.id:
                return Response(
                    {"error": "শুধু নিজের scan সম্পর্কে প্রশ্ন করা যাবে।"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if (
                not hasattr(scan, "final_report")
                or scan.final_report.status != "approved"
            ):
                return Response(
                    {"error": "রিপোর্ট approved হওয়ার আগে প্রশ্ন করা যাবে না।"},
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif request.user.role not in ("radiologist", "doctor"):
            return Response(
                {
                    "error": "শুধু patient (নিজের scan) অথবা radiologist/doctor প্রশ্ন করতে পারবে।"
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        question = request.data.get("question", "").strip()
        if not question:
            return Response(
                {"error": "question ফিল্ড খালি রাখা যাবে না।"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not hasattr(scan, "analysis"):
            return Response(
                {"error": "এই scan-এর জন্য এখনো কোনো AI analysis নেই।"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            answer = llm_service.answer_medical_question(scan, question)
        except Exception as e:
            return Response(
                {"error": f"উত্তর তৈরি করা যায়নি: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            {"question": question, "answer": answer}, status=status.HTTP_200_OK
        )


class FollowUpRecommendationsView(APIView):
    permission_classes = [IsDoctor]

    def get(self, request, scan_id):
        scan = get_object_or_404(MRIScan, id=scan_id)
        if not hasattr(scan, "final_report"):
            return Response(
                {"error": "এই scan-এর জন্য এখনো কোনো final report তৈরি হয়নি।"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            recommendations = llm_service.suggest_follow_up_recommendations(scan)
        except Exception as e:
            return Response(
                {"error": f"Follow-up সাজেশন তৈরি করা যায়নি: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"recommendations": recommendations}, status=status.HTTP_200_OK)


class PatientExplanationView(APIView):
    permission_classes = [IsPatient]

    def get(self, request, scan_id):
        scan = get_object_or_404(MRIScan, id=scan_id)
        if scan.patient_id != request.user.id:
            return Response(
                {"error": "শুধু নিজের scan-এর ব্যাখ্যা দেখা যাবে।"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not hasattr(scan, "final_report") or scan.final_report.status != "approved":
            return Response(
                {
                    "error": "রিপোর্ট এখনো approved হয়নি -- ব্যাখ্যা এখনো পাওয়া যাবে না।"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            explanation = llm_service.generate_patient_friendly_explanation(scan)
        except Exception as e:
            return Response(
                {"error": f"ব্যাখ্যা তৈরি করা যায়নি: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"explanation": explanation}, status=status.HTTP_200_OK)


class AdminDashboardStatsView(APIView):
    """
    GET /api/scans/admin-stats/
    শুধু Admin বা Super Admin দেখতে পারবে।
    """

    permission_classes = [IsAdminRole]

    def get(self, request):
        stats = {
            "total_patients": User.objects.filter(role="patient").count(),
            "total_radiologists": User.objects.filter(role="radiologist").count(),
            "total_doctors": User.objects.filter(role="doctor").count(),
            "total_scans": MRIScan.objects.count(),
            "pending_reviews": MRIScan.objects.filter(
                analysis__needs_review=True, radiologist_review__isnull=True
            ).count(),
            "approved_reports": FinalReport.objects.filter(status="approved").count(),
        }
        return Response(stats, status=status.HTTP_200_OK)


class BookAppointmentView(APIView):
    """
    POST /api/scans/<scan_id>/book-appointment/
    Patient তার অনুমোদিত রিপোর্টের জন্য ডাক্তারের সাথে ফলো-আপ অ্যাপয়েন্টমেন্ট বুক করবে।
    """

    permission_classes = [IsPatient]

    def post(self, request, scan_id):
        scan = get_object_or_404(MRIScan, id=scan_id, patient=request.user)

        if not hasattr(scan, "final_report") or scan.final_report.status != "approved":
            return Response(
                {
                    "error": "শুধুমাত্র অনুমোদিত (approved) রিপোর্টের জন্য ফলো-আপ বুক করা যাবে।"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AppointmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        doctor_id = request.data.get("doctor")
        try:
            doctor = User.objects.get(id=doctor_id, role="doctor")
        except User.DoesNotExist:
            return Response(
                {"error": "এই আইডির কোনো ডাক্তার পাওয়া যায়নি।"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer.save(
            scan=scan, patient=request.user, doctor=doctor, status="scheduled"
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdminScanListView(generics.ListAPIView):
    """
    GET /api/scans/admin-scans/?status=all
    GET /api/scans/admin-scans/?status=pending
    শুধু Admin বা Super Admin সব স্ক্যান বা পেন্ডিং স্ক্যান দেখতে পারবে।
    """

    serializer_class = MRIScanSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        queryset = MRIScan.objects.all().order_by("-uploaded_at")
        status = self.request.query_params.get("status")
        if status == "pending":
            queryset = queryset.filter(
                analysis__needs_review=True, radiologist_review__isnull=True
            )
        return queryset


class AdminScanDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/scans/admin-scans/<id>/
    PATCH /api/scans/admin-scans/<id>/ (ছবি এডিট করার জন্য)
    DELETE /api/scans/admin-scans/<id>/ (স্ক্যান ডিলিট করার জন্য)
    """

    queryset = MRIScan.objects.all()
    serializer_class = MRIScanSerializer
    permission_classes = [IsAdminRole]

    def perform_update(self, serializer):
        instance = serializer.save()

        # --- অটো-কনভার্সন লজিক (.tif থেকে .png তে কনভার্ট) ---
        img_path = instance.original_image.path
        try:
            if img_path.lower().endswith(".tif") or img_path.lower().endswith(".tiff"):
                img = Image.open(img_path)
                if img.mode != "RGB":
                    img = img.convert("RGB")

                new_path = img_path.rsplit(".", 1)[0] + ".png"
                img.save(new_path, "PNG")

                os.remove(img_path)

                instance.original_image.name = (
                    instance.original_image.name.rsplit(".", 1)[0] + ".png"
                )
                instance.save()
        except Exception as e:
            pass


class PatientScanDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    PATCH /api/scans/my-scans/<id>/ (পেশেন্ট নিজের ছবি এডিট করবে)
    DELETE /api/scans/my-scans/<id>/ (পেশেন্ট নিজের স্ক্যান ডিলিট করবে)
    """

    serializer_class = MRIScanSerializer
    permission_classes = [IsPatient]

    def get_queryset(self):
        return MRIScan.objects.filter(patient=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()

        # --- অটো-কনভার্সন লজিক (.tif থেকে .png তে কনভার্ট) ---
        img_path = instance.original_image.path
        try:
            if img_path.lower().endswith(".tif") or img_path.lower().endswith(".tiff"):
                img = Image.open(img_path)
                if img.mode != "RGB":
                    img = img.convert("RGB")

                new_path = img_path.rsplit(".", 1)[0] + ".png"
                img.save(new_path, "PNG")

                os.remove(img_path)

                instance.original_image.name = (
                    instance.original_image.name.rsplit(".", 1)[0] + ".png"
                )
                instance.save()
        except Exception as e:
            pass

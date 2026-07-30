import os
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
)

from .models import (
    MRIScan,
    AIAnalysisResult,
    RadiologistReview,
    DoctorConsultation,
    FinalReport,
    Appointment 
)
from .serializers import (
    MRIScanSerializer,
    ScanUploadSerializer,
    RadiologistReviewCreateSerializer,
    DoctorConsultationCreateSerializer,
    FinalReportCreateSerializer,
    AppointmentSerializer
)
from .inference import predict_tumor, predict_segmentation
from . import llm_service
from .models import AuditLog
from accounts.models import User
from accounts.permissions import IsAdminRole


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

        response_serializer = MRIScanSerializer(scan, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class GenerateReportView(APIView):
    """
    POST /api/scans/<scan_id>/generate-report/
    Doctor consultation হয়ে যাওয়ার পর, doctor এখান থেকে চূড়ান্ত রিপোর্ট তৈরি করে
    (status='draft' -- এখনো patient দেখতে পাবে না, আগে approve করতে হবে)।

    final_diagnosis auto-নির্ধারিত হয়: radiologist-এর corrected_classification
    থাকলে সেটা, নাহলে AI-এর classification।
    """

    permission_classes = [IsDoctor]

    def post(self, request, scan_id):
        scan = get_object_or_404(MRIScan, id=scan_id)

        # Doctor consultation ছাড়া final report generate করা যাবে না
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

        # final_diagnosis নির্ধারণ: radiologist-এর সংশোধন থাকলে সেটাই চূড়ান্ত ধরা হয়
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
    Draft report-কে approve করে -- এর পরেই শুধু patient এই report দেখতে পারবে
    ("Only the Final Approved Report is delivered to the Patient")।
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

        # --- এই লাইনটি যুক্ত করুন ---
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
#
# সবগুলোতেই একটা common প্যাটার্ন: llm_service ফাংশন কল করা try/except-এ মোড়া
# থাকে, কারণ এটা একটা বাইরের API কল (network issue, rate limit, ইত্যাদি হতে
# পারে) -- ব্যর্থ হলে পুরো request 500 করে দেওয়া হয় স্পষ্ট error message সহ।
# ===========================================================================


class ClinicalSummaryView(APIView):
    """
    GET /api/scans/<scan_id>/clinical-summary/
    Radiologist/Doctor -- এখন পর্যন্ত scan-এ যা রেকর্ড হয়েছে তার সংক্ষিপ্ত
    ক্লিনিক্যাল সামারি (LLM Clinical Assistant ফিচার ১)।
    """

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
    """
    GET /api/scans/<scan_id>/interpret-result/
    Radiologist/Doctor -- AI classification/segmentation ফলাফলের ক্লিনিক্যাল
    ব্যাখ্যা (LLM Clinical Assistant ফিচার ২)।
    """

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
    """
    GET /api/scans/<scan_id>/draft-report/
    Doctor -- doctor consultation হয়ে যাওয়ার পর final report-এর জন্য একটা
    LLM-generated draft (LLM Clinical Assistant ফিচার ৩)। এটা শুধু একটা
    starting point -- doctor edit করে generate-report endpoint-এ পাঠাবে,
    এটা নিজে থেকে কোনো report সেভ করে না।
    """

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
    """
    GET /api/scans/<scan_id>/compare/<other_scan_id>/
    Radiologist/Doctor -- একই patient-এর দুইটা scan-এর মধ্যে tumor
    progression তুলনা (LLM Clinical Assistant ফিচার ৪)।
    """

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
        # current_scan সবসময় পরের scan হওয়া উচিত -- না হলে swap করে নিচ্ছি
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
    """
    POST /api/scans/<scan_id>/ask/  { "question": "..." }
    Patient (শুধু নিজের scan, রিপোর্ট approved হলে) অথবা Radiologist/Doctor
    (যেকোনো scan) -- scan-এর ডেটার ভিত্তিতে প্রশ্নের উত্তর (LLM Clinical
    Assistant ফিচার ৫: Medical Q&A)।
    """

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
    """
    GET /api/scans/<scan_id>/follow-up-recommendations/
    Doctor -- final report-এর ভিত্তিতে সম্ভাব্য follow-up পদক্ষেপের সাজেশন
    (LLM Clinical Assistant ফিচার ৬)। এগুলো শুধু সাজেশন -- doctor নিজে
    যাচাই করে গ্রহণ/বাতিল করবে।
    """

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
    """
    GET /api/scans/<scan_id>/explanation/
    Patient -- শুধু নিজের scan, এবং শুধু final report approved হলেই সহজ ভাষায়
    ব্যাখ্যা পাওয়া যাবে (LLM Clinical Assistant ফিচার ৭: Patient Friendly
    Explanation) -- ঠিক "Only the Final Approved Report is delivered to the
    Patient" নিয়ম অনুযায়ী।
    """

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

    permission_classes = [IsAdminRole]  # <--- এখানেও IsAdminRole হবে

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

        # রিপোর্ট অ্যাপ্রুভড না হলে অ্যাপয়েন্টমেন্ট করা যাবে না
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

        # ক্লায়েন্ট কোন ডাক্তারের আইডি দিয়েছে তা চেক করা
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

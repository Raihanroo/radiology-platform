"""
scans app-এর জন্য টেস্ট স্যুট -- পুরো clinical workflow কভার করে:

    upload/analyze -> radiologist review -> doctor consultation
    -> generate report -> approve report -> patient access

গুরুত্বপূর্ণ ডিজাইন সিদ্ধান্ত:
- ML মডেল (classifier/segmentation) আসলে লোড না করে predict_tumor/predict_segmentation
  mock করা হয়েছে। এতে টেস্ট দ্রুত চলে এবং ML weight ফাইলের উপর নির্ভর করে না --
  এই টেস্টগুলোর উদ্দেশ্য business logic/permission/workflow যাচাই করা, model accuracy না।
- media ফাইল আসল filesystem-এ না লিখে override_settings দিয়ে temp ডিরেক্টরিতে লেখা হয়,
  যাতে টেস্ট রান শেষে media/ ফোল্ডার নোংরা না হয়।
"""

import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from django.urls import reverse
from django.test import override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from .models import MRIScan, AIAnalysisResult, RadiologistReview, FinalReport

MEDIA_ROOT = tempfile.mkdtemp()


def make_test_image():
    """ScanUploadSerializer-এর ImageField পাশ করার জন্য একটা ছোট বৈধ PNG তৈরি করে।"""
    buf = BytesIO()
    Image.new("RGB", (32, 32), color=(120, 120, 120)).save(buf, format="PNG")
    buf.seek(0)
    buf.name = "test_scan.png"
    return buf


MOCK_CLASSIFICATION_RESULT = {"classification": "glioma", "confidence": 92.4}
MOCK_NO_TUMOR_RESULT = {"classification": "notumor", "confidence": 88.0}
MOCK_SEGMENTATION_RESULT_LOW = {
    "mask_filename": "mask.png",
    "overlay_filename": "overlay.png",
    "tumor_area_pixels": 10,
    "tumor_area_percentage": 0.1,
}
MOCK_SEGMENTATION_RESULT_HIGH = {
    "mask_filename": "mask.png",
    "overlay_filename": "overlay.png",
    "tumor_area_pixels": 5000,
    "tumor_area_percentage": 5.0,
}


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class BaseScanTestCase(APITestCase):
    """সব scan টেস্টের জন্য common ইউজার সেটআপ।"""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.patient = User.objects.create_user(
            username="patient1", password="x", role="patient"
        )
        self.other_patient = User.objects.create_user(
            username="patient2", password="x", role="patient"
        )
        self.radiologist = User.objects.create_user(
            username="radio1", password="x", role="radiologist"
        )
        self.other_radiologist = User.objects.create_user(
            username="radio2", password="x", role="radiologist"
        )
        self.doctor = User.objects.create_user(
            username="doc1", password="x", role="doctor"
        )
        self.admin = User.objects.create_user(
            username="admin1", password="x", role="admin"
        )


class ScanUploadPermissionTests(BaseScanTestCase):
    """
    workflow ধাপ ১: শুধু patient নিজের scan upload/analyze করতে পারবে
    (আগের commit history অনুযায়ী -- এটা explicit ভাবে fix করা একটা security gap)।
    """

    def setUp(self):
        super().setUp()
        self.url = reverse("scan-analyze")

    @patch(
        "scans.views.predict_segmentation", return_value=MOCK_SEGMENTATION_RESULT_LOW
    )
    @patch("scans.views.predict_tumor", return_value=MOCK_CLASSIFICATION_RESULT)
    def test_patient_can_upload_and_analyze(self, mock_predict, mock_seg):
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(
            self.url,
            {"original_image": make_test_image(), "scan_type": "MRI"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["analysis"]["classification"], "glioma")

    def test_radiologist_cannot_upload(self):
        self.client.force_authenticate(user=self.radiologist)
        response = self.client.post(
            self.url,
            {"original_image": make_test_image(), "scan_type": "MRI"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_doctor_cannot_upload(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(
            self.url,
            {"original_image": make_test_image(), "scan_type": "MRI"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_upload(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            self.url,
            {"original_image": make_test_image(), "scan_type": "MRI"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_upload(self):
        response = self.client.post(
            self.url,
            {"original_image": make_test_image(), "scan_type": "MRI"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(
        "scans.views.predict_segmentation", return_value=MOCK_SEGMENTATION_RESULT_LOW
    )
    @patch("scans.views.predict_tumor", return_value=MOCK_CLASSIFICATION_RESULT)
    def test_scan_always_belongs_to_uploading_patient(self, mock_predict, mock_seg):
        """
        ScanUploadSerializer-এ patient ফিল্ড ইচ্ছাকৃতভাবে বাদ, তাই client এই ফিল্ড
        পাঠানোর চেষ্টা করলেও (অন্য patient-এর নামে scan বসানোর চেষ্টা) সেটা কাজ করবে না --
        view সবসময় patient=request.user সেট করে।
        """
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(
            self.url,
            {
                "original_image": make_test_image(),
                "scan_type": "MRI",
                "patient": self.other_patient.id,  # স্পুফ করার চেষ্টা
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        scan = MRIScan.objects.get(id=response.data["id"])
        self.assertEqual(scan.patient, self.patient)
        self.assertNotEqual(scan.patient, self.other_patient)


class NeedsReviewLogicTests(BaseScanTestCase):
    """
    workflow-এর গুরুত্বপূর্ণ safety-net: classifier 'notumor' বললেও segmentation
    উল্লেখযোগ্য (>1%) tumor area পেলে needs_review=True হবে -- দুই মডেলের
    দ্বন্দ্ব ধরার জন্য এই cross-check।
    """

    def setUp(self):
        super().setUp()
        self.url = reverse("scan-analyze")
        self.client.force_authenticate(user=self.patient)

    @patch(
        "scans.views.predict_segmentation", return_value=MOCK_SEGMENTATION_RESULT_HIGH
    )
    @patch("scans.views.predict_tumor", return_value=MOCK_NO_TUMOR_RESULT)
    def test_conflicting_results_flagged_for_review(self, mock_predict, mock_seg):
        response = self.client.post(
            self.url,
            {"original_image": make_test_image(), "scan_type": "MRI"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["analysis"]["needs_review"])

    @patch(
        "scans.views.predict_segmentation", return_value=MOCK_SEGMENTATION_RESULT_LOW
    )
    @patch("scans.views.predict_tumor", return_value=MOCK_NO_TUMOR_RESULT)
    def test_agreeing_results_not_flagged(self, mock_predict, mock_seg):
        """notumor + সামান্য (<1%) segmentation area -- এটা দ্বন্দ্ব না, review লাগবে না।"""
        response = self.client.post(
            self.url,
            {"original_image": make_test_image(), "scan_type": "MRI"},
            format="multipart",
        )
        self.assertFalse(response.data["analysis"]["needs_review"])

    @patch(
        "scans.views.predict_segmentation", return_value=MOCK_SEGMENTATION_RESULT_HIGH
    )
    @patch("scans.views.predict_tumor", return_value=MOCK_CLASSIFICATION_RESULT)
    def test_tumor_classification_not_flagged_regardless_of_area(
        self, mock_predict, mock_seg
    ):
        """classifier আগে থেকেই tumor বললে needs_review flag লাগার কথা না (dedicated conflict-check শুধু notumor কেসের জন্য)।"""
        response = self.client.post(
            self.url,
            {"original_image": make_test_image(), "scan_type": "MRI"},
            format="multipart",
        )
        self.assertFalse(response.data["analysis"]["needs_review"])


class WorkflowQueueTests(BaseScanTestCase):
    """review-queue / consultation-queue endpoint-গুলো সঠিক scan-ই দেখায় কিনা।"""

    def _upload_scan(
        self, classification="glioma", confidence=90.0, needs_review=False
    ):
        scan = MRIScan.objects.create(
            patient=self.patient,
            uploaded_by=self.patient,
            original_image="scans/original/x.png",
        )
        AIAnalysisResult.objects.create(
            scan=scan,
            classification=classification,
            confidence_score=confidence,
            needs_review=needs_review,
        )
        return scan

    def test_review_queue_only_shows_flagged_unreviewed_scans(self):
        flagged_scan = self._upload_scan(needs_review=True)
        self._upload_scan(needs_review=False)  # flagged না, queue-তে থাকার কথা না

        reviewed_scan = self._upload_scan(needs_review=True)
        RadiologistReview.objects.create(
            scan=reviewed_scan, radiologist=self.radiologist, status="approved"
        )  # ইতিমধ্যে review হয়ে গেছে, queue-তে থাকার কথা না

        self.client.force_authenticate(user=self.radiologist)
        response = self.client.get(reverse("scan-review-queue"))
        ids = [item["id"] for item in response.data]

        self.assertIn(flagged_scan.id, ids)
        self.assertEqual(len(ids), 1)

    def test_review_queue_forbidden_for_non_radiologist(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.get(reverse("scan-review-queue"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_consultation_queue_requires_review_but_not_consultation(self):
        scan = self._upload_scan()
        RadiologistReview.objects.create(
            scan=scan, radiologist=self.radiologist, status="approved"
        )
        not_reviewed_scan = (
            self._upload_scan()
        )  # review হয়নি, consultation queue-তে আসার কথা না

        self.client.force_authenticate(user=self.doctor)
        response = self.client.get(reverse("scan-consultation-queue"))
        ids = [item["id"] for item in response.data]

        self.assertIn(scan.id, ids)
        self.assertNotIn(not_reviewed_scan.id, ids)


class RadiologistReviewCreateTests(BaseScanTestCase):
    def setUp(self):
        super().setUp()
        self.scan = MRIScan.objects.create(
            patient=self.patient,
            uploaded_by=self.patient,
            original_image="scans/original/x.png",
        )
        AIAnalysisResult.objects.create(
            scan=self.scan,
            classification="glioma",
            confidence_score=90.0,
            needs_review=True,
        )
        self.url = reverse("scan-review-create", args=[self.scan.id])

    def test_radiologist_can_submit_review(self):
        self.client.force_authenticate(user=self.radiologist)
        response = self.client.post(
            self.url,
            {"status": "approved", "observations": "AI ফলাফল ঠিক আছে।"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            hasattr(self.scan, "radiologist_review")
            or RadiologistReview.objects.filter(scan=self.scan).exists()
        )

    def test_review_cannot_be_submitted_twice(self):
        self.client.force_authenticate(user=self.radiologist)
        self.client.post(self.url, {"status": "approved"}, format="json")
        response = self.client.post(self.url, {"status": "rejected"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(RadiologistReview.objects.filter(scan=self.scan).count(), 1)

    def test_patient_cannot_submit_review(self):
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(self.url, {"status": "approved"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class DoctorConsultationCreateTests(BaseScanTestCase):
    def setUp(self):
        super().setUp()
        self.scan = MRIScan.objects.create(
            patient=self.patient,
            uploaded_by=self.patient,
            original_image="scans/original/x.png",
        )
        AIAnalysisResult.objects.create(
            scan=self.scan, classification="glioma", confidence_score=90.0
        )
        self.url = reverse("scan-consult-create", args=[self.scan.id])

    def test_consultation_blocked_without_radiologist_review(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(
            self.url, {"clinical_assessment": "মূল্যায়ন"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_consultation_allowed_after_review(self):
        RadiologistReview.objects.create(
            scan=self.scan, radiologist=self.radiologist, status="approved"
        )
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(
            self.url,
            {
                "clinical_assessment": "সবকিছু স্বাভাবিক দেখাচ্ছে।",
                "treatment_recommendation": "৩ মাস পর ফলো-আপ।",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_consultation_cannot_be_submitted_twice(self):
        RadiologistReview.objects.create(
            scan=self.scan, radiologist=self.radiologist, status="approved"
        )
        self.client.force_authenticate(user=self.doctor)
        self.client.post(self.url, {"clinical_assessment": "প্রথমবার"}, format="json")
        response = self.client.post(
            self.url, {"clinical_assessment": "দ্বিতীয়বার"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class FinalReportWorkflowTests(BaseScanTestCase):
    """
    সবচেয়ে গুরুত্বপূর্ণ security টেস্ট এখানে: draft report patient দেখতে পারবে না,
    approve করার পরেই দেখতে পারবে ("Only the Final Approved Report is delivered
    to the Patient")।
    """

    def setUp(self):
        super().setUp()
        self.scan = MRIScan.objects.create(
            patient=self.patient,
            uploaded_by=self.patient,
            original_image="scans/original/x.png",
        )
        AIAnalysisResult.objects.create(
            scan=self.scan, classification="glioma", confidence_score=90.0
        )
        RadiologistReview.objects.create(
            scan=self.scan, radiologist=self.radiologist, status="approved"
        )
        from .models import DoctorConsultation

        DoctorConsultation.objects.create(
            scan=self.scan, doctor=self.doctor, clinical_assessment="ঠিক আছে।"
        )
        self.generate_url = reverse("scan-generate-report", args=[self.scan.id])
        self.approve_url = reverse("scan-approve-report", args=[self.scan.id])
        self.my_scans_url = reverse("scan-my-list")

    def test_generate_report_blocked_without_consultation(self):
        scan2 = MRIScan.objects.create(
            patient=self.patient,
            uploaded_by=self.patient,
            original_image="scans/original/y.png",
        )
        AIAnalysisResult.objects.create(
            scan=scan2, classification="glioma", confidence_score=90.0
        )
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(
            reverse("scan-generate-report", args=[scan2.id]),
            {"summary": "সারসংক্ষেপ"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_report_creates_draft(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(
            self.generate_url, {"summary": "রোগীর অবস্থা স্থিতিশীল।"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        report = FinalReport.objects.get(scan=self.scan)
        self.assertEqual(report.status, "draft")

    def test_final_diagnosis_prefers_radiologist_correction(self):
        """radiologist-এর corrected_classification থাকলে সেটাই final_diagnosis হবে, AI-এরটা না।"""
        review = self.scan.radiologist_review
        review.corrected_classification = "meningioma"
        review.save()

        self.client.force_authenticate(user=self.doctor)
        self.client.post(self.generate_url, {"summary": "সারসংক্ষেপ"}, format="json")

        report = FinalReport.objects.get(scan=self.scan)
        self.assertEqual(report.final_diagnosis, "meningioma")

    def test_report_cannot_be_generated_twice(self):
        self.client.force_authenticate(user=self.doctor)
        self.client.post(self.generate_url, {"summary": "প্রথম"}, format="json")
        response = self.client.post(
            self.generate_url, {"summary": "দ্বিতীয়"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_draft_report_hidden_from_patient(self):
        self.client.force_authenticate(user=self.doctor)
        self.client.post(
            self.generate_url, {"summary": "খসড়া সারসংক্ষেপ"}, format="json"
        )

        self.client.force_authenticate(user=self.patient)
        response = self.client.get(self.my_scans_url)
        scan_data = next(s for s in response.data if s["id"] == self.scan.id)
        self.assertIsNone(scan_data["final_report"])

    def test_draft_report_visible_to_doctor_and_radiologist(self):
        self.client.force_authenticate(user=self.doctor)
        self.client.post(
            self.generate_url, {"summary": "খসড়া সারসংক্ষেপ"}, format="json"
        )

        # doctor-এর নিজস্ব "list" endpoint নেই, তাই radiologist-এর
        # reviewed-by-me endpoint দিয়ে serializer-এর role-aware আচরণ যাচাই করি
        self.client.force_authenticate(user=self.radiologist)
        response = self.client.get(reverse("scan-reviewed-by-me"))
        scan_data = next(s for s in response.data if s["id"] == self.scan.id)
        self.assertIsNotNone(scan_data["final_report"])
        self.assertEqual(scan_data["final_report"]["status"], "draft")

    def test_approved_report_visible_to_patient(self):
        self.client.force_authenticate(user=self.doctor)
        self.client.post(self.generate_url, {"summary": "খসড়া"}, format="json")
        self.client.post(self.approve_url, {}, format="json")

        self.client.force_authenticate(user=self.patient)
        response = self.client.get(self.my_scans_url)
        scan_data = next(s for s in response.data if s["id"] == self.scan.id)
        self.assertIsNotNone(scan_data["final_report"])
        self.assertEqual(scan_data["final_report"]["status"], "approved")

    def test_report_cannot_be_approved_twice(self):
        self.client.force_authenticate(user=self.doctor)
        self.client.post(self.generate_url, {"summary": "খসড়া"}, format="json")
        self.client.post(self.approve_url, {}, format="json")
        response = self.client.post(self.approve_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approve_blocked_without_draft_report(self):
        scan2 = MRIScan.objects.create(
            patient=self.patient,
            uploaded_by=self.patient,
            original_image="scans/original/z.png",
        )
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(
            reverse("scan-approve-report", args=[scan2.id]), {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class FullEndToEndWorkflowTest(BaseScanTestCase):
    """
    ইনফোগ্রাফিকের Complete Workflow (ধাপ ১-৬) পুরোপুরি একটা টেস্টে
    end-to-end চালিয়ে যাচাই করে যে পুরো চেইন একসাথে কাজ করে।
    """

    @patch(
        "scans.views.predict_segmentation", return_value=MOCK_SEGMENTATION_RESULT_HIGH
    )
    @patch("scans.views.predict_tumor", return_value=MOCK_CLASSIFICATION_RESULT)
    def test_full_patient_to_approved_report_flow(self, mock_predict, mock_seg):
        # ১. Patient uploads + AI analyzes
        self.client.force_authenticate(user=self.patient)
        upload_response = self.client.post(
            reverse("scan-analyze"),
            {"original_image": make_test_image(), "scan_type": "MRI"},
            format="multipart",
        )
        self.assertEqual(upload_response.status_code, status.HTTP_201_CREATED)
        scan_id = upload_response.data["id"]

        # ২. Radiologist reviews
        self.client.force_authenticate(user=self.radiologist)
        review_response = self.client.post(
            reverse("scan-review-create", args=[scan_id]),
            {"status": "approved", "observations": "নিশ্চিত করা হয়েছে।"},
            format="json",
        )
        self.assertEqual(review_response.status_code, status.HTTP_201_CREATED)

        # ৩. Doctor consults
        self.client.force_authenticate(user=self.doctor)
        consult_response = self.client.post(
            reverse("scan-consult-create", args=[scan_id]),
            {
                "clinical_assessment": "চিকিৎসা প্রয়োজন।",
                "treatment_recommendation": "অনকোলজিস্ট রেফারেল।",
            },
            format="json",
        )
        self.assertEqual(consult_response.status_code, status.HTTP_201_CREATED)

        # ৪. Doctor generates + approves final report
        generate_response = self.client.post(
            reverse("scan-generate-report", args=[scan_id]),
            {"summary": "সম্পূর্ণ মূল্যায়ন শেষে চূড়ান্ত রিপোর্ট।"},
            format="json",
        )
        self.assertEqual(generate_response.status_code, status.HTTP_201_CREATED)

        approve_response = self.client.post(
            reverse("scan-approve-report", args=[scan_id]), {}, format="json"
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)

        # ৫. Patient can now see the approved final report
        self.client.force_authenticate(user=self.patient)
        my_scans_response = self.client.get(reverse("scan-my-list"))
        final_scan = next(s for s in my_scans_response.data if s["id"] == scan_id)
        self.assertEqual(final_scan["final_report"]["status"], "approved")
        self.assertIsNotNone(final_scan["final_report"]["summary"])


class LLMClinicalAssistantTests(BaseScanTestCase):
    """
    LLM Clinical Assistant-এর ৭টা ফিচারের endpoint টেস্ট। এখানে Gemini API
    আসলে কল না করে llm_service-এর প্রতিটা ফাংশন mock করা হয়েছে -- উদ্দেশ্য
    permission/workflow-state/error-handling logic যাচাই করা, LLM output-এর
    quality না (সেটা আলাদাভাবে manual/eval দিয়ে যাচাই করা উচিত)।
    """

    def setUp(self):
        super().setUp()
        self.scan = MRIScan.objects.create(
            patient=self.patient,
            uploaded_by=self.patient,
            original_image="scans/original/a.png",
        )
        AIAnalysisResult.objects.create(
            scan=self.scan,
            classification="glioma",
            confidence_score=91.0,
            tumor_area_percentage=4.2,
        )

    # ---------- Clinical Summarization ----------

    @patch(
        "scans.llm_service.generate_clinical_summary", return_value="সংক্ষিপ্ত সামারি"
    )
    def test_clinical_summary_accessible_by_radiologist_and_doctor(self, mock_llm):
        url = reverse("scan-clinical-summary", args=[self.scan.id])
        for user in (self.radiologist, self.doctor):
            self.client.force_authenticate(user=user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["summary"], "সংক্ষিপ্ত সামারি")

    def test_clinical_summary_forbidden_for_patient(self):
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(
            reverse("scan-clinical-summary", args=[self.scan.id])
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_clinical_summary_requires_analysis(self):
        bare_scan = MRIScan.objects.create(
            patient=self.patient,
            uploaded_by=self.patient,
            original_image="scans/original/b.png",
        )
        self.client.force_authenticate(user=self.doctor)
        response = self.client.get(
            reverse("scan-clinical-summary", args=[bare_scan.id])
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(
        "scans.llm_service.generate_clinical_summary",
        side_effect=Exception("Gemini timeout"),
    )
    def test_clinical_summary_llm_failure_returns_500(self, mock_llm):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.get(
            reverse("scan-clinical-summary", args=[self.scan.id])
        )
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ---------- Result Interpretation ----------

    @patch("scans.llm_service.interpret_ai_result", return_value="ব্যাখ্যা")
    def test_interpret_result_for_radiologist(self, mock_llm):
        self.client.force_authenticate(user=self.radiologist)
        response = self.client.get(
            reverse("scan-interpret-result", args=[self.scan.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["interpretation"], "ব্যাখ্যা")

    def test_interpret_result_forbidden_for_patient(self):
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(
            reverse("scan-interpret-result", args=[self.scan.id])
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---------- Report Drafting ----------

    def test_draft_report_requires_consultation(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.get(reverse("scan-draft-report", args=[self.scan.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("scans.llm_service.draft_final_report_text", return_value="Findings: ...")
    def test_draft_report_after_consultation(self, mock_llm):
        RadiologistReview.objects.create(
            scan=self.scan, radiologist=self.radiologist, status="approved"
        )
        from .models import DoctorConsultation

        DoctorConsultation.objects.create(
            scan=self.scan, doctor=self.doctor, clinical_assessment="ঠিক আছে।"
        )
        self.client.force_authenticate(user=self.doctor)
        response = self.client.get(reverse("scan-draft-report", args=[self.scan.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["draft"], "Findings: ...")

    def test_draft_report_forbidden_for_radiologist(self):
        self.client.force_authenticate(user=self.radiologist)
        response = self.client.get(reverse("scan-draft-report", args=[self.scan.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---------- Comparison & Progression ----------

    @patch(
        "scans.llm_service.compare_scan_progression", return_value="tumor area বেড়েছে"
    )
    def test_compare_progression_same_patient(self, mock_llm):
        older_scan = MRIScan.objects.create(
            patient=self.patient,
            uploaded_by=self.patient,
            original_image="scans/original/c.png",
        )
        AIAnalysisResult.objects.create(
            scan=older_scan,
            classification="glioma",
            confidence_score=80.0,
            tumor_area_percentage=2.0,
        )
        self.client.force_authenticate(user=self.radiologist)
        response = self.client.get(
            reverse("scan-compare-progression", args=[self.scan.id, older_scan.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["comparison"], "tumor area বেড়েছে")

    def test_compare_progression_rejects_different_patients(self):
        other_scan = MRIScan.objects.create(
            patient=self.other_patient,
            uploaded_by=self.other_patient,
            original_image="scans/original/d.png",
        )
        AIAnalysisResult.objects.create(
            scan=other_scan, classification="notumor", confidence_score=95.0
        )
        self.client.force_authenticate(user=self.radiologist)
        response = self.client.get(
            reverse("scan-compare-progression", args=[self.scan.id, other_scan.id])
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- Medical Q&A ----------

    def test_ask_question_patient_blocked_before_approval(self):
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(
            reverse("scan-ask-question", args=[self.scan.id]),
            {"question": "আমার টিউমারের আকার কতটুকু?"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(
        "scans.llm_service.answer_medical_question", return_value="টিউমারের আকার ৪.২%"
    )
    def test_ask_question_patient_allowed_after_approval(self, mock_llm):
        RadiologistReview.objects.create(
            scan=self.scan, radiologist=self.radiologist, status="approved"
        )
        from .models import DoctorConsultation

        DoctorConsultation.objects.create(
            scan=self.scan, doctor=self.doctor, clinical_assessment="ঠিক আছে।"
        )
        FinalReport.objects.create(
            scan=self.scan,
            final_diagnosis="glioma",
            summary="সারসংক্ষেপ",
            status="approved",
            generated_by=self.doctor,
        )
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(
            reverse("scan-ask-question", args=[self.scan.id]),
            {"question": "আমার টিউমারের আকার কতটুকু?"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["answer"], "টিউমারের আকার ৪.২%")

    def test_ask_question_patient_cannot_ask_about_others_scan(self):
        self.client.force_authenticate(user=self.other_patient)
        response = self.client.post(
            reverse("scan-ask-question", args=[self.scan.id]),
            {"question": "এটা কার scan?"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("scans.llm_service.answer_medical_question", return_value="উত্তর")
    def test_ask_question_radiologist_can_ask_anytime(self, mock_llm):
        self.client.force_authenticate(user=self.radiologist)
        response = self.client.post(
            reverse("scan-ask-question", args=[self.scan.id]),
            {"question": "confidence কেমন?"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ask_question_empty_question_rejected(self):
        self.client.force_authenticate(user=self.radiologist)
        response = self.client.post(
            reverse("scan-ask-question", args=[self.scan.id]),
            {"question": "  "},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- Follow-up Recommendations ----------

    def test_follow_up_requires_final_report(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.get(
            reverse("scan-follow-up-recommendations", args=[self.scan.id])
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(
        "scans.llm_service.suggest_follow_up_recommendations",
        return_value="- ৩ মাস পর ফলো-আপ",
    )
    def test_follow_up_after_report_generated(self, mock_llm):
        FinalReport.objects.create(
            scan=self.scan,
            final_diagnosis="glioma",
            summary="সারসংক্ষেপ",
            status="draft",
            generated_by=self.doctor,
        )
        self.client.force_authenticate(user=self.doctor)
        response = self.client.get(
            reverse("scan-follow-up-recommendations", args=[self.scan.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("ফলো-আপ", response.data["recommendations"])

    def test_follow_up_forbidden_for_radiologist(self):
        self.client.force_authenticate(user=self.radiologist)
        response = self.client.get(
            reverse("scan-follow-up-recommendations", args=[self.scan.id])
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---------- Patient Friendly Explanation ----------

    def test_explanation_blocked_before_approval(self):
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(
            reverse("scan-patient-explanation", args=[self.scan.id])
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(
        "scans.llm_service.generate_patient_friendly_explanation",
        return_value="সহজ ব্যাখ্যা",
    )
    def test_explanation_available_after_approval(self, mock_llm):
        FinalReport.objects.create(
            scan=self.scan,
            final_diagnosis="glioma",
            summary="সারসংক্ষেপ",
            status="approved",
            generated_by=self.doctor,
        )
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(
            reverse("scan-patient-explanation", args=[self.scan.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["explanation"], "সহজ ব্যাখ্যা")

    def test_explanation_forbidden_for_other_patient(self):
        FinalReport.objects.create(
            scan=self.scan,
            final_diagnosis="glioma",
            summary="সারসংক্ষেপ",
            status="approved",
            generated_by=self.doctor,
        )
        self.client.force_authenticate(user=self.other_patient)
        response = self.client.get(
            reverse("scan-patient-explanation", args=[self.scan.id])
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_explanation_forbidden_for_doctor_role(self):
        """
        এই endpoint ইচ্ছাকৃতভাবে শুধু patient role-এর জন্য (IsPatient permission) --
        doctor/radiologist একই তথ্য draft-report/clinical-summary endpoint দিয়ে
        professional ভাষায় পাবে, patient-friendly ভাষার endpoint তাদের দরকার নেই।
        """
        FinalReport.objects.create(
            scan=self.scan,
            final_diagnosis="glioma",
            summary="সারসংক্ষেপ",
            status="approved",
            generated_by=self.doctor,
        )
        self.client.force_authenticate(user=self.doctor)
        response = self.client.get(
            reverse("scan-patient-explanation", args=[self.scan.id])
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

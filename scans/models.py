from django.db import models
from accounts.models import User
from django.conf import settings


class MRIScan(models.Model):
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="scans",
        limit_choices_to={"role": "patient"},
    )
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="uploaded_scans"
    )
    original_image = models.ImageField(upload_to="scans/original/")
    scan_type = models.CharField(max_length=50, default="MRI")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Scan #{self.id} - {self.patient.username}"


class AIAnalysisResult(models.Model):
    scan = models.OneToOneField(
        MRIScan, on_delete=models.CASCADE, related_name="analysis"
    )
    classification = models.CharField(max_length=50)
    confidence_score = models.FloatField()
    segmentation_mask = models.ImageField(
        upload_to="scans/masks/", null=True, blank=True
    )
    segmented_overlay = models.ImageField(
        upload_to="scans/overlay/", null=True, blank=True
    )
    tumor_area_pixels = models.IntegerField(null=True, blank=True)
    tumor_area_percentage = models.FloatField(null=True, blank=True)
    needs_review = models.BooleanField(
        default=False,
        help_text="Classifier 'notumor' বলেছে কিন্তু segmentation উল্লেখযোগ্য tumor area পেয়েছে — ম্যানুয়াল review দরকার",
    )
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.classification} ({self.confidence_score:.2f}%)"


class RadiologistReview(models.Model):
    """
    Radiologist একটা scan review করে এখানে তার মতামত রেকর্ড করে।
    OneToOne রাখা হয়েছে -- একটা scan-এ একবারই final review হবে ধরে নিচ্ছি
    (ভবিষ্যতে একাধিক review লাগলে ForeignKey-তে বদলানো যাবে)।
    """

    STATUS_CHOICES = [
        ("approved", "Approved — AI ফলাফল সঠিক"),
        ("rejected", "Rejected — AI ফলাফল ভুল"),
        ("modified", "Modified — radiologist সংশোধন করেছে"),
    ]

    scan = models.OneToOneField(
        MRIScan, on_delete=models.CASCADE, related_name="radiologist_review"
    )
    radiologist = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reviews",
        limit_choices_to={"role": "radiologist"},
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    observations = models.TextField(
        blank=True, help_text="Radiologist-এর ক্লিনিক্যাল পর্যবেক্ষণ/মন্তব্য"
    )
    corrected_classification = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="AI-এর classification ভুল হলে radiologist-এর সঠিক মত (ঐচ্ছিক)",
    )
    reviewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review of Scan #{self.scan_id} by {self.radiologist} — {self.status}"


class DoctorConsultation(models.Model):
    """
    Radiologist review হয়ে যাওয়ার পর Doctor সেই scan-এ চূড়ান্ত ক্লিনিক্যাল
    মূল্যায়ন ও চিকিৎসা পরামর্শ যোগ করে (infographic workflow ধাপ ৫)।
    OneToOne -- একটা scan-এ একবারই doctor consultation হবে ধরে নিচ্ছি।
    """

    scan = models.OneToOneField(
        MRIScan, on_delete=models.CASCADE, related_name="doctor_consultation"
    )
    doctor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="consultations",
        limit_choices_to={"role": "doctor"},
    )
    clinical_assessment = models.TextField(
        help_text="Doctor-এর সামগ্রিক ক্লিনিক্যাল মূল্যায়ন (AI + radiologist review বিবেচনা করে)"
    )
    treatment_recommendation = models.TextField(
        blank=True, help_text="প্রস্তাবিত চিকিৎসা পরিকল্পনা / পরবর্তী পদক্ষেপ"
    )
    consulted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Consultation of Scan #{self.scan_id} by {self.doctor}"


class FinalReport(models.Model):
    """
    AI Analysis + Radiologist Review + Doctor Consultation -- এই তিনটা ধাপের
    তথ্য একত্র করে চূড়ান্ত রিপোর্ট (infographic workflow ধাপ ৬)।

    গুরুত্বপূর্ণ: status='draft' অবস্থায় patient এই রিপোর্ট দেখতে পারবে না,
    শুধু status='approved' হওয়ার পরেই patient-কে দেখানো হবে
    ("Only the Final Approved Report is delivered to the Patient")।
    """

    STATUS_CHOICES = [
        ("draft", "Draft — এখনো approve হয়নি"),
        ("approved", "Approved — patient দেখতে পারবে"),
    ]

    scan = models.OneToOneField(
        MRIScan, on_delete=models.CASCADE, related_name="final_report"
    )
    final_diagnosis = models.CharField(
        max_length=50,
        help_text="চূড়ান্ত diagnosis -- radiologist-এর corrected_classification "
        "থাকলে সেটা, নাহলে AI-এর classification (view-তে auto-নির্ধারিত)",
    )
    summary = models.TextField(
        help_text="Doctor-এর লেখা সামগ্রিক সারসংক্ষেপ, patient-এর জন্য বোধগম্য ভাষায়"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="generated_reports",
        limit_choices_to={"role": "doctor"},
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_reports",
        limit_choices_to={"role": "doctor"},
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Final Report of Scan #{self.scan_id} — {self.status}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("upload", "Scan Uploaded"),
        ("review", "Scan Reviewed"),
        ("consult", "Doctor Consulted"),
        ("generate_report", "Report Generated"),
        ("approve_report", "Report Approved"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
    )
    scan = models.ForeignKey("MRIScan", on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    details = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    scan = models.ForeignKey(
        MRIScan, on_delete=models.CASCADE, related_name="appointments"
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_appointments",
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_appointments",
    )
    appointment_date = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="scheduled"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Appointment for {self.patient.username} with {self.doctor.username} on {self.appointment_date}"

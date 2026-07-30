from django.db import models
from accounts.models import User


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

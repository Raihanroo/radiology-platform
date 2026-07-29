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

from django.conf import settings
from django.db import models


class UploadedFile(models.Model):
    class Category(models.TextChoices):
        PAPER = "paper", "Paper"
        CODE = "code", "Code archive"
        DOCUMENT = "document", "Document"
        WRITING = "writing", "Writing"
        FEEDBACK = "feedback", "Feedback"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_files"
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    original_filename = models.CharField(max_length=255)
    stored_name = models.CharField(max_length=512)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField()
    checksum_sha256 = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category", "created_at"], name="common_upload_category_idx"),
            models.Index(fields=["owner", "category"], name="common_upload_owner_idx"),
        ]

    def __str__(self) -> str:
        return self.original_filename

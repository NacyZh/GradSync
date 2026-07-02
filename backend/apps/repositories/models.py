from django.conf import settings
from django.db import models


class CodeArtifact(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUPERSEDED = "superseded", "Superseded"
        ARCHIVED = "archived", "Archived"

    project = models.ForeignKey(
        "projects.ResearchProject", on_delete=models.CASCADE, related_name="code_artifacts"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]


class CodeArtifactVersion(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUPERSEDED = "superseded", "Superseded"
        ARCHIVED = "archived", "Archived"

    artifact = models.ForeignKey(CodeArtifact, on_delete=models.CASCADE, related_name="versions")
    project = models.ForeignKey(
        "projects.ResearchProject",
        on_delete=models.CASCADE,
        related_name="code_artifact_versions",
    )
    version_label = models.CharField(max_length=120, blank=True)
    commit_reference = models.CharField(max_length=255, blank=True)
    release_notes = models.TextField(blank=True)
    storage_key = models.CharField(max_length=500)
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    checksum_sha256 = models.CharField(max_length=64)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["-uploaded_at"]

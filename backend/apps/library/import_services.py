from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.projects.archive_services import ensure_project_writable

from .duplicate_services import find_duplicate, normalize_doi, title_author_year_fingerprint
from .models import PaperImportBatch, PaperRecord


def _duplicate_inputs(data: dict) -> dict:
    return {
        "checksum_sha256": data.get("checksum_sha256"),
        "doi": data.get("doi"),
        "external_ids": data.get("external_ids", {}),
        "title": data.get("title"),
        "authors": data.get("authors", []),
        "publication_year": data.get("publication_year"),
    }


class PaperImportService:
    def __init__(self, user, project):
        self.user = user
        self.project = project

    def _require_member(self):
        if not self.project.memberships.filter(user=self.user, status="active").exists():
            raise ValidationError("You are not a member of this project")

    @transaction.atomic
    def create_paper(self, **data) -> PaperRecord:
        self._require_member()
        ensure_project_writable(self.project)
        match = find_duplicate(self.project, **_duplicate_inputs(data))
        if match:
            raise ValidationError(
                {
                    "message": "Duplicate paper detected",
                    "duplicateOfPaperId": str(match.paper.id),
                    "duplicateReason": match.reason,
                }
            )
        paper = PaperRecord.objects.create(
            project=self.project,
            title=data["title"],
            authors=data.get("authors", []),
            venue=data.get("venue", ""),
            publication_year=data.get("publication_year"),
            doi=normalize_doi(data.get("doi")),
            external_ids=data.get("external_ids", {}),
            abstract=data.get("abstract", ""),
            notes=data.get("notes", ""),
            tags=data.get("tags", []),
            import_source=data.get("import_source", PaperRecord.ImportSource.MANUAL),
            fingerprint=title_author_year_fingerprint(
                title=data.get("title"),
                authors=data.get("authors", []),
                publication_year=data.get("publication_year"),
            ),
            created_by=self.user,
        )
        record_event(self.project, self.user, "paper.created", f"Created paper {paper.id}", paper)
        return paper

    @transaction.atomic
    def stage_import(self, *, source_type: str, items: list[dict]) -> PaperImportBatch:
        self._require_member()
        ensure_project_writable(self.project)
        results = []
        accepted_count = duplicate_count = error_count = 0
        for item in items:
            try:
                match = find_duplicate(self.project, **_duplicate_inputs(item))
                if match:
                    duplicate_count += 1
                    results.append(
                        {
                            "status": "duplicate",
                            "duplicateOfPaperId": str(match.paper.id),
                            "duplicateReason": match.reason,
                            "message": "Duplicate paper detected",
                        }
                    )
                else:
                    accepted_count += 1
                    results.append({"status": "accepted", "paper": item})
            except Exception as exc:
                error_count += 1
                results.append({"status": "error", "message": str(exc)})
        batch = PaperImportBatch.objects.create(
            project=self.project,
            requested_by=self.user,
            source_type=source_type,
            total_items=len(items),
            accepted_count=accepted_count,
            duplicate_count=duplicate_count,
            error_count=error_count,
            result_summary=results,
        )
        record_event(
            self.project, self.user, "paper_import.staged", f"Staged paper import {batch.id}", batch
        )
        return batch

    @transaction.atomic
    def commit_import(self, batch: PaperImportBatch) -> PaperImportBatch:
        self._require_member()
        ensure_project_writable(self.project)
        for result in batch.result_summary:
            if result.get("status") == "accepted" and isinstance(result.get("paper"), dict):
                paper_data = result["paper"]
                paper = self.create_paper(
                    **{
                        **paper_data,
                        "import_source": PaperRecord.ImportSource.BATCH,
                    }
                )
                result["paper"] = {"id": str(paper.id), "title": paper.title}
        batch.status = PaperImportBatch.Status.COMMITTED
        batch.committed_at = timezone.now()
        batch.save(update_fields=["status", "committed_at", "result_summary"])
        record_event(
            self.project,
            self.user,
            "paper_import.committed",
            f"Committed paper import {batch.id}",
            batch,
        )
        return batch

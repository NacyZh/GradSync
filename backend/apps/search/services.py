from django.db.models import Q

from apps.library.models import DocumentRecord, PaperRecord
from apps.projects.material_services import externally_shared_q
from apps.projects.models import ProjectMembership
from apps.projects.services import projects_visible_to
from apps.repositories.models import CodeArtifact
from apps.submissions.models import WeeklyProgressReport
from apps.tasks.models import Task

SEARCH_TYPES = ("project", "task", "report", "paper", "document", "code", "member")


def _visible_material_q(user):
    if getattr(user, "is_superuser", False) or getattr(user, "is_administrator", False):
        return Q()
    return externally_shared_q() | Q(
        project__memberships__user=user,
        project__memberships__status=ProjectMembership.Status.ACTIVE,
    )


def _project_result(project):
    return {
        "id": f"project:{project.id}",
        "type": "project",
        "title": project.title,
        "context": project.get_status_display(),
        "path": f"/projects/{project.id}",
        "projectId": project.id,
    }


def global_search(*, user, query: str, per_type_limit: int = 5):
    term = " ".join(query.split())
    visible_projects = projects_visible_to(user)
    visible_project_ids = visible_projects.values("id")

    projects = list(
        visible_projects.filter(Q(title__icontains=term) | Q(description__icontains=term))
        .select_related("advisor")
        .order_by("title", "id")[:per_type_limit]
    )
    tasks = list(
        Task.objects.filter(project_id__in=visible_project_ids)
        .filter(
            Q(title__icontains=term)
            | Q(description__icontains=term)
            | Q(project__title__icontains=term)
        )
        .select_related("project")
        .order_by("-updated_at", "id")[:per_type_limit]
    )
    reports = list(
        WeeklyProgressReport.objects.filter(project_id__in=visible_project_ids)
        .filter(
            Q(completed_work__icontains=term)
            | Q(blockers__icontains=term)
            | Q(next_steps__icontains=term)
            | Q(project__title__icontains=term)
            | Q(student__name__icontains=term)
            | Q(student__nickname__icontains=term)
        )
        .select_related("project", "student")
        .order_by("-report_week_start", "-revision_number")[:per_type_limit]
    )

    material_scope = _visible_material_q(user)
    papers = list(
        PaperRecord.objects.filter(status=PaperRecord.Status.ACTIVE)
        .filter(material_scope)
        .filter(
            Q(title__icontains=term)
            | Q(canonical_title__icontains=term)
            | Q(authors__icontains=term)
            | Q(abstract__icontains=term)
            | Q(tags__icontains=term)
        )
        .select_related("project")
        .distinct()
        .order_by("title", "id")[:per_type_limit]
    )
    documents = list(
        DocumentRecord.objects.filter(status=DocumentRecord.Status.ACTIVE)
        .filter(material_scope)
        .filter(
            Q(title__icontains=term)
            | Q(description__icontains=term)
            | Q(category__name__icontains=term)
        )
        .select_related("project", "category")
        .distinct()
        .order_by("title", "id")[:per_type_limit]
    )
    code_artifacts = list(
        CodeArtifact.objects.filter(status=CodeArtifact.Status.ACTIVE)
        .filter(material_scope)
        .filter(
            Q(name__icontains=term)
            | Q(description__icontains=term)
            | Q(tags__icontains=term)
            | Q(source_path_label__icontains=term)
        )
        .select_related("project")
        .distinct()
        .order_by("name", "id")[:per_type_limit]
    )
    memberships = list(
        ProjectMembership.objects.filter(
            project_id__in=visible_project_ids,
            status=ProjectMembership.Status.ACTIVE,
            user__status="active",
        )
        .filter(
            Q(user__name__icontains=term)
            | Q(user__nickname__icontains=term)
            | Q(user__email__icontains=term)
        )
        .select_related("project", "user")
        .order_by("user__name", "project__title", "id")[:per_type_limit]
    )

    grouped = {
        "project": [_project_result(project) for project in projects],
        "task": [
            {
                "id": f"task:{task.id}",
                "type": "task",
                "title": task.title,
                "context": f"{task.project.title} · {task.get_status_display()}",
                "path": f"/projects/{task.project_id}",
                "projectId": task.project_id,
            }
            for task in tasks
        ],
        "report": [
            {
                "id": f"report:{report.id}",
                "type": "report",
                "title": f"{report.student.name} · {report.report_week_start.isoformat()}",
                "context": f"{report.project.title} · {report.get_review_status_display()}",
                "path": f"/projects/{report.project_id}/reports",
                "projectId": report.project_id,
            }
            for report in reports
        ],
        "paper": [
            {
                "id": f"paper:{paper.id}",
                "type": "paper",
                "title": paper.canonical_title or paper.title,
                "context": paper.project.title,
                "path": "/library/papers",
                "projectId": paper.project_id,
            }
            for paper in papers
        ],
        "document": [
            {
                "id": f"document:{document.id}",
                "type": "document",
                "title": document.title,
                "context": f"{document.category.name} · {document.project.title}",
                "path": "/library/documents",
                "projectId": document.project_id,
            }
            for document in documents
        ],
        "code": [
            {
                "id": f"code:{artifact.id}",
                "type": "code",
                "title": artifact.name,
                "context": artifact.project.title,
                "path": "/library/code",
                "projectId": artifact.project_id,
            }
            for artifact in code_artifacts
        ],
        "member": [
            {
                "id": f"member:{membership.id}",
                "type": "member",
                "title": membership.user.nickname or membership.user.name,
                "context": f"{membership.project.title} · {membership.get_role_display()}",
                "path": f"/projects/{membership.project_id}",
                "projectId": membership.project_id,
            }
            for membership in memberships
        ],
    }
    return {
        "query": term,
        "results": [result for result_type in SEARCH_TYPES for result in grouped[result_type]],
        "counts": {result_type: len(grouped[result_type]) for result_type in SEARCH_TYPES},
    }

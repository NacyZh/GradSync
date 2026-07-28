from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.audit.services import record_execution_event

from .access_services import project_capabilities
from .models import (
    DecisionRecord,
    Deliverable,
    Milestone,
    ProjectMaterial,
    ProjectMembership,
    ProjectRecordLink,
    RiskRecord,
    RiskRevision,
)

RISK_MATRIX = {
    ("low", "low"): "low",
    ("low", "medium"): "low",
    ("low", "high"): "medium",
    ("medium", "low"): "low",
    ("medium", "medium"): "medium",
    ("medium", "high"): "high",
    ("high", "low"): "medium",
    ("high", "medium"): "high",
    ("high", "high"): "high",
}


def derive_risk_severity(likelihood, impact):
    try:
        return RISK_MATRIX[(likelihood, impact)]
    except KeyError as exc:
        raise ValueError("Likelihood and impact must be low, medium, or high.") from exc


def _require_capability(actor, project, capability):
    if not project_capabilities(actor, project).get(capability):
        raise PermissionDenied("This project governance action is forbidden.")


def _active_member(project, user_id, roles=None):
    queryset = ProjectMembership.objects.filter(
        project=project, user_id=user_id, status=ProjectMembership.Status.ACTIVE
    )
    if roles:
        queryset = queryset.filter(role__in=roles)
    membership = queryset.select_related("user").first()
    if not membership:
        raise ValueError("Select an eligible active project member.")
    return membership.user


def _target_snapshot(project, target_type, target_id):
    if target_type == "milestone":
        target = Milestone.objects.filter(project=project, pk=target_id).first()
    elif target_type == "deliverable":
        target = Deliverable.objects.filter(project=project, pk=target_id).first()
    elif target_type == "project_material":
        target = ProjectMaterial.objects.filter(project=project, pk=target_id).first()
    elif target_type == "report":
        from apps.submissions.models import WeeklyProgressReport

        target = WeeklyProgressReport.objects.filter(project=project, pk=target_id).first()
    elif target_type == "decision":
        target = DecisionRecord.objects.filter(project=project, pk=target_id).first()
    elif target_type == "risk":
        target = RiskRecord.objects.filter(project=project, pk=target_id).first()
    elif target_type == "task":
        from apps.tasks.models import Task

        target = Task.objects.filter(project=project, pk=target_id).first()
    else:
        target = None
    if target is None:
        raise ValueError("Linked record must belong to this project.")
    label = getattr(target, "title", None) or f"{target_type.replace('_', ' ').title()} {target.pk}"
    return str(target.pk), str(label)[:255]


def _create_links(*, actor, project, source, links):
    if len(links) > 100:
        raise ValueError("A governance record supports at most 100 links.")
    seen = set()
    rows = []
    for link in links:
        target_type = str(link.get("targetType", ""))
        target_id, label = _target_snapshot(project, target_type, link.get("targetId"))
        key = (target_type, target_id)
        if key in seen:
            raise ValueError("Duplicate governance record link.")
        seen.add(key)
        rows.append(
            ProjectRecordLink(
                project=project,
                decision=source if isinstance(source, DecisionRecord) else None,
                risk=source if isinstance(source, RiskRecord) else None,
                target_type_snapshot=target_type,
                target_id_snapshot=target_id,
                label_snapshot=label,
                created_by=actor,
            )
        )
    ProjectRecordLink.objects.bulk_create(rows)


def _validate_decision_payload(options_considered):
    if not 1 <= len(options_considered) <= 20:
        raise ValueError("Record between 1 and 20 options considered.")
    if any(not str(option).strip() or len(str(option)) > 1000 for option in options_considered):
        raise ValueError("Each considered option must be 1-1000 characters.")


@transaction.atomic
def publish_decision(
    *,
    actor,
    project,
    title,
    context,
    options_considered,
    outcome,
    rationale,
    owner_id,
    effective_date,
    links=(),
    idempotency_key="",
    supersedes=None,
):
    _require_capability(actor, project, "canPublishDecisions")
    existing = DecisionRecord.objects.filter(
        project=project, idempotency_key=idempotency_key
    ).first()
    if idempotency_key and existing:
        return existing
    _validate_decision_payload(options_considered)
    owner = _active_member(
        project,
        owner_id,
        roles=[
            ProjectMembership.Role.ADVISOR,
            ProjectMembership.Role.CO_ADVISOR,
        ],
    )
    predecessor = None
    if supersedes is not None:
        predecessor = (
            DecisionRecord.objects.select_for_update()
            .filter(project=project, pk=supersedes.pk)
            .first()
        )
        if not predecessor or predecessor.status != DecisionRecord.Status.CURRENT:
            raise ValueError("Only a current decision can be superseded.")
        if hasattr(predecessor, "superseded_by"):
            raise ValueError("This decision already has a successor.")
    decision = DecisionRecord.objects.create(
        project=project,
        title=title.strip(),
        context=context.strip(),
        options_considered=[str(value).strip() for value in options_considered],
        outcome=outcome.strip(),
        rationale=rationale.strip(),
        owner=owner,
        effective_date=effective_date,
        supersedes=predecessor,
        published_by=actor,
        idempotency_key=idempotency_key,
    )
    if predecessor:
        DecisionRecord.objects.filter(pk=predecessor.pk).update(
            status=DecisionRecord.Status.SUPERSEDED
        )
    _create_links(actor=actor, project=project, source=decision, links=links)
    record_execution_event(
        project=project,
        actor=actor,
        action="decision.published" if not predecessor else "decision.superseded",
        target=decision,
        state={"status": decision.status},
        privileged=True,
    )
    return decision


def supersede_decision(*, predecessor, **kwargs):
    kwargs.pop("project", None)
    return publish_decision(project=predecessor.project, supersedes=predecessor, **kwargs)


def _append_risk_revision(risk, actor, previous_state, reason, idempotency_key=""):
    revision_number = (risk.revisions.aggregate(value=Max("revision_number"))["value"] or 0) + 1
    return RiskRevision.objects.create(
        project=risk.project,
        risk=risk,
        revision_number=revision_number,
        previous_state=previous_state,
        new_state=risk.state,
        likelihood=risk.likelihood,
        impact=risk.impact,
        severity=risk.severity,
        owner_id_snapshot=risk.owner_id,
        treatment=risk.treatment,
        review_date=risk.review_date,
        closure_rationale=risk.closure_rationale,
        actor=actor,
        reason=reason.strip(),
        idempotency_key=idempotency_key,
    )


@transaction.atomic
def raise_risk(
    *,
    actor,
    project,
    title,
    description,
    source_type="manual",
    source_key="",
    links=(),
    idempotency_key="",
):
    _require_capability(actor, project, "canRaiseRisks")
    existing = RiskRecord.objects.filter(project=project, idempotency_key=idempotency_key).first()
    if idempotency_key and existing:
        return existing
    if source_key:
        existing = RiskRecord.objects.filter(
            project=project, source_type=source_type, source_key=source_key
        ).first()
        if existing:
            return existing
    risk = RiskRecord.objects.create(
        project=project,
        title=title.strip(),
        description=description.strip(),
        source_type=source_type,
        source_key=source_key,
        raised_by=actor,
        idempotency_key=idempotency_key,
    )
    _create_links(actor=actor, project=project, source=risk, links=links)
    _append_risk_revision(risk, actor, RiskRecord.State.RAISED, "Risk raised")
    record_execution_event(
        project=project,
        actor=actor,
        action="risk.raised",
        target=risk,
        state={"status": risk.state, "severity": risk.severity, "version": risk.version},
    )
    return risk


@transaction.atomic
def triage_risk(
    *,
    actor,
    risk,
    expected_version,
    likelihood,
    impact,
    owner_id,
    treatment,
    review_date,
    reason="Risk triaged",
):
    risk = RiskRecord.objects.select_for_update().select_related("project").get(pk=risk.pk)
    _require_capability(actor, risk.project, "canTriageRisks")
    if risk.version != expected_version:
        raise ValueError("The risk changed; refresh and try again.")
    owner = _active_member(risk.project, owner_id)
    if not treatment.strip() or review_date is None:
        raise ValueError("Treatment, owner, and review date are required.")
    previous_state = risk.state
    risk.likelihood = likelihood
    risk.impact = impact
    risk.severity = derive_risk_severity(likelihood, impact)
    risk.owner = owner
    risk.treatment = treatment.strip()
    risk.review_date = review_date
    risk.state = RiskRecord.State.OPEN
    risk.version += 1
    risk.save()
    _append_risk_revision(risk, actor, previous_state, reason)
    record_execution_event(
        project=risk.project,
        actor=actor,
        action="risk.triaged",
        target=risk,
        state={"status": risk.state, "severity": risk.severity, "version": risk.version},
        privileged=True,
    )
    return risk


@transaction.atomic
def transition_risk(
    *,
    actor,
    risk,
    expected_version,
    action,
    reason,
    idempotency_key,
    owner_id=None,
    review_date=None,
    evidence_links=(),
):
    risk = RiskRecord.objects.select_for_update().select_related("project").get(pk=risk.pk)
    _require_capability(actor, risk.project, "canTriageRisks")
    existing = risk.revisions.filter(idempotency_key=idempotency_key).first()
    if existing:
        return risk
    if risk.version != expected_version:
        raise ValueError("The risk changed; refresh and try again.")
    transitions = {
        "start_mitigation": RiskRecord.State.MITIGATING,
        "accept": RiskRecord.State.ACCEPTED,
        "resolve": RiskRecord.State.RESOLVED,
        "reopen": RiskRecord.State.OPEN,
    }
    if action not in transitions:
        raise ValueError("Select a valid risk transition.")
    target = transitions[action]
    previous_state = risk.state
    if action == "reopen":
        if previous_state not in {RiskRecord.State.ACCEPTED, RiskRecord.State.RESOLVED}:
            raise ValueError("Only a closed risk can be reopened.")
        if owner_id:
            risk.owner = _active_member(risk.project, owner_id)
        if not risk.owner_id or not review_date:
            raise ValueError("Reopening requires an owner and review date.")
        risk.review_date = review_date
        risk.closure_rationale = ""
        risk.closed_at = None
    elif action in {"accept", "resolve"}:
        if not reason.strip():
            raise ValueError("Closing a risk requires rationale.")
        risk.closure_rationale = reason.strip()
        risk.closed_at = timezone.now()
    risk.state = target
    risk.version += 1
    risk.save()
    if evidence_links:
        _create_links(actor=actor, project=risk.project, source=risk, links=evidence_links)
    _append_risk_revision(risk, actor, previous_state, reason, idempotency_key=idempotency_key)
    record_execution_event(
        project=risk.project,
        actor=actor,
        action=f"risk.{action}",
        target=risk,
        state={"status": risk.state, "severity": risk.severity, "version": risk.version},
        privileged=action in {"accept", "resolve", "reopen"},
    )
    return risk

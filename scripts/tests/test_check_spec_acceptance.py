import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "check-spec-acceptance.py"
FIXTURES = Path(__file__).parent / "fixtures" / "spec-acceptance"
SPEC = importlib.util.spec_from_file_location("check_spec_acceptance", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def policy():
    return {
        "normativeHeadings": ["Requirements", "Included Scope"],
        "requiredDisciplines": ["product", "testing", "development"],
        "maximumExceptionDays": 14,
        "acceptanceFilename": "acceptance.json",
    }


def test_normative_fingerprint_ignores_formatting_and_metadata(tmp_path):
    first = tmp_path / "spec.md"
    first.write_text("# Feature\n**Status**: Draft\n## Requirements\n- **R1**: Works\n")
    before = module.normative_revision(first, policy())
    first.write_text("# Feature\n**Status**: Accepted\n## Requirements\n\n* R1:   Works\n")
    assert module.normative_revision(first, policy()) == before
    first.write_text("# Feature\n## Requirements\n- R1: Works differently\n")
    assert module.normative_revision(first, policy()) != before


def test_pending_and_stale_decisions_block(tmp_path):
    feature = tmp_path / "016-access-governance"
    feature.mkdir()
    (feature / "spec.md").write_text("# Feature\n## Requirements\n- R1: Works\n")
    revision = module.normative_revision(feature / "spec.md", policy())
    evidence = valid_evidence(revision)
    evidence["decisions"]["testing"] = pending_decision("testing@example.edu")
    (feature / "acceptance.json").write_text(json.dumps(evidence))
    result = module.evaluate_feature(
        feature,
        policy(),
        scope="production",
        now=datetime.now(UTC),
    )
    assert result["outcome"] == "blocked"
    assert "testing" in result["blockers"]


def test_valid_exception_requires_distinct_approver_exact_scope_and_14_days(tmp_path):
    feature = tmp_path / "016-access-governance"
    feature.mkdir()
    (feature / "spec.md").write_text("# Feature\n## Requirements\n- R1: Works\n")
    revision = module.normative_revision(feature / "spec.md", policy())
    now = datetime.now(UTC)
    evidence = valid_evidence(revision)
    evidence["decisions"]["testing"] = pending_decision("testing@example.edu")
    evidence["exceptions"] = [{
        "id": "EXC-2026-001",
        "owner": "owner@example.edu",
        "approver": "approver@example.edu",
        "coveredDisciplines": ["testing"],
        "normativeRevision": revision,
        "releaseScope": "production",
        "reason": "Time-bound release need",
        "approvedAt": now.isoformat(),
        "expiresAt": (now + timedelta(days=14)).isoformat(),
        "revokedAt": None,
    }]
    (feature / "acceptance.json").write_text(json.dumps(evidence))
    result = module.evaluate_feature(feature, policy(), scope="production", now=now)
    assert result["outcome"] == "eligible"
    evidence["exceptions"][0]["approver"] = evidence["exceptions"][0]["owner"]
    assert module.validate_evidence(evidence, feature.name)


def test_exception_longer_than_fourteen_days_is_rejected(tmp_path):
    feature = tmp_path / "016-access-governance"
    feature.mkdir()
    (feature / "spec.md").write_text("# Feature\n## Requirements\n- R1: Works\n")
    revision = module.normative_revision(feature / "spec.md", policy())
    now = datetime.now(UTC)
    evidence = valid_evidence(revision)
    evidence["decisions"]["testing"] = pending_decision("testing@example.edu")
    evidence["exceptions"] = [{
        "id": "EXC-2026-002",
        "owner": "owner@example.edu",
        "approver": "approver@example.edu",
        "coveredDisciplines": ["testing"],
        "normativeRevision": revision,
        "releaseScope": "production",
        "reason": "Overlong exception",
        "approvedAt": now.isoformat(),
        "expiresAt": (now + timedelta(days=14, seconds=1)).isoformat(),
        "revokedAt": None,
    }]
    (feature / "acceptance.json").write_text(json.dumps(evidence))
    result = module.evaluate_feature(feature, policy(), scope="production", now=now)
    assert result["outcome"] == "blocked"


def test_schema_fixtures_reject_malformed_evidence():
    valid = json.loads((FIXTURES / "valid.json").read_text())
    malformed = json.loads((FIXTURES / "malformed.json").read_text())
    assert module.validate_evidence(valid, valid["feature"]) == []
    assert module.validate_evidence(malformed, malformed["feature"])


def test_repository_discovery_defaults_legacy_spec_to_pending(tmp_path):
    (tmp_path / ".specify").mkdir()
    (tmp_path / "specs" / "001-legacy").mkdir(parents=True)
    (tmp_path / ".specify" / "acceptance-policy.json").write_text(
        json.dumps(policy())
    )
    (tmp_path / "specs" / "001-legacy" / "spec.md").write_text(
        "# Legacy\n## Requirements\n- R1: Existing behavior\n"
    )
    report = module.evaluate_repository(root=tmp_path)
    assert [item["feature"] for item in report["features"]] == ["001-legacy"]
    assert report["features"][0]["blockers"] == ["missing acceptance evidence"]


def test_repository_enforcement_can_start_at_a_governance_baseline(tmp_path):
    configured_policy = policy() | {
        "enforcementStartFeature": "016-access-governance",
    }
    (tmp_path / ".specify").mkdir()
    for feature in ("015-legacy", "016-access-governance", "017-next"):
        feature_dir = tmp_path / "specs" / feature
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text(
            f"# {feature}\n## Requirements\n- R1: Existing behavior\n"
        )
    (tmp_path / ".specify" / "acceptance-policy.json").write_text(
        json.dumps(configured_policy)
    )

    report = module.evaluate_repository(root=tmp_path)

    assert [item["feature"] for item in report["features"]] == [
        "016-access-governance",
        "017-next",
    ]
    legacy_report = module.evaluate_repository(root=tmp_path, feature="015-legacy")
    assert [item["feature"] for item in legacy_report["features"]] == ["015-legacy"]


def test_explanatory_edits_outside_normative_sections_keep_revision(tmp_path):
    spec = tmp_path / "spec.md"
    spec.write_text(
        "# Feature\nIntro one\n## Requirements\n- R1: Works\n"
        "## Specification Review\nPending\n"
    )
    before = module.normative_revision(spec, policy())
    spec.write_text(
        "# Feature\nIntro two\n## Requirements\n- R1: Works\n"
        "## Specification Review\nAccepted later\n"
    )
    assert module.normative_revision(spec, policy()) == before


def test_current_boundary_heading_is_part_of_normative_fingerprint(tmp_path):
    configured_policy = policy() | {
        "normativeHeadings": [
            "3. Boundary and Negative Scenarios",
            "3. Exception, Boundary, and Degradation Scenarios",
        ]
    }
    spec = tmp_path / "spec.md"
    spec.write_text(
        "# Feature\n"
        "## 3. Exception, Boundary, and Degradation Scenarios *(mandatory)*\n"
        "- A degraded dependency remains visible.\n"
    )
    before = module.normative_revision(spec, configured_policy)
    spec.write_text(
        "# Feature\n"
        "## 3. Exception, Boundary, and Degradation Scenarios *(mandatory)*\n"
        "- A degraded dependency fails closed.\n"
    )
    assert module.normative_revision(spec, configured_policy) != before


def test_current_boundary_edit_stales_previously_accepted_decisions(tmp_path):
    feature = tmp_path / "017-research-execution-loop"
    feature.mkdir()
    configured_policy = policy() | {
        "normativeHeadings": ["3. Exception, Boundary, and Degradation Scenarios"]
    }
    spec = feature / "spec.md"
    spec.write_text(
        "# Feature\n"
        "## 3. Exception, Boundary, and Degradation Scenarios *(mandatory)*\n"
        "- Email failure keeps in-app delivery.\n"
    )
    evidence = valid_evidence(module.normative_revision(spec, configured_policy))
    evidence["feature"] = feature.name
    evidence["specificationPath"] = f"specs/{feature.name}/spec.md"
    (feature / "acceptance.json").write_text(json.dumps(evidence))
    spec.write_text(
        "# Feature\n"
        "## 3. Exception, Boundary, and Degradation Scenarios *(mandatory)*\n"
        "- Email and cache failure keep authoritative in-app delivery.\n"
    )

    result = module.evaluate_feature(
        feature,
        configured_policy,
        scope="production",
        now=datetime.now(UTC),
    )

    assert result["outcome"] == "blocked"
    assert "acceptance evidence normative revision is stale" in result["blockers"]
    assert {"product", "testing", "development"} <= set(result["blockers"])


def pending_decision(reviewer):
    return {
        "assignedReviewer": reviewer,
        "decision": "pending",
        "decidedRevision": None,
        "decidedAt": None,
        "rationale": "",
    }


def valid_evidence(revision):
    decided = datetime.now(UTC).isoformat()
    decisions = {}
    for discipline in ("product", "testing", "development"):
        decisions[discipline] = {
            "assignedReviewer": f"{discipline}@example.edu",
            "decision": "accepted",
            "decidedRevision": revision,
            "decidedAt": decided,
            "rationale": "Accepted for test",
        }
    return {
        "schemaVersion": 1,
        "feature": "016-access-governance",
        "specificationPath": "specs/016-access-governance/spec.md",
        "normativeRevision": revision,
        "decisions": decisions,
        "exceptions": [],
    }

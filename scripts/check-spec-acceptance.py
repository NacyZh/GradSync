#!/usr/bin/env python3
"""Evaluate revision-bound specification acceptance using repository evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / ".specify" / "acceptance-policy.json"
FEATURE_RE = re.compile(r"^[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")
REVISION_RE = re.compile(r"^[a-f0-9]{64}$")
EXCEPTION_RE = re.compile(r"^EXC-[0-9]{4}-[0-9]{3,}$")


def _heading(line: str):
    match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
    return (len(match.group(1)), match.group(2).strip()) if match else None


def _heading_matches(title: str, configured: list[str]) -> bool:
    normalized = re.sub(r"\s+\*\([^)]*\)\*\s*$", "", title).strip()
    return any(
        normalized == candidate
        or normalized.startswith(candidate + " ")
        or normalized.startswith(candidate + " -")
        for candidate in configured
    )


def _normalize_markdown(lines: list[str]) -> str:
    normalized = []
    for line in lines:
        value = line.strip()
        if not value:
            continue
        value = re.sub(r"<!--.*?-->", "", value)
        value = re.sub(r"^[-*+]\s+", "", value)
        value = re.sub(r"^\d+[.)]\s+", "", value)
        value = re.sub(r"[*_`~]", "", value)
        value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
        value = re.sub(r"\s+", " ", value).strip()
        if value:
            normalized.append(value)
    return "\n".join(normalized)


def normative_content(spec_text: str, headings: list[str]) -> str:
    lines = spec_text.splitlines()
    selected: list[str] = []
    active_level = None
    for line in lines:
        parsed = _heading(line)
        if parsed:
            level, title = parsed
            if _heading_matches(title, headings):
                active_level = level
                selected.append(title)
                continue
            if active_level is not None and level <= active_level:
                active_level = None
        if active_level is not None:
            selected.append(line)
    return _normalize_markdown(selected)


def normative_revision(spec_path: Path, policy: dict) -> str:
    content = normative_content(
        spec_path.read_text(encoding="utf-8"),
        policy["normativeHeadings"],
    )
    if not content:
        raise ValueError(f"{spec_path}: no configured normative sections found")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _timestamp(value, field, errors):
    if not isinstance(value, str):
        errors.append(f"{field} must be an ISO-8601 timestamp")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} must be an ISO-8601 timestamp")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{field} must include a timezone")
        return None
    return parsed


def validate_evidence(data: object, feature: str) -> list[str]:
    errors = []
    if not isinstance(data, dict):
        return ["evidence must be a JSON object"]
    expected_keys = {
        "schemaVersion",
        "feature",
        "specificationPath",
        "normativeRevision",
        "decisions",
        "exceptions",
    }
    unknown = set(data) - expected_keys
    if unknown:
        errors.append("unknown evidence fields: " + ", ".join(sorted(unknown)))
    if data.get("schemaVersion") != 1:
        errors.append("schemaVersion must equal 1")
    if data.get("feature") != feature or not FEATURE_RE.fullmatch(str(data.get("feature", ""))):
        errors.append("feature must match the feature directory")
    if data.get("specificationPath") != f"specs/{feature}/spec.md":
        errors.append("specificationPath must identify this feature spec")
    if not REVISION_RE.fullmatch(str(data.get("normativeRevision", ""))):
        errors.append("normativeRevision must be a lowercase SHA-256 value")
    decisions = data.get("decisions")
    if not isinstance(decisions, dict) or set(decisions) != {
        "product",
        "testing",
        "development",
    }:
        errors.append("decisions must contain only product, testing, and development")
    else:
        for discipline, decision in decisions.items():
            prefix = f"decisions.{discipline}"
            if not isinstance(decision, dict):
                errors.append(f"{prefix} must be an object")
                continue
            required = {
                "assignedReviewer",
                "decision",
                "decidedRevision",
                "decidedAt",
                "rationale",
            }
            if set(decision) != required:
                errors.append(f"{prefix} fields do not match the acceptance schema")
                continue
            if not isinstance(decision["assignedReviewer"], str) or not decision[
                "assignedReviewer"
            ]:
                errors.append(f"{prefix}.assignedReviewer is required")
            state = decision["decision"]
            if state not in {"pending", "accepted", "rejected"}:
                errors.append(f"{prefix}.decision is invalid")
            if state == "pending":
                if decision["decidedRevision"] is not None or decision["decidedAt"] is not None:
                    errors.append(f"{prefix} pending decisions cannot have decision evidence")
            else:
                if not REVISION_RE.fullmatch(str(decision["decidedRevision"] or "")):
                    errors.append(f"{prefix}.decidedRevision must be SHA-256")
                _timestamp(decision["decidedAt"], f"{prefix}.decidedAt", errors)
                if not str(decision["rationale"]).strip():
                    errors.append(f"{prefix}.rationale is required")
    exceptions = data.get("exceptions")
    if not isinstance(exceptions, list):
        errors.append("exceptions must be an array")
    else:
        for index, exception in enumerate(exceptions):
            prefix = f"exceptions[{index}]"
            required = {
                "id",
                "owner",
                "approver",
                "coveredDisciplines",
                "normativeRevision",
                "releaseScope",
                "reason",
                "approvedAt",
                "expiresAt",
                "revokedAt",
            }
            if not isinstance(exception, dict) or set(exception) != required:
                errors.append(f"{prefix} fields do not match the acceptance schema")
                continue
            if not EXCEPTION_RE.fullmatch(str(exception["id"])):
                errors.append(f"{prefix}.id is invalid")
            if not exception["owner"] or not exception["approver"]:
                errors.append(f"{prefix} owner and approver are required")
            if exception["owner"] == exception["approver"]:
                errors.append(f"{prefix} owner and approver must be distinct")
            disciplines = exception["coveredDisciplines"]
            if (
                not isinstance(disciplines, list)
                or not disciplines
                or len(disciplines) != len(set(disciplines))
                or not set(disciplines) <= {"product", "testing", "development"}
            ):
                errors.append(f"{prefix}.coveredDisciplines is invalid")
            if not REVISION_RE.fullmatch(str(exception["normativeRevision"])):
                errors.append(f"{prefix}.normativeRevision must be SHA-256")
            if not str(exception["releaseScope"]).strip() or not str(exception["reason"]).strip():
                errors.append(f"{prefix} scope and reason are required")
            _timestamp(exception["approvedAt"], f"{prefix}.approvedAt", errors)
            _timestamp(exception["expiresAt"], f"{prefix}.expiresAt", errors)
            if exception["revokedAt"] is not None:
                _timestamp(exception["revokedAt"], f"{prefix}.revokedAt", errors)
    return errors


def _valid_exception(exception, *, blockers, revision, scope, now, maximum_days):
    if exception["normativeRevision"] != revision or exception["releaseScope"] != scope:
        return False
    if exception["revokedAt"] is not None or exception["owner"] == exception["approver"]:
        return False
    approved = datetime.fromisoformat(exception["approvedAt"].replace("Z", "+00:00"))
    expires = datetime.fromisoformat(exception["expiresAt"].replace("Z", "+00:00"))
    if (
        approved > now
        or expires <= now
        or expires - approved > timedelta(days=maximum_days)
    ):
        return False
    return set(blockers) <= set(exception["coveredDisciplines"])


def evaluate_feature(
    feature_dir: Path,
    policy: dict,
    *,
    scope: str,
    now: datetime,
    root: Path = ROOT,
):
    feature = feature_dir.name
    spec_path = feature_dir / "spec.md"
    revision = normative_revision(spec_path, policy)
    evidence_path = feature_dir / policy["acceptanceFilename"]
    result = {
        "feature": feature,
        "specificationPath": f"specs/{feature}/spec.md",
        "normativeRevision": revision,
        "decisions": {},
        "exception": None,
        "evidenceValid": False,
        "blockers": [],
        "evaluatedAt": now.isoformat().replace("+00:00", "Z"),
        "outcome": "blocked",
    }
    if not evidence_path.exists():
        result["blockers"] = ["missing acceptance evidence"]
        return result
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result["blockers"] = [f"malformed acceptance evidence: {exc}"]
        return result
    errors = validate_evidence(evidence, feature)
    if errors:
        result["blockers"] = errors
        return result
    result["evidenceValid"] = True
    if evidence["normativeRevision"] != revision:
        result["blockers"].append("acceptance evidence normative revision is stale")
    blocked_disciplines = []
    for discipline in policy["requiredDisciplines"]:
        decision = evidence["decisions"][discipline]
        result["decisions"][discipline] = {
            "reviewer": decision["assignedReviewer"],
            "decision": decision["decision"],
            "decidedRevision": decision["decidedRevision"],
        }
        if decision["decision"] != "accepted":
            blocked_disciplines.append(discipline)
        elif decision["decidedRevision"] != revision:
            blocked_disciplines.append(discipline)
    result["blockers"].extend(blocked_disciplines)
    if result["blockers"]:
        for exception in evidence["exceptions"]:
            try:
                valid = _valid_exception(
                    exception,
                    blockers=blocked_disciplines,
                    revision=revision,
                    scope=scope,
                    now=now,
                    maximum_days=policy["maximumExceptionDays"],
                )
            except (TypeError, ValueError):
                valid = False
            if valid and not any("stale" in blocker for blocker in result["blockers"]):
                result["exception"] = {
                    "id": exception["id"],
                    "scope": exception["releaseScope"],
                    "expiresAt": exception["expiresAt"],
                }
                result["blockers"] = []
                break
    result["outcome"] = "eligible" if not result["blockers"] else "blocked"
    return result


def discover_features(root: Path):
    return sorted(
        path
        for path in (root / "specs").iterdir()
        if path.is_dir() and FEATURE_RE.fullmatch(path.name) and (path / "spec.md").is_file()
    )


def evaluate_repository(*, root=ROOT, scope="production", feature=None, now=None):
    policy = json.loads((root / ".specify/acceptance-policy.json").read_text())
    now = now or datetime.now(UTC)
    feature_dirs = discover_features(root)
    if feature:
        feature_dirs = [path for path in feature_dirs if path.name == feature]
    results = [
        evaluate_feature(path, policy, scope=scope, now=now, root=root)
        for path in feature_dirs
    ]
    return {
        "schemaVersion": 1,
        "releaseScope": scope,
        "evaluatedAt": now.isoformat().replace("+00:00", "Z"),
        "features": results,
        "outcome": "eligible"
        if results and all(item["outcome"] == "eligible" for item in results)
        else "blocked",
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["validate", "report", "enforce"], default="report")
    parser.add_argument("--scope", default="production")
    parser.add_argument("--feature")
    parser.add_argument("--json-output")
    args = parser.parse_args(argv)
    report = evaluate_repository(scope=args.scope, feature=args.feature)
    encoded = json.dumps(report, indent=2, sort_keys=True)
    if args.json_output:
        if args.json_output == "-":
            print(encoded)
        else:
            Path(args.json_output).write_text(encoded + "\n", encoding="utf-8")
    else:
        for item in report["features"]:
            blockers = ", ".join(item["blockers"]) or "none"
            print(f"{item['feature']}: {item['outcome']} (blockers: {blockers})")
        print(f"release scope {args.scope}: {report['outcome']}")
    if args.mode == "validate":
        return int(
            any(
                not item["evidenceValid"]
                and "missing acceptance evidence" not in item["blockers"]
                for item in report["features"]
            )
        )
    if args.mode == "enforce" and report["outcome"] != "eligible":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

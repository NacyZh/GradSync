from __future__ import annotations

import ast
import importlib
import subprocess
import tomllib
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


def _python_files(root: Path):
    return sorted(
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts and "migrations" not in path.parts
    )


def _direct_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.add(node.module)
    return imports


def test_common_shared_core_has_no_direct_business_app_imports():
    forbidden_prefixes = {
        "apps.library",
        "apps.repositories",
        "apps.projects",
        "apps.submissions",
        "apps.resources",
        "apps.notifications",
    }
    violations: list[str] = []

    for path in _python_files(BACKEND_ROOT / "apps" / "common"):
        for imported in _direct_imports(path):
            if any(
                imported == prefix or imported.startswith(f"{prefix}.")
                for prefix in forbidden_prefixes
            ):
                violations.append(f"{path.relative_to(BACKEND_ROOT)} imports {imported}")

    assert violations == []


def test_library_responsibility_areas_are_discoverable():
    expected_paths = [
        "apps/library/models/papers.py",
        "apps/library/models/documents.py",
        "apps/library/models/shared.py",
        "apps/library/serializers/papers.py",
        "apps/library/serializers/documents.py",
        "apps/library/serializers/imports.py",
        "apps/library/serializers/downloads.py",
        "apps/library/services/papers.py",
        "apps/library/services/documents.py",
        "apps/library/services/imports.py",
        "apps/library/services/duplicates.py",
        "apps/library/services/downloads.py",
        "apps/library/views/papers.py",
        "apps/library/views/documents.py",
        "apps/library/views/imports.py",
        "apps/library/views/downloads.py",
    ]

    missing = [path for path in expected_paths if not (BACKEND_ROOT / path).is_file()]

    assert missing == []


def test_library_public_package_exports_preserve_stable_imports():
    models = importlib.import_module("apps.library.models")
    serializers = importlib.import_module("apps.library.serializers")
    services = importlib.import_module("apps.library.services")
    views = importlib.import_module("apps.library.views")

    for name in [
        "DocumentCategory",
        "DocumentRecord",
        "DuplicateDetectionResult",
        "PaperAttachment",
        "PaperFile",
        "PaperImportBatch",
        "PaperImportJob",
        "PaperLibraryActivity",
        "PaperRecord",
        "PaperTitleExtractionResult",
    ]:
        assert hasattr(models, name), f"apps.library.models missing {name}"

    for name in [
        "DocumentRecordSerializer",
        "PaperImportJobSerializer",
        "PaperRecordSerializer",
        "PaperUploadSerializer",
    ]:
        assert hasattr(serializers, name), f"apps.library.serializers missing {name}"

    for name in [
        "DocumentService",
        "PaperImportService",
        "find_duplicate",
        "paper_upload_policy",
        "prepare_shared_paper_download",
    ]:
        assert hasattr(services, name), f"apps.library.services missing {name}"

    for name in [
        "DocumentDownloadView",
        "DocumentViewSet",
        "PaperImportStatusView",
        "PaperViewSet",
        "SharedPaperDownloadView",
    ]:
        assert hasattr(views, name), f"apps.library.views missing {name}"


def test_maintenance_command_mapping_matches_contract():
    target_commands = {
        "apps/library/management/commands/cleanup_seeded_library_papers.py",
        "apps/library/management/commands/cleanup_seeded_library_documents.py",
        "apps/repositories/management/commands/cleanup_seeded_code_artifacts.py",
        "apps/operations/management/commands/seed_research_ops_e2e.py",
        "apps/operations/management/commands/seed_research_ops_validation.py",
        "apps/operations/management/commands/seed_research_ops_performance.py",
    }
    old_commands = {
        "apps/accounts/management/commands/remove_seeded_paper_samples.py",
        "apps/accounts/management/commands/remove_seeded_document_examples.py",
        "apps/accounts/management/commands/remove_seeded_code_samples.py",
        "apps/accounts/management/commands/seed_e2e_research_ops.py",
        "apps/accounts/management/commands/seed_validation_research_ops.py",
        "apps/projects/management/commands/seed_performance_research_ops.py",
    }

    missing_targets = [path for path in target_commands if not (BACKEND_ROOT / path).is_file()]
    retained_old = [path for path in old_commands if (BACKEND_ROOT / path).exists()]

    assert missing_targets == []
    assert retained_old == []


def test_pytest_configuration_uses_backend_pyproject_only():
    pyproject = tomllib.loads((BACKEND_ROOT / "pyproject.toml").read_text())
    pytest_options = pyproject["tool"]["pytest"]["ini_options"]

    assert not (BACKEND_ROOT / "pytest.ini").exists()
    assert pytest_options["DJANGO_SETTINGS_MODULE"] == "gradsync.settings.test"
    assert pytest_options["python_files"] == ["test_*.py", "*_test.py"]
    assert pytest_options["testpaths"] == ["tests"]
    assert "--strict-markers" in pytest_options["addopts"]


def test_pytest_command_contract_uses_module_invocation():
    readme = (REPO_ROOT / "README.md").read_text()
    production_docs = (REPO_ROOT / "docs" / "production.md").read_text()
    release_workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text()

    assert "docker compose exec backend python -m pytest" in readme
    assert "docker compose exec backend python -m pytest" in production_docs
    assert "run: python -m pytest" in release_workflow
    assert "pytest.ini" not in readme
    assert "pytest.ini" not in production_docs


def test_generated_artifact_guard_covers_backend_runtime_paths():
    script = (REPO_ROOT / "scripts" / "check-generated-artifacts.sh").read_text()
    required_patterns = [
        "backend/.pytest_cache",
        "backend/.ruff_cache",
        "backend/*.egg-info",
        "backend/e2e.sqlite3",
        "backend/media/e2e",
        "*/__pycache__",
        "*.pyc",
    ]

    missing = [pattern for pattern in required_patterns if pattern not in script]

    assert missing == []


def test_generated_artifact_guard_reports_and_cleans_backend_negative_fixtures(tmp_path):
    script = REPO_ROOT / "scripts" / "check-generated-artifacts.sh"
    artifacts = [
        REPO_ROOT / "backend" / ".pytest_cache" / "structure-contract.tmp",
        REPO_ROOT / "backend" / ".ruff_cache" / "structure-contract.tmp",
        REPO_ROOT / "backend" / "structure_contract.egg-info" / "PKG-INFO",
        REPO_ROOT / "backend" / "e2e.sqlite3",
        REPO_ROOT / "backend" / "media" / "e2e" / "paper.pdf",
    ]
    for artifact in artifacts:
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("generated")
    try:
        result = subprocess.run(
            ["sh", str(script)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        clean = subprocess.run(
            ["sh", str(script), "--clean"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        subprocess.run(["sh", str(script), "--clean"], cwd=REPO_ROOT, check=False)

    assert result.returncode == 1
    assert "backend/.pytest_cache" in result.stderr
    assert "backend/.ruff_cache" in result.stderr
    assert "backend/structure_contract.egg-info" in result.stderr
    assert "backend/e2e.sqlite3" in result.stderr
    assert "backend/media/e2e" in result.stderr
    assert clean.returncode == 0
    for artifact in artifacts:
        assert not artifact.exists()


def test_release_workflow_keeps_generated_artifact_gates_around_build_outputs():
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text()

    assert workflow.count("sh scripts/check-generated-artifacts.sh") >= 5
    assert "Check generated artifacts before frontend gates" in workflow
    assert "Check generated artifacts after frontend build" in workflow
    assert "Check generated artifacts before full-stack e2e" in workflow
    assert "Check generated artifacts after full-stack e2e" in workflow
    assert "Clean generated frontend build artifacts" in workflow
    assert "Clean generated full-stack e2e artifacts" in workflow

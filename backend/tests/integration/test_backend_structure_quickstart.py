from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2].parent


def test_quickstart_lists_structural_and_us1_validation_commands():
    readme = (REPO_ROOT / "README.md").read_text()
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text()
    expected_test_files = [
        "tests/unit/test_backend_structure_contracts.py",
        "tests/integration/test_paper_library_downloads.py",
        "tests/contract/test_paper_library_file_actions_api.py",
    ]

    missing_test_files = [
        path for path in expected_test_files if not (REPO_ROOT / "backend" / path).is_file()
    ]

    assert "sh scripts/check-generated-artifacts.sh" in readme
    assert "sh scripts/check-generated-artifacts.sh" in workflow
    assert "python -m pytest" in workflow
    assert "python manage.py makemigrations --check --dry-run" in workflow
    assert missing_test_files == []

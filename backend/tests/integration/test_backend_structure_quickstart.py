from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2].parent


def test_quickstart_lists_structural_and_us1_validation_commands():
    quickstart = (
        REPO_ROOT / "specs" / "010-backend-structure-refactor" / "quickstart.md"
    ).read_text()

    expected_commands = [
        "sh scripts/check-generated-artifacts.sh",
        "python -m pytest tests/unit/test_backend_structure_contracts.py",
        "python manage.py makemigrations --check --dry-run",
        "tests/integration/test_paper_library_downloads.py",
        "tests/contract/test_paper_library_file_actions_api.py",
    ]

    missing = [command for command in expected_commands if command not in quickstart]

    assert missing == []

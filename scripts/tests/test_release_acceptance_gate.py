from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_release_workflow_enforces_acceptance_before_image_build():
    workflow = (ROOT / ".github/workflows/release.yml").read_text()
    assert "acceptance-enforce" in workflow
    assert "scripts/check-spec-acceptance.py --mode enforce" in workflow
    assert workflow.index("acceptance-enforce") < workflow.index("production-image")
    assert "needs: [backend, frontend, frontend-e2e, acceptance-enforce]" in workflow
    assert (
        "needs: [backend, frontend, frontend-e2e, acceptance-enforce, "
        "production-image]" in workflow
    )

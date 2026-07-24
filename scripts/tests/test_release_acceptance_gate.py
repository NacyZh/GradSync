from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_release_workflow_enforces_acceptance_before_image_build():
    workflow = (ROOT / ".github/workflows/release.yml").read_text()
    production_only = (
        "if: github.event_name != 'pull_request' && "
        "github.ref == 'refs/heads/master'"
    )

    assert "acceptance-enforce" in workflow
    assert "scripts/check-spec-acceptance.py --mode enforce" in workflow
    assert workflow.index("acceptance-enforce") < workflow.index("production-image")
    assert "needs: [backend, frontend, frontend-e2e, acceptance-enforce]" in workflow
    assert (
        "needs: [backend, frontend, frontend-e2e, acceptance-enforce, "
        "production-image]" in workflow
    )
    assert workflow.count(production_only) == 3
    assert "scripts/check-spec-acceptance.py --mode report" in workflow

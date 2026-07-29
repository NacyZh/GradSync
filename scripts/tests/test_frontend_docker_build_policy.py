from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_frontend_dependency_install_is_bounded_and_configurable():
    dockerfile = (ROOT / "docker/frontend.Dockerfile").read_text()
    compose = (ROOT / "docker-compose.prod.yml").read_text()

    assert "ARG NPM_CONFIG_REGISTRY=" in dockerfile
    assert "ARG NPM_CONFIG_FETCH_TIMEOUT=" in dockerfile
    assert "ARG NPM_CI_TIMEOUT_SECONDS=" in dockerfile
    assert "id=gradsync-frontend-npm" in dockerfile
    assert 'timeout "${NPM_CI_TIMEOUT_SECONDS}s"' in dockerfile
    assert "--loglevel=http" in dockerfile

    assert "GRADSYNC_NPM_REGISTRY" in compose
    assert "GRADSYNC_NPM_FETCH_TIMEOUT_MS" in compose
    assert "GRADSYNC_NPM_CI_TIMEOUT_SECONDS" in compose

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


def test_frontend_image_and_public_asset_are_revision_bound():
    dockerfile = (ROOT / "docker/frontend.Dockerfile").read_text()
    compose = (ROOT / "docker-compose.prod.yml").read_text()
    nginx = (ROOT / "docker/nginx.conf").read_text()
    service_worker = (ROOT / "frontend/public/sw.js").read_text()
    deploy = (ROOT / "scripts/deploy-production.sh").read_text()

    assert "GRADSYNC_BUILD_REVISION" in dockerfile
    assert "org.opencontainers.image.revision" in dockerfile
    assert "dist/version.txt" in dockerfile
    assert "GRADSYNC_BUILD_REVISION" in compose
    assert "location = /version.txt" in nginx
    assert "__GRADSYNC_BUILD_REVISION__" in service_worker
    assert 'public_frontend_revision="$(curl -fsS "$PUBLIC_URL/version.txt"' in deploy
    assert "Public frontend revision mismatch." in deploy

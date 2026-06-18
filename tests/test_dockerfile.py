"""Smoke tests for Docker packaging.

Verifies the Dockerfile and docker-compose.yml exist and contain
the required instructions for a working container.
"""

import re


def test_dockerfile_exists():
    """Dockerfile must exist at the project root."""
    with open("Dockerfile") as f:
        content = f.read()
    assert len(content) > 0


def test_dockerfile_uses_python_base():
    """Dockerfile must use a Python 3.14 base image."""
    with open("Dockerfile") as f:
        content = f.read()
    assert re.search(r"FROM\s+python:3\.14", content), "Must use Python 3.14 base"


def test_dockerfile_copies_source_and_templates():
    """Dockerfile must copy application source, templates, and data."""
    with open("Dockerfile") as f:
        content = f.read()
    for pattern in ["\\.py", "templates", "data/"]:
        assert re.search(pattern, content), f"Dockerfile must copy: {pattern}"


def test_dockerfile_installs_deps():
    """Dockerfile must install Python dependencies via uv."""
    with open("Dockerfile") as f:
        content = f.read()
    assert "uv" in content, "Dockerfile must use uv for dependency installation"
    assert "pyproject.toml" in content, "Dockerfile must copy pyproject.toml"


def test_dockerfile_exposes_port():
    """Dockerfile must EXPOSE the application port (default 8000)."""
    with open("Dockerfile") as f:
        content = f.read()
    assert "EXPOSE" in content, "Dockerfile must EXPOSE a port"


def test_dockerfile_has_entrypoint():
    """Dockerfile must set CMD or ENTRYPOINT to run the app."""
    with open("Dockerfile") as f:
        content = f.read()
    assert "CMD" in content or "ENTRYPOINT" in content, (
        "Dockerfile must have CMD or ENTRYPOINT"
    )
    assert "main" in content, "Entrypoint must reference main module"


def test_docker_compose_exists():
    """docker-compose.yml must exist at the project root."""
    with open("docker-compose.yml") as f:
        content = f.read()
    assert len(content) > 0


def test_docker_compose_has_app_service():
    """docker-compose.yml must define an app service with build and ports."""
    with open("docker-compose.yml") as f:
        content = f.read()
    assert ("build" in content or "image" in content), "Must have build or image directive"
    assert "ports" in content, "Must expose ports"
    assert "BRAVE_SEARCH_API_KEY" in content, (
        "Must reference BRAVE_SEARCH_API_KEY in environment"
    )

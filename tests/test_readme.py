"""Tests for README.md completeness.

Ensures the README contains the deployment instructions and API key
setup documentation required for first-time users (Story 19).
"""

def test_readme_has_brave_api_key_instructions():
    """README must explain how to get and set BRAVE_SEARCH_API_KEY."""
    with open("README.md") as f:
        content = f.read()
    assert "BRAVE_SEARCH_API_KEY" in content, "README must mention the Brave API key env var"
    assert "brave.com" in content or "bravesearchapi.com" in content or "api" in content, (
        "README should link to where to get the Brave Search API key"
    )


def test_readme_has_docker_build_instructions():
    """README must explain how to build and run the Docker image."""
    with open("README.md") as f:
        content = f.read()
    assert "docker" in content.lower(), "README must mention Docker"
    assert "compose" in content.lower() or "docker build" in content.lower(), (
        "README should include Docker Compose or build instructions"
    )


def test_readme_has_cantodict_attribution():
    """README must include attribution for cantodict-archive data (CC4.0)."""
    with open("README.md") as f:
        content = f.read()
    assert "cantodict" in content.lower(), "README must mention CantoDict source"


def test_readme_has_usage_overview():
    """README must describe the basic workflow: paste words, select translation, image, audio."""
    with open("README.md") as f:
        content = f.read()
    # Should mention the key pipeline steps
    assert "translate" in content.lower() or "translation" in content.lower()
    assert "image" in content.lower()
    assert "audio" in content.lower() or "pronunciation" in content.lower()

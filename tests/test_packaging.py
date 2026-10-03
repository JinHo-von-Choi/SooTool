from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _server_json() -> dict:
    return json.loads((_ROOT / "server.json").read_text(encoding="utf-8"))


def _pyproject() -> dict:
    return tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_server_json_versions_match_package_version():
    project_version = _pyproject()["project"]["version"]
    server          = _server_json()
    assert server["version"] == project_version
    assert [p["version"] for p in server["packages"]] == [project_version]


def test_server_json_package_identifier_is_the_published_distribution():
    package = _server_json()["packages"][0]
    assert package["registryType"] == "pypi"
    assert package["identifier"] == _pyproject()["project"]["name"]


def test_readme_carries_registry_ownership_marker():
    name   = _server_json()["name"]
    readme = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert re.search(rf"mcp-name:\s*{re.escape(name)}", readme)


def test_server_json_repository_matches_project_urls():
    repository = _server_json()["repository"]["url"]
    assert repository == _pyproject()["project"]["urls"]["Repository"]

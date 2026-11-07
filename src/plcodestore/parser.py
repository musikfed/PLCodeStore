"""Read-only project inference; never executes application code."""
from __future__ import annotations
import json
import re
import tomllib
from pathlib import Path
from .standards import validate

def detect_project(root: Path) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")
    name = root.name
    version = "0.0.0"
    description = ""
    tags = []
    evidence = {}
    py = root / "pyproject.toml"
    pkg = root / "package.json"
    cargo = root / "Cargo.toml"
    go = root / "go.mod"
    if py.is_file():
        data = tomllib.loads(py.read_text(encoding="utf-8"))
        project = data.get("project", {})
        name = project.get("name") or name
        version = project.get("version") or version
        description = project.get("description") or description
        tags.append("Python")
        evidence["Python"] = "pyproject.toml"
    if pkg.is_file():
        data = json.loads(pkg.read_text(encoding="utf-8"))
        name = data.get("name") or name
        version = data.get("version") or version
        description = data.get("description") or description
        tags.append("JavaScript")
        evidence["JavaScript"] = "package.json"
    if cargo.is_file():
        data = tomllib.loads(cargo.read_text(encoding="utf-8"))
        project = data.get("package", {})
        name = project.get("name") or name
        version = project.get("version") or version
        description = project.get("description") or description
        tags.append("Rust")
        evidence["Rust"] = "Cargo.toml"
    if go.is_file():
        tags.append("Go")
        evidence["Go"] = "go.mod"
    if (root / "platformio.ini").is_file():
        tags.append("PlatformIO")
        evidence["PlatformIO"] = "platformio.ini"
    if (root / "Dockerfile").is_file():
        tags.append("Docker")
        evidence["Docker"] = "Dockerfile"
    if (root / "README.md").is_file() and not description:
        readme = (root / "README.md").read_text(encoding="utf-8")[:8000]
        for line in readme.splitlines():
            s = re.sub(r"[#*_`]", "", line).strip()
            if s and not s.startswith(("!", "[", "<", "http")):
                description = s[:350]
                evidence["description"] = "README.md"
                break
    identifier = re.sub(r"[^A-Za-z0-9._-]+", "-", root.name).strip("-")[:100] or "project"
    meta = {
        "schema_version": "1.0", "id": identifier, "title": str(name)[:180],
        "version": str(version)[:80], "description": str(description or f"Project {name}")[:4000],
        "tags": tags, "visibility": "private", "publication": "disabled",
        "repo_url": None, "demo_url": None, "screenshots": [],
        "source_evidence": evidence
    }
    return validate(meta)

def initialize(root: Path, *, dry_run: bool = False) -> tuple[dict, bool]:
    root = root.resolve()
    target = root / "vitrine" / "meta.json"
    if target.exists():
        return validate(json.loads(target.read_text(encoding="utf-8"))), False
    meta = detect_project(root)
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        # exclusive create; existing author data is never replaced
        with target.open("x", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
            f.write("\n")
    return meta, True

def load(root: Path) -> dict:
    path = root.resolve() / "vitrine" / "meta.json"
    return validate(json.loads(path.read_text(encoding="utf-8")))

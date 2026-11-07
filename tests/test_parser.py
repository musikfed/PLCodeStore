import json
from pathlib import Path
from plcodestore.parser import initialize, detect_project

def test_python_project(tmp_path):
    (tmp_path/"pyproject.toml").write_text('[project]\nname = "hello"\nversion = "1.2.3"\ndescription = "An actual tool"\n')
    meta,created=initialize(tmp_path)
    assert created and meta["title"] == "hello"
    assert meta["version"] == "1.2.3"
    assert meta["publication"] == "disabled"
    (tmp_path/"vitrine"/"meta.json").write_text(json.dumps({**meta,"description":"Author version"}))
    again,created=initialize(tmp_path)
    assert not created and again["description"]=="Author version"

def test_dry_run_never_modifies_project(tmp_path):
    (tmp_path/"package.json").write_text('{"name":"hello","version":"0.2.0"}')
    meta,created=initialize(tmp_path,dry_run=True)
    assert created and meta["title"]=="hello"
    assert not (tmp_path/"vitrine").exists()

def test_rust(tmp_path):
    (tmp_path/"Cargo.toml").write_text('[package]\nname="rustbox"\nversion="0.3"\n')
    assert "Rust" in detect_project(tmp_path)["tags"]

import json
import pytest
from scripts.build_pages import ROOT, prepare, build

def sample():
    return {"publishedOnly": True, "contact": {"phone": "+7 999 999 99 99"},
    "projects": [
      {"id":"demo","title":"<script>bad()</script>","description":"Real demo", "kind":"infra",
       "created_at":"2026-11-05T08:00:00Z","stack":["Python"],"image":"javascript:bad()","api_key":"SECRET"},
      {"id":"private","title":"Private","description":"Secret","kind":"infra","visibility":"private"}]}

def test_safe_import():
    rows=prepare(sample())
    assert len(rows)==1 and rows[0]["id"]=="demo"
    assert "api_key" not in rows[0] and "image" not in rows[0]

def test_requires_author_curated_source():
    with pytest.raises(ValueError):prepare({"projects":sample()["projects"]})

def test_static_render(tmp_path):
    build(prepare(sample()),tmp_path)
    index=(tmp_path/"index.html").read_text(encoding="utf-8")
    assert "&lt;script&gt;" in index and "SECRET" not in index
    assert "+7 999" not in index and "<script>bad()" not in index
    assert (tmp_path/"projects"/"demo"/"index.html").is_file()
    assert (tmp_path/"sitemap.xml").is_file()

def test_snapshot_has_20_projects():
    source=json.loads((ROOT/"data"/"catalog-source.json").read_text(encoding="utf-8"))
    assert len(prepare(source))==20

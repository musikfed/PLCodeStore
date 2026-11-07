"""Autonomous discovery must cover the inventory once, then use Git history."""
import json
from scripts.auto_vitrine import scan

class FakeGit:
    token = None
    budget = 350
    def __init__(self, n=28):
        self.used = 0
        self.data = []
        for i in range(n):
            self.data.append({
                "name": f"project-{i:02d}",
                "full_name": f"musikfed/project-{i:02d}",
                "owner": {"login": "musikfed"},
                "html_url": f"https://github.com/musikfed/project-{i:02d}",
                "private": i == 3,
                "default_branch": "main",
                "size": 0,
                "pushed_at": "2026-11-07T09:00:00Z",
                "created_at": "2026-11-01T08:00:00Z",
                "language": "Python"
            })
    def repos(self, owner):
        self.used += 1
        return self.data
    def file(self, owner, repo, path):
        self.used += 1
        return None

def test_first_scan_covers_all_accessible_repos(tmp_path):
    gh = FakeGit()
    result = scan(gh, "musikfed", tmp_path/"state.json",
                  tmp_path/"drafts", max_repos=60, max_prs=6)
    assert result["inspected"] == 28
    assert result["total"] == 28
    assert result["requests"] < 350
    assert not (tmp_path/"drafts"/"project-03.json").exists()
    assert (tmp_path/"drafts"/"project-00.json").exists()
    state = (tmp_path/"state.json").read_text()
    assert "project-03" not in state

def test_second_scan_skips_unchanged_and_detects_delta(tmp_path):
    gh = FakeGit()
    state = tmp_path/"state.json"
    drafts = tmp_path/"drafts"
    scan(gh, "musikfed", state, drafts, max_repos=60)
    second = scan(gh, "musikfed", state, drafts, max_repos=60)
    assert second["inspected"] == 0
    assert second["skipped_unchanged"] == 28
    gh.data[7]["pushed_at"] = "2026-11-08T09:00:00Z"
    changed = scan(gh, "musikfed", state, drafts, max_repos=60)
    assert changed["inspected"] == 1
    assert changed["items"][0]["repo"] == "project-07"

def test_manual_full_scan_rechecks_everything(tmp_path):
    gh = FakeGit(8)
    state = tmp_path/"state.json"
    scan(gh, "musikfed", state, tmp_path/"drafts", max_repos=60)
    forced = scan(gh, "musikfed", state, tmp_path/"drafts",
                  max_repos=60, full_scan=True)
    assert forced["inspected"] == 8


def test_readme_metadata_does_not_fabricate_version():
    from scripts.auto_vitrine import readme_profile, version
    class ReadMe:
        def file(self,owner,name,path):
            if path=="README.md":
                return """# ACHEWIW — Типография в кармане

> Слово чтимое.

**ACHEWIW (StoryEngine)** — локальная издательская студия для автора: от идеи и плана до редакторской проверки, иллюстраций и книги в PDF, DOCX и EPUB.
"""
            return None
    source=ReadMe()
    profile=readme_profile(source,"musikfed","achewiw")
    assert profile["title"]=="ACHEWIW"
    assert profile["subtitle"]=="Типография в кармане"
    assert "локальная издательская студия" in profile["description"]
    assert version({"name":"achewiw"},source,"musikfed")=="—"


def test_root_studio_jpg_wins_over_vector_docs_preview():
    from scripts.auto_vitrine import images, image_candidates
    nodes=[
        {"path":"docs/screenshots/studio-preview.svg","type":"blob","size":1721,"sha":"a"*40},
        {"path":"docs/showcase/overview.svg","type":"blob","size":2509,"sha":"b"*40},
        {"path":"Studio esp32_2.jpg","type":"blob","size":324518,"sha":"c"*40},
        {"path":"icon.png","type":"blob","size":100,"sha":"d"*40},
    ]
    repo={"name":"esp32s3devkitC-1N16R8","private":False,
          "owner":{"login":"musikfed"},"default_branch":"main"}
    found=images(nodes,repo)
    assert len(found)==1
    assert found[0].endswith("/Studio%20esp32_2.jpg")
    assert image_candidates(nodes,repo)[0][1]=="Studio esp32_2.jpg"


def test_only_documents_and_wallpaper_means_no_real_screenshot():
    from scripts.auto_vitrine import images
    nodes=[
        {"path":"docs/showcase/overview.svg","type":"blob","size":2509},
        {"path":"ui/web/assets/baikal.svg","type":"blob","size":2091},
    ]
    repo={"name":"Irila_baikal_v1.0","private":False,
          "owner":{"login":"musikfed"},"default_branch":"main"}
    assert images(nodes,repo)==[]

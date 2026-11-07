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

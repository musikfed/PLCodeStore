"""GitHub-native author decision bridge, no PAT or OAuth token in Pages.

A logged-in repository owner creates a prefilled Issue to authorize a decision.
Actions consumes the event server-side and uses PL_CODESTORE_TOKEN to change
ONLY vitrine/ of the exact source PR, then merges when explicitly approved.

This flow has two user interactions: Review Studio choice -> GitHub "Submit new
issue". GitHub issues provide authentication and the final confirmation.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

TITLE = re.compile(
    r"^PLCS REVIEW (APPROVE|REWORK) ([A-Za-z0-9-]+)/([A-Za-z0-9][A-Za-z0-9._-]{0,99})#([1-9][0-9]*)$"
)
REVISION = re.compile(r"(?m)^Revision: ([0-9a-f]{40})$")
VALID_BRANCH = "plcodestore/vitrine-proposal"


class DecisionError(Exception):
    pass


class API:
    def __init__(self, token):
        if not token:
            raise DecisionError("GitHub API access is not configured")
        self.token = token

    def call(self, method, url, data=None):
        if not url.startswith("https://api.github.com/"):
            raise DecisionError("Unsupported API host")
        body = None if data is None else json.dumps(data).encode("utf-8")
        headers = {
            "Authorization": "Bearer " + self.token,
            "Accept": "application/vnd.github+json",
            "User-Agent": "PLCodeStore-IssueOps/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, method=method, data=body, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                raw = response.read(2_000_000)
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            # Never show response bodies: they can contain sensitive private-repo data.
            raise DecisionError(f"GitHub API returned HTTP {exc.code} for {method}") from exc

    def repo(self, owner, project, suffix="", method="GET", data=None):
        return self.call(method, f"https://api.github.com/repos/{owner}/{project}{suffix}", data)


def parse_decision(event, expected_owner):
    if event.get("action") != "opened":
        raise DecisionError("Only newly submitted decisions are accepted")
    issue = event.get("issue") or {}
    if issue.get("pull_request") or issue.get("state") != "open":
        raise DecisionError("Only an ordinary open Issue may submit a decision")
    if (issue.get("user") or {}).get("login", "").lower() != expected_owner.lower():
        raise DecisionError("Only the GitHub repository owner may authorize publication")
    match = TITLE.fullmatch(str(issue.get("title", "")))
    if not match:
        raise DecisionError("Not a PL Code Store review decision")
    action, owner, project, number = match.groups()
    if owner.lower() != expected_owner.lower() or project == "PLCodeStore":
        raise DecisionError("Target is outside the allowed GitHub account")
    body = issue.get("body") or ""
    revision = REVISION.search(body)
    if revision is None:
        raise DecisionError("Missing exact proposal revision")
    if action == "APPROVE" and not re.search(r"(?m)^Checks: 3/3$", body):
        raise DecisionError("All three publication checks must be confirmed")
    note_marker = "Замечания (необязательно):"
    note = body.split(note_marker, 1)[1].strip()[:3000] if note_marker in body else ""
    return {
        "action": action,
        "owner": owner,
        "project": project,
        "number": int(number),
        "revision": revision.group(1),
        "note": note,
        "issue_number": issue.get("number"),
    }


def verify_source(api, decision):
    owner, project, number = decision["owner"], decision["project"], decision["number"]
    repo = api.repo(owner, project)
    pr = api.repo(owner, project, f"/pulls/{number}")
    if repo.get("owner", {}).get("login", "").lower() != owner.lower():
        raise DecisionError("Repository owner mismatch")
    head = pr.get("head") or {}
    if (pr.get("state") != "open"
        or head.get("ref") != VALID_BRANCH
        or (head.get("repo") or {}).get("full_name") != f"{owner}/{project}"
        or (pr.get("base") or {}).get("ref") != repo.get("default_branch")
        or head.get("sha") != decision["revision"]):
        raise DecisionError("Proposal changed or does not belong to PL Code Store")
    if pr.get("changed_files", 101) > 100:
        raise DecisionError("Too many changed files for a vitrine-only proposal")
    files = api.repo(owner, project, f"/pulls/{number}/files?per_page=100")
    if (not isinstance(files, list) or not files
        or any(not str(file.get("filename", "")).startswith("vitrine/")
               for file in files)
        or not any(file.get("filename") == "vitrine/meta.json" for file in files)):
        raise DecisionError("Refusing to process a PR that changes project source code")
    return repo, pr


def apply_decision(api, decision, source_repo, pr):
    owner, project, number = decision["owner"], decision["project"], decision["number"]
    if decision["action"] == "REWORK":
        feedback = "🛑 Решение автора: вернуть карточку на доработку."
        if decision["note"]:
            feedback += "\n\nЗамечания:\n" + decision["note"]
        api.repo(owner, project, f"/issues/{number}/comments", "POST", {"body": feedback})
        return f"Замечания переданы в {owner}/{project}#{number}. PR оставлен открытым."

    info = api.repo(owner, project, f"/contents/vitrine/meta.json?ref={decision['revision']}")
    if not isinstance(info, dict) or info.get("encoding") != "base64" or not info.get("sha"):
        raise DecisionError("Expected vitrine/meta.json was not found")
    try:
        meta = json.loads(base64.b64decode(info["content"]).decode("utf-8"))
    except (ValueError, KeyError, UnicodeError) as exc:
        raise DecisionError("Proposal contains invalid JSON metadata") from exc
    if not isinstance(meta, dict) or meta.get("id") != project:
        raise DecisionError("Metadata ID mismatch")
    if meta.get("publication") not in ("review_required", "approved"):
        raise DecisionError("Publication is explicitly disabled in metadata")
    if meta.get("visibility") not in ("public", "private"):
        raise DecisionError("Invalid source visibility")
    if source_repo.get("private") and not meta.get("public_private_approved"):
        raise DecisionError("Closed-source public metadata requires separate owner permission")
    meta["publication"] = "approved"
    updated = base64.b64encode((json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
                               .encode("utf-8")).decode("ascii")
    if meta != json.loads(base64.b64decode(info["content"]).decode("utf-8")):
        api.repo(owner, project, "/contents/vitrine/meta.json", "PUT", {
            "message": "vitrine: author approved publication from PL Code Store Review Studio",
            "content": updated,
            "sha": info["sha"],
            "branch": VALID_BRANCH,
        })
        pr = api.repo(owner, project, f"/pulls/{number}")
        if pr.get("state") != "open" or pr.get("head", {}).get("ref") != VALID_BRANCH:
            raise DecisionError("Proposal status changed during approval")
    latest_sha = (pr.get("head") or {}).get("sha")
    result = api.repo(owner, project, f"/pulls/{number}/merge", "PUT", {
        "merge_method": "squash",
        "sha": latest_sha,
        "commit_title": f"vitrine: publish {project} approved by author",
    })
    if not result.get("merged"):
        raise DecisionError("GitHub did not confirm merge")
    return f"❤️ Автор одобрил {owner}/{project}#{number}. PR объединён; витрина обновится после Pages build."


def run(event, home_token, source_token, repository):
    expected_owner, expected_name = repository.split("/", 1)
    if expected_name != "PLCodeStore":
        raise DecisionError("Review commands may only run from PLCodeStore")
    decision = parse_decision(event, expected_owner)
    home = API(home_token)
    source = API(source_token)
    issue_num = decision["issue_number"]
    if not isinstance(issue_num, int) or issue_num < 1:
        raise DecisionError("Missing GitHub Issue number")
    try:
        repo, pr = verify_source(source, decision)
        result = apply_decision(source, decision, repo, pr)
        home.repo(expected_owner, expected_name,
                  f"/issues/{issue_num}/comments", "POST", {"body": result})
        home.repo(expected_owner, expected_name,
                  f"/issues/{issue_num}", "PATCH", {"state": "closed"})
        print(result)
    except DecisionError as exc:
        # Preserve Issue as open, so the author can see and resolve a rejected decision.
        home.repo(expected_owner, expected_name,
                  f"/issues/{issue_num}/comments", "POST",
                  {"body": "⚠️ Решение не выполнено: " + str(exc)
                           + ". Проверь PR и предложи действие заново."})
        raise


def main():
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        raise SystemExit("GITHUB_EVENT_PATH required")
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    run(event, os.environ.get("GITHUB_TOKEN"), os.environ.get("PL_CODESTORE_TOKEN"),
        os.environ.get("GITHUB_REPOSITORY", ""))
if __name__ == "__main__":
    main()

"""Build public author-review queue from real, open vitrine Pull Requests.

GitHub Pages remains stateless and public. Do not show private repository
metadata or their PRs. Approval takes place in source GitHub PR, not on Pages.
"""
from __future__ import annotations
import base64
import json
import re
import urllib.parse
from pathlib import Path
from scripts.vitrine_cover import cover

ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
BRANCH = "plcodestore/vitrine-proposal"

def review_items(gh, owner, repos, max_repos=65):
    found = []
    for repo in repos[:max_repos]:
        if repo.get("private") or not ID.fullmatch(repo.get("name","")):
            continue
        if gh.used + 3 >= gh.budget:
            break
        name=repo["name"]
        prs=gh.api("GET",f"/repos/{owner}/{name}/pulls?state=open&per_page=30",missing_ok=True)
        if not isinstance(prs,list):
            continue
        for pr in prs:
            if pr.get("head",{}).get("ref") != BRANCH:
                continue
            if pr.get("head",{}).get("repo",{}).get("full_name") != f"{owner}/{name}":
                continue
            if not isinstance(pr.get("number"),int):
                continue
            head=pr["head"].get("sha","")
            if not re.fullmatch("[a-fA-F0-9]{40}",head):
                continue
            if gh.used + 2 >= gh.budget:
                break
            data=gh.api("GET",f"/repos/{owner}/{name}/contents/vitrine/meta.json?ref={head}",missing_ok=True)
            if not isinstance(data,dict) or data.get("encoding")!="base64":
                continue
            try:
                meta=json.loads(base64.b64decode(data["content"]).decode("utf-8"))
            except (ValueError,TypeError,KeyError,UnicodeError):
                continue
            if not isinstance(meta,dict) or meta.get("id") != name or meta.get("visibility")!="public":
                continue
            if meta.get("publication") not in ("review_required","approved"):
                continue
            # Only allowlisted author-reviewed public fields are exported.
            title=str(meta.get("title") or name)[:160]
            desc=str(meta.get("description") or "")[:600]
            version=str(meta.get("version") or "—")[:65]
            tags=[str(x)[:35] for x in meta.get("tags",[])[:12] if isinstance(x,str)]
            number=pr["number"]
            pr_url=f"https://github.com/{owner}/{name}/pull/{number}"
            edit_url=f"https://github.com/{owner}/{name}/edit/{BRANCH}/vitrine/meta.json"
            found.append({
                "id":name,"repository":f"{owner}/{name}","number":number,
                "revision":head,"title":title,"description":desc,"version":version,
                "tags":tags,"pr_url":pr_url,"edit_url":edit_url,
                "image":None,"status":str(meta.get("status") or "Ожидает решения")[:100],
            })
    return sorted(found,key=lambda r:(r["repository"].lower(),r["number"]))

def write_queue(out:Path, items):
    path=out/"data"
    path.mkdir(parents=True,exist_ok=True)
    (path/"review_queue.json").write_text(
       json.dumps({"source":"open GitHub PRs with vitrine/meta.json",
                   "public_only":True,"items":items},ensure_ascii=False,indent=2)+"\n",
       encoding="utf-8")
    covers=out/"assets"/"covers"
    covers.mkdir(parents=True,exist_ok=True)
    for item in items:
        (covers/("review-"+item["id"]+".svg")).write_text(
            cover(item["title"],item["version"],"diagram","public",
                  item["tags"][0] if item["tags"] else "Software"),encoding="utf-8")

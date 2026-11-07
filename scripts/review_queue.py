"""Build public author-review queue from real, open vitrine Pull Requests.

GitHub Pages remains stateless and public. Do not show private repository
metadata or their PRs. Approval takes place in source GitHub PR, not on Pages.
"""
from __future__ import annotations
import base64
import json
import re
import urllib.parse
from urllib.parse import urlsplit, unquote, quote
from pathlib import Path
from scripts.vitrine_cover import cover

ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
BRANCH = "plcodestore/vitrine-proposal"


VALID_MEDIA_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".svg")
MEDIA_ROOTS = ("docs/media/", "docs/screenshots/", "docs/showcase/",
               "screenshots/", "images/", "static/", "assets/", "vitrine/screenshots/")

def public_original_image(screenshots, owner, repo, branch):
    """Choose real existing-repo media, never link a private or third-party host."""
    if not isinstance(screenshots, list):
        return None
    expected = f"/{owner}/{repo}/{quote(branch, safe='')}/"
    for item in screenshots[:20]:
        if not isinstance(item, str):
            continue
        parsed = urlsplit(item)
        if parsed.scheme != "https" or parsed.hostname != "raw.githubusercontent.com":
            continue
        if parsed.query or parsed.fragment or parsed.username or parsed.password:
            continue
        if not parsed.path.startswith(expected):
            continue
        asset_path = unquote(parsed.path[len(expected):])
        if (".." in asset_path.split("/") or not asset_path.startswith(MEDIA_ROOTS)
            or not asset_path.lower().endswith(VALID_MEDIA_SUFFIXES)):
            continue
        # Prefer the exact first verified source path; avoid inheriting external URLs.
        return "https://raw.githubusercontent.com" + parsed.path
    return None

def proposal_media(gh,item,owner,name,default_branch,head):
    """Resolve version-pinned images from the pending PR branch.

    Relative vitrine/screenshots files are allowed only when they are *actually
    present* in the current reviewed PR SHA. This also prevents broken thumbs.
    """
    if not isinstance(item,str):
        return None
    if item.startswith("vitrine/screenshots/") and not item.startswith("/"):
        path=item
        if (".." in path.split("/") or
            not re.fullmatch(r"vitrine/screenshots/[a-zA-Z0-9_. -]+\.(?:png|jpg|jpeg|webp|svg)",path,re.I)):
            return None
        data=gh.api("GET",f"/repos/{owner}/{name}/contents/"
                    +urllib.parse.quote(path,safe="/")+f"?ref={head}",missing_ok=True)
        if not isinstance(data,dict) or data.get("type")!="file" or data.get("size",0)>3_000_000:
            return None
        return "https://raw.githubusercontent.com/"+owner+"/"+name+"/"+head+"/"+quote(path,safe="/")
    return public_original_image([item],owner,name,default_branch)

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
            if meta.get("publication") not in ("review_required","approved","publish_on_merge"):
                continue
            # Only allowlisted author-reviewed public fields are exported.
            title=str(meta.get("title") or name)[:160]
            desc=str(meta.get("description") or "")[:600]
            version=str(meta.get("version") or "—")[:65]
            tags=[str(x)[:35] for x in meta.get("tags",[])[:12] if isinstance(x,str)]
            real_images=[]
            for asset in meta.get("screenshots",[])[:8] if isinstance(meta.get("screenshots"),list) else []:
                validated=proposal_media(gh,asset,owner,name,repo.get("default_branch","main"),head)
                if validated and validated not in real_images:real_images.append(validated)
            real_image=real_images[0] if real_images else None
            image_caption=("Снимок HTML-интерфейса, отрендеренный Playwright (не фото аппаратного запуска)"
                           if meta.get("screenshot_source")=="browser-rendered-static" and real_image
                           else "Векторный макет из исходного репозитория"
                           if real_image and real_image.lower().endswith(".svg")
                           else "Изображение из исходного репозитория"
                           if real_image else "Сгенерированная графическая обложка")
            number=pr["number"]
            pr_url=f"https://github.com/{owner}/{name}/pull/{number}"
            edit_url=f"https://github.com/{owner}/{name}/edit/{BRANCH}/vitrine/meta.json"
            found.append({
                "id":name,"repository":f"{owner}/{name}","number":number,
                "revision":head,"title":title,"description":desc,"version":version,
                "tags":tags,"pr_url":pr_url,"edit_url":edit_url,
                "image":real_image,"images":real_images[:4],"image_caption":image_caption,
                "status":str(meta.get("status") or "Ожидает решения")[:100],
                "publication":meta.get("publication"),
                "publish_on_merge":meta.get("publication") in ("approved","publish_on_merge"),
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

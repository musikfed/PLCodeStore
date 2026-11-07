#!/usr/bin/env python3
"""Safely render an existing STATIC HTML interface to a real screenshot.

Used only for author-owned PUBLIC repositories and already-open vitrine PRs.
No build commands, npm install, arbitrary subprocesses or online API calls
inside Chromium. It never claims the result is a photo of live hardware.
"""
from __future__ import annotations
import argparse
import base64
import io
import json
import tempfile
import urllib.parse
from pathlib import Path

from scripts.auto_vitrine import Git, PROPOSAL_BRANCH

ENTRYPOINTS = (
    "ui/web/index.html",
    "web/index.html",
    "frontend/static/index.html",
    "docs/index.html",
)
IMAGE_DEST = "vitrine/screenshots/desktop.png"
MAX_SOURCE_BYTES = 512_000


def contents(gh: Git, owner: str, repo: str, path: str, ref: str):
    url = f"/repos/{owner}/{repo}/contents/" + urllib.parse.quote(path, safe="/")
    url += "?ref=" + urllib.parse.quote(ref, safe="")
    result = gh.api("GET", url, missing_ok=True)
    if not isinstance(result, dict) or result.get("encoding") != "base64":
        return None, None
    return base64.b64decode(result["content"]), result.get("sha")


def guarded_repo(gh, owner, name):
    data=gh.api("GET",f"/repos/{owner}/{name}",missing_ok=True)
    if not data or data.get("private") or data.get("archived"):
        raise ValueError("Screenshots can only be generated for public active repos")
    if data.get("owner",{}).get("login","").lower()!=owner.lower():
        raise ValueError("Repository must be owned by the configured account")
    return data


def capture_static(gh, owner, name, *, requested_entry=None):
    from playwright.sync_api import sync_playwright

    details=guarded_repo(gh,owner,name)
    base=details.get("default_branch","main")
    raw,sha=contents(gh,owner,name,"vitrine/meta.json",PROPOSAL_BRANCH)
    if not raw:
        return {"repo":name,"status":"skip: no proposal branch metadata"}
    meta=json.loads(raw)
    if (meta.get("id")!=name or meta.get("visibility")!="public"
            or meta.get("publication") not in ("review_required","publish_on_merge")):
        return {"repo":name,"status":"skip: not public pending proposal"}
    if meta.get("screenshot_source") in ("original-repository-file","browser-rendered-static") or any(
        isinstance(x,str) and x.startswith("vitrine/screenshots/")
        for x in meta.get("screenshots",[]) if isinstance(meta.get("screenshots"),list)
    ):
        return {"repo":name,"status":"skip: approved asset or captured screen already present"}

    tree=gh.tree(owner,name,base)
    paths={n["path"] for n in tree if n.get("type")=="blob"}
    candidates=(requested_entry,) if requested_entry else ENTRYPOINTS
    entry=next((p for p in candidates if p in paths),None)
    if not entry:
        return {"repo":name,"status":"skip: no trusted static HTML entrypoint"}
    web_root=entry.rsplit("/",1)[0]
    # Only HTML, CSS, JS and SVG used for static preview, not arbitrary binaries.
    allowed={".html",".css",".js",".svg",".json"}
    files=[n for n in tree if n.get("type")=="blob" and
           n.get("path","").startswith(web_root+"/") and
           Path(n["path"]).suffix.lower() in allowed and
           n.get("size",0)<=MAX_SOURCE_BYTES]
    if len(files)>50:
        return {"repo":name,"status":"skip: excessive static assets"}
    with tempfile.TemporaryDirectory(prefix="plcs-static-") as folder:
        root=Path(folder)
        for node in files:
            data,_=contents(gh,owner,name,node["path"],base)
            if data is None or len(data)>MAX_SOURCE_BYTES:continue
            dest=root/node["path"]
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(data)
        index=root/entry
        if not index.is_file():
            return {"repo":name,"status":"skip: HTML asset not accessible"}
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
            context=browser.new_context(viewport={"width":1440,"height":810},
                device_scale_factor=1,service_workers="block")
            # Static site may have JS; abort ALL network requests.
            context.route("**/*",lambda route: route.abort() if
                route.request.url.startswith(("http://","https://")) else route.continue_())
            page=context.new_page()
            page.goto(index.as_uri(),wait_until="domcontentloaded",timeout=25000)
            page.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important}")
            page.wait_for_timeout(500)
            picture=page.screenshot(type="png",animations="disabled",full_page=False)
            browser.close()

    if len(picture)>2_500_000:
        return {"repo":name,"status":"skip: screenshot too large"}
    route=f"/repos/{owner}/{name}/contents/"+IMAGE_DEST
    existing=gh.api("GET",route+"?ref="+urllib.parse.quote(PROPOSAL_BRANCH,safe=""),
                    missing_ok=True)
    if existing:
        return {"repo":name,"status":"skip: pre-existing screenshot never overwritten"}
    gh.api("PUT",route,{"branch":PROPOSAL_BRANCH,
        "message":"vitrine: capture real browser rendering of project static UI",
        "content":base64.b64encode(picture).decode("ascii")})
    # Re-read metadata, with current SHA, to avoid clobbering author edits.
    updated,current_sha=contents(gh,owner,name,"vitrine/meta.json",PROPOSAL_BRANCH)
    current=json.loads(updated)
    if current.get("publication") not in ("review_required","publish_on_merge"):
        raise ValueError("Publication state changed during capture")
    current["screenshots"]=[IMAGE_DEST]+[
        p for p in current.get("screenshots",[])
        if isinstance(p,str) and p!=IMAGE_DEST
    ][:5]
    current["display_mode"]="interface"
    current["screenshot_source"]="browser-rendered-static"
    current["screenshot_origin"]=entry
    gh.api("PUT",f"/repos/{owner}/{name}/contents/vitrine/meta.json",{
        "branch":PROPOSAL_BRANCH,
        "message":"vitrine: use captured static UI screenshot (not a hardware photograph)",
        "sha":current_sha,
        "content":base64.b64encode((json.dumps(current,ensure_ascii=False,indent=2)+"\n").encode()).decode(),
    })
    return {"repo":name,"status":"captured static HTML viewport",
            "path":IMAGE_DEST,"bytes":len(picture),"entry":entry}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--owner",default="musikfed")
    p.add_argument("--repo",default="Irila_baikal_v1.0")
    p.add_argument("--entry",default=None)
    p.add_argument("--budget",type=int,default=45)
    a=p.parse_args()
    token=__import__("os").getenv("PL_CODESTORE_TOKEN")
    if not token:
        raise SystemExit("PL_CODESTORE_TOKEN is required")
    result=capture_static(Git(token,budget=a.budget),a.owner,a.repo,requested_entry=a.entry)
    print(json.dumps(result,ensure_ascii=False))

if __name__=="__main__":
    main()

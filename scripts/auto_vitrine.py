#!/usr/bin/env python3
"""Daily GitHub-only vitrine discovery; independent of AI and view_my_prj.

One optional owner PAT (PL_CODESTORE_TOKEN) can read/write all repositories
it is granted access to. Proposes vitrine/ through per-repository pull requests.
Private code and images are never included in public showcase metadata.
"""
from __future__ import annotations
import argparse
import base64
import html
import hashlib
import json
import os
import re
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from scripts.vitrine_cover import cover as make_cover

ROOT=Path(__file__).resolve().parents[1]
PROPOSAL_BRANCH="plcodestore/vitrine-proposal"
IMAGE_EXT=(".png",".jpg",".jpeg",".webp",".svg")
IMAGE_PREFIX=("docs/screenshots/","docs/media/","docs/showcase/","screenshots/","images/","static/","assets/")
SKIP={"PLCodeStore","view_my_prj","my_self"}

class Git:
    def __init__(self,token=None,budget=160):
        self.token=token
        self.budget=budget
        self.used=0
    def api(self,method,path,body=None,missing_ok=False):
        if not path.startswith("/") or path.startswith("//"):raise ValueError("Invalid API path")
        if self.used>=self.budget:raise RuntimeError("API budget exhausted")
        self.used+=1
        data=None if body is None else json.dumps(body).encode("utf-8")
        head={"User-Agent":"PLCodeStore-vitrine/0.2","Accept":"application/vnd.github+json"}
        if self.token:head["Authorization"]="Bearer "+self.token
        if body is not None:head["Content-Type"]="application/json"
        req=urllib.request.Request("https://api.github.com"+path,data=data,method=method,headers=head)
        try:
            with urllib.request.urlopen(req,timeout=18) as response:
                return json.loads(response.read(1_500_000).decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if missing_ok and exc.code in (403,404,409,422):return None
            raise
    def repos(self,owner):
        # Authenticated personal token can include owned private repositories.
        url="/user/repos?affiliation=owner&per_page=100&page={}"
        page1=self.api("GET",url.format(1),missing_ok=True) if self.token else None
        if not isinstance(page1,list):
            url="/users/"+urllib.parse.quote(owner,safe="")+"/repos?per_page=100&page={}"
            page1=self.api("GET",url.format(1))
        result=[]
        for page in range(1,5):
            arr=page1 if page==1 else self.api("GET",url.format(page))
            if not isinstance(arr,list):break
            result.extend(x for x in arr if x.get("owner",{}).get("login","").lower()==owner.lower()
                          and x.get("name") not in SKIP and not x.get("archived") and not x.get("disabled"))
            if len(arr)<100:break
        return sorted(result,key=lambda x:x["name"].lower())
    def file(self,owner,repo,path):
        ep="/repos/"+owner+"/"+repo+"/contents/"+urllib.parse.quote(path,safe="/")
        result=self.api("GET",ep,missing_ok=True)
        if not isinstance(result,dict) or result.get("type")!="file" or result.get("encoding")!="base64":return None
        return base64.b64decode(result["content"]).decode("utf-8",errors="replace")
    def tree(self,owner,repo,sha):
        path="/repos/"+owner+"/"+repo+"/git/trees/"+urllib.parse.quote(sha,safe="")+"?recursive=1"
        result=self.api("GET",path,missing_ok=True)
        return result.get("tree",[]) if isinstance(result,dict) and not result.get("truncated") else []

def version(repo,gh,owner):
    for name in ("pyproject.toml","package.json","Cargo.toml"):
        data=gh.file(owner,repo["name"],name)
        if not data:continue
        try:
            parsed=json.loads(data) if name=="package.json" else tomllib.loads(data)
            value=parsed.get("version") if name=="package.json" else parsed.get("project" if name=="pyproject.toml" else "package",{}).get("version")
            if isinstance(value,str) and value:return value[:65]
        except (ValueError,KeyError):pass
    return "—"  # Unverified version must not be invented.

def image_candidates(tree,repo):
    """Source-verified assets, including root-level photos with spaces in filenames.

    Raster screenshots win over generic diagrams; never claim a UI screenshot
    where only a decorative SVG or an architecture sketch exists.
    """
    if repo.get("private"):
        return []
    choices=[]
    for node in tree:
        path=node.get("path","")
        if node.get("type")!="blob" or not path.lower().endswith(IMAGE_EXT):
            continue
        if node.get("size",0)>3_000_000 or re.search(
            r"secret|password|token|private\.key|credential",path,re.I):
            continue
        lower=path.lower()
        is_raster=lower.endswith((".png",".jpg",".jpeg",".webp"))
        screenshot_hints=("screenshot","screen","studio","desktop","capture","interface","ui-preview","webui","web-ui","dashboard","gui")
        has_hint=any(t in lower for t in screenshot_hints)
        in_vitrine=lower.startswith("vitrine/screenshots/")
        in_known=lower.startswith(IMAGE_PREFIX)
        is_root="/" not in path
        # Root-level Studio*.jpg is genuine source media; random assets are not.
        if not (in_vitrine or in_known or (is_root and is_raster and has_hint)):
            continue
        if any(t in lower for t in ("logo","favicon","badge","icon","wallpaper","background","watermark")):
            continue
        is_diagram=lower.endswith(".svg") or any(t in lower for t in ("diagram","overview","schematic"))
        score=(150 if in_vitrine else 0)+(90 if is_raster else 0)+(40 if has_hint else 0)
        score+=(25 if "/screenshots/" in lower else 0)+(10 if is_root else 0)
        if is_diagram:score-=110
        choices.append((score,path,node.get("sha"),is_diagram))
    choices.sort(key=lambda x:(-x[0],x[1]))
    return choices

def images(tree,repo):
    owner=repo["owner"]["login"];branch=repo.get("default_branch","main")
    # Do not promote a vector workflow sketch as an authentic app screenshot.
    winners=[x for x in image_candidates(tree,repo) if not x[3]][:3]
    return ["https://raw.githubusercontent.com/"+owner+"/"+repo["name"]+"/"
            +urllib.parse.quote(branch,safe="")+"/"+urllib.parse.quote(path,safe="/")
            for _,path,_,_ in winners]

def cover(name, ver, mode, visibility="public"):
    """Illustrative artistic cover: reproducible, not a screenshot."""
    return make_cover(name, ver, mode=mode, visibility=visibility)

def readme_profile(gh,owner,name):
    """Read author-written project information; do not fabricate marketing claims."""
    raw=gh.file(owner,name,"README.md")
    if not raw:return {"title":name,"description":None,"subtitle":None}
    head=re.search(r"(?m)^#\s+(.{2,160})\s*$",raw)
    heading=re.sub(r"[\*_\[\]]","",head.group(1)).replace(chr(96),"").strip() if head else name
    title,sep,subtitle=heading.partition(" — ")
    if not sep:title,sep,subtitle=heading.partition(" - ")
    if not title or name.lower() not in title.lower():
        title=name
        subtitle=None
    description=None
    for block in re.split(r"\n\s*\n",raw):
        line=block.strip()
        if not line or line.startswith(("#",">","![","[![",chr(96)*3,"|","- ","* ","1. ")):
            continue
        if "](" in line and len(line.split())<10:continue
        plain=re.sub(r"!?\[([^\]]+)\]\([^)]+\)",r"\1",line)
        plain=re.sub(r"[\*_]","",plain).replace(chr(96),"")
        plain=re.sub(r"\s+"," ",plain).strip()
        if len(plain)<85 or plain.startswith(("Источник:","License:","Status:")):
            continue
        description=plain[:350]
        break
    return {"title":title[:120],"description":description,
            "subtitle":subtitle[:140] if subtitle else None}

def inferred(repo,gh,owner):
    private=bool(repo.get("private"))
    is_empty=repo.get("size",0)==0
    tree=[] if is_empty else gh.tree(owner,repo["name"],repo.get("default_branch","main"))
    shots=images(tree,repo)
    ver="—" if is_empty else version(repo,gh,owner)
    profile={"title":repo["name"],"description":None,"subtitle":None} if is_empty else readme_profile(gh,owner,repo["name"])
    mode="development" if is_empty else "interface" if shots else "diagram"
    status="В разработке" if is_empty else "Черновик — ожидает проверки"
    return {"schema_version":"1.0","id":repo["name"],"title":profile["title"],"version":ver,
      "description":(repo.get("description") or profile["description"] or "Назначение проекта уточняется автором.")[:350],
      "subtitle":profile["subtitle"],
      "tags":[repo.get("language") or "Git"],"visibility":"private" if private else "public",
      "publication":"publish_on_merge" if not private else "review_required","public_private_approved":False,
      "display_mode":mode,"status":status,"repo_url":None if private else repo.get("html_url"),
      "screenshots":shots,"cover":"vitrine/generated/cover.svg","cover_type":"schematic-not-screenshot"}

def propose(gh,owner,repo,meta):
    if not gh.token:return "no personal token"
    name=repo["name"]
    refpath="/repos/"+owner+"/"+name+"/git/ref/heads/"
    exists=gh.api("GET",refpath+urllib.parse.quote(PROPOSAL_BRANCH,safe="/"),missing_ok=True)
    if exists:return "proposal branch exists"
    base=gh.api("GET",refpath+urllib.parse.quote(repo.get("default_branch","main"),safe="/"),missing_ok=True)
    if not base:return "no initial commit"
    gh.api("POST","/repos/"+owner+"/"+name+"/git/refs",
           {"ref":"refs/heads/"+PROPOSAL_BRANCH,"sha":base["object"]["sha"]})
    def put(path,text,message):
        gh.api("PUT","/repos/"+owner+"/"+name+"/contents/"+urllib.parse.quote(path,safe="/"),
               {"branch":PROPOSAL_BRANCH,"message":message,
                "content":base64.b64encode(text.encode("utf-8")).decode()})
    # Place verified screenshots *inside the source repo* as requested by the
    # open vitrine/ standard. Each image is copied verbatim, never synthesized.
    # Only a small, bounded number of source images is copied per proposal.
    copied=[]
    source_urls=meta.get("screenshots",[])[:3]
    base_branch=repo.get("default_branch","main")
    for ix,url in enumerate(source_urls):
        parsed=urllib.parse.urlsplit(url)
        prefix="/"+owner+"/"+name+"/"+urllib.parse.quote(base_branch,safe="")+"/"
        if parsed.scheme!="https" or parsed.hostname!="raw.githubusercontent.com" or not parsed.path.startswith(prefix):
            continue
        source=urllib.parse.unquote(parsed.path[len(prefix):])
        if source.startswith("vitrine/screenshots/"):
            copied.append(source)
            continue
        if source.startswith("/") or ".." in Path(source).parts:
            continue
        suffix=Path(source).suffix.lower()
        if suffix not in (".png",".jpg",".jpeg",".webp"):
            continue
        value=gh.api("GET","/repos/"+owner+"/"+name+"/contents/"
                     +urllib.parse.quote(source,safe="/")+"?ref="+urllib.parse.quote(base_branch,safe=""),
                     missing_ok=True)
        if not isinstance(value,dict) or value.get("encoding")!="base64" or value.get("size",0)>3_000_000:
            continue
        destination="vitrine/screenshots/"+("main" if ix==0 else "extra-"+str(ix))+suffix
        gh.api("PUT","/repos/"+owner+"/"+name+"/contents/"+destination,{
            "branch":PROPOSAL_BRANCH,
            "message":"vitrine: include original project screenshot",
            "content":value["content"].replace("\n",""),
        })
        copied.append(destination)
    meta["screenshots"]=copied
    meta["screenshot_source"]="original-repository-file" if copied else "not-available"
    put("vitrine/meta.json",json.dumps(meta,ensure_ascii=False,indent=2)+"\n","chore: propose vitrine metadata")
    put("vitrine/generated/cover.svg",cover(name,meta["version"],meta["display_mode"],meta["visibility"]),
        "chore: create labeled vitrine schematic cover")
    guide=(ROOT/"docs"/"VITRINE_MEDIA.md").read_text(encoding="utf-8")
    put("vitrine/README.md",guide,"docs: explain screenshot paths and publication standard")
    gh.api("POST","/repos/"+owner+"/"+name+"/pulls",{
        "title":"PL Code Store: create vitrine/ standard",
        "head":PROPOSAL_BRANCH,"base":repo.get("default_branch","main"),
        "body":"Automated proposal. No application code was changed. Review metadata and visual. "
               "Private projects: only an explicitly approved public cover and version may be shown. "
               "Public projects: Merge this PR to grant publication consent without editing JSON. "
               "Private projects still require explicit private metadata permission."})
    return "PR opened"

def scan(gh, owner, state_path, drafts, max_repos=60, max_prs=6,
         open_prs=False, full_scan=False, audit_days=14):
    """Full first-time inventory, incremental subsequent scans and periodic audits.

    State persists through GitHub Actions cache rather than being committed.
    Repository names are hashed in the state to avoid revealing private names.
    A daily cap limits PR creation separately from discovery.
    """
    repos=gh.repos(owner)
    prior=json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    records=prior.get("projects",{}) if isinstance(prior.get("projects",{}),dict) else {}
    now=int(time.time())
    changed=[]
    inspected=skipped=prs=0
    drafts.mkdir(parents=True,exist_ok=True)
    # Prefer new/updated repositories, then older entries due for a periodic audit.
    # Do not interpret pushed_at as proof the vitrine itself was modified.
    def repo_key(r):
        return hashlib.sha256(r["name"].encode("utf-8")).hexdigest()[:24]
    candidates=[]
    for r in repos:
        key=repo_key(r)
        old=records.get(key,{})
        pushed=r.get("pushed_at") or ""
        is_new=not old or old.get("pushed_at")!=pushed
        due=(now-int(old.get("checked_at",0)))>=audit_days*86400
        needs_pr=(old.get("status") in ("waiting_proposal","no personal token",
                                        "PR unavailable") and open_prs and bool(gh.token))
        if full_scan or is_new or due or needs_pr:
            candidates.append((0 if is_new else 1 if needs_pr else 2,r,key,pushed))
        else:
            skipped+=1
    candidates.sort(key=lambda item:(item[0],item[1]["name"].lower()))
    # The number of inspected projects and number of PRs are independent controls.
    for _,repo,key,pushed in candidates[:max_repos]:
        if gh.used+12>gh.budget:break
        name=repo["name"]
        try:
            current=gh.file(owner,name,"vitrine/meta.json")
            if current:
                try:
                    meta=json.loads(current)
                    if not isinstance(meta,dict) or meta.get("id")!=name:
                        raise ValueError("ID mismatch")
                    status="author-owned vitrine"
                except (ValueError,TypeError):
                    status="invalid vitrine"
                    meta=None
            else:
                meta=inferred(repo,gh,owner)
                status="waiting_proposal" if open_prs else "draft"
                if open_prs and prs<max_prs:
                    if not gh.token:
                        status="no personal token"
                    else:
                        try:
                            status=propose(gh,owner,repo,meta)
                            if status=="PR opened":prs+=1
                        except (urllib.error.HTTPError,RuntimeError) as exc:
                            status="PR unavailable"
                            # Never include error payloads from private repos in public logs.
                elif open_prs and prs>=max_prs:
                    status="waiting_proposal"
            inspected+=1
            if isinstance(meta,dict) and not repo.get("private"):
                (drafts/(name+".json")).write_text(
                    json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            records[key]={"pushed_at":pushed,"checked_at":now,"status":status}
            changed.append({"repo":"(private)" if repo.get("private") else name,
                            "status":status,"private":bool(repo.get("private"))})
        except RuntimeError as exc:
            if "budget" in str(exc).lower():break
            raise
    state_path.parent.mkdir(parents=True,exist_ok=True)
    state_path.write_text(json.dumps({"version":2,"projects":records,
        "last_scan":now},indent=2)+"\n",encoding="utf-8")
    return {"total":len(repos),"candidates":len(candidates),"inspected":inspected,
            "skipped_unchanged":skipped,"opened_prs":prs,"requests":gh.used,
            "items":changed}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--owner",default="musikfed")
    p.add_argument("--max-repos",type=int,default=60)
    p.add_argument("--max-prs",type=int,default=6)
    p.add_argument("--budget",type=int,default=350)
    p.add_argument("--propose-prs",action="store_true")
    p.add_argument("--full-scan",action="store_true",help="Recheck all repos, ignoring cached pushed_at")
    p.add_argument("--state",type=Path,default=ROOT/"data"/"discovery-state.json")
    p.add_argument("--drafts",type=Path,default=ROOT/"data"/"drafts")
    a=p.parse_args()
    if not 1<=a.max_repos<=200 or not 0<=a.max_prs<=20 or not 30<=a.budget<=1000:p.error("Invalid limits")
    token=os.getenv("PL_CODESTORE_TOKEN") or os.getenv("GITHUB_TOKEN")
    print(json.dumps(scan(Git(token,a.budget),a.owner,a.state,a.drafts,
                          a.max_repos,a.max_prs,a.propose_prs,full_scan=a.full_scan),ensure_ascii=False,indent=2))
if __name__=="__main__":main()

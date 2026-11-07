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
import json
import os
import re
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

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
    return "0.0.0"

def images(tree,repo):
    if repo.get("private"):return []
    choices=[]
    for node in tree:
        path=node.get("path","")
        if node.get("type")!="blob" or not path.startswith(IMAGE_PREFIX) or not path.lower().endswith(IMAGE_EXT):continue
        if node.get("size",0)>3_000_000 or re.search("secret|password|token|private.key",path,re.I):continue
        score=sum(4 for word in ("dashboard","screen","main","home","overview","preview") if word in path.lower())
        if "/screenshots/" in path or "/showcase/" in path:score+=2
        choices.append((score,path))
    choices.sort(key=lambda x:(-x[0],x[1]))
    owner=repo["owner"]["login"];branch=repo.get("default_branch","main")
    return ["https://raw.githubusercontent.com/"+owner+"/"+repo["name"]+"/"
            +urllib.parse.quote(branch,safe="")+"/"+urllib.parse.quote(path,safe="/")
            for _,path in choices[:3]]

def cover(name,ver,mode):
    """An honest, automatically generated SVG schematic, not an app screenshot."""
    title=html.escape(name[:55]);v=html.escape(ver[:45]);label=html.escape(mode)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675">'
      '<rect width="1200" height="675" fill="#0e1722"/>'
      '<rect x="65" y="65" width="1070" height="545" rx="26" fill="#172936" stroke="#536a7d" stroke-width="2"/>'
      '<path d="M850 240h240v200H850z M970 240v-60 M970 440v60" stroke="#c79c70" stroke-width="5" fill="none"/>'
      '<text x="115" y="133" fill="#deb27d" font-size="24" font-family="monospace">PL CODE STORE / SCHEMATIC COVER</text>'
      '<text x="115" y="294" fill="#f6eade" font-size="52" font-family="Arial" font-weight="bold">'+title+'</text>'
      '<text x="115" y="355" fill="#adbfcc" font-size="26" font-family="Arial">'+label+'</text>'
      '<text x="115" y="520" fill="#8bd4b7" font-size="28" font-family="monospace">VERSION '+v+'</text>'
      '<text x="115" y="568" fill="#879dab" font-size="18" font-family="monospace">DIAGRAM / NOT A SCREENSHOT</text></svg>')

def inferred(repo,gh,owner):
    private=bool(repo.get("private"))
    is_empty=repo.get("size",0)==0
    tree=[] if is_empty else gh.tree(owner,repo["name"],repo.get("default_branch","main"))
    shots=images(tree,repo)
    ver="0.0.0" if is_empty else version(repo,gh,owner)
    mode="development" if is_empty else "interface" if shots else "diagram"
    status="В разработке" if is_empty else "Черновик — ожидает проверки"
    return {"schema_version":"1.0","id":repo["name"],"title":repo["name"],"version":ver,
      "description":(repo.get("description") or "Назначение проекта уточняется автором.")[:350],
      "tags":[repo.get("language") or "Git"],"visibility":"private" if private else "public",
      "publication":"review_required","public_private_approved":False,
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
    put("vitrine/meta.json",json.dumps(meta,ensure_ascii=False,indent=2)+"\n","chore: propose vitrine metadata")
    put("vitrine/generated/cover.svg",cover(name,meta["version"],meta["display_mode"]),
        "chore: create labeled vitrine schematic cover")
    gh.api("POST","/repos/"+owner+"/"+name+"/pulls",{
        "title":"PL Code Store: create vitrine/ standard",
        "head":PROPOSAL_BRANCH,"base":repo.get("default_branch","main"),
        "body":"Automated proposal. No application code was changed. Review metadata and visual. "
               "Private projects: only an explicitly approved public cover and version may be shown. "
               "Edit publication before final display."})
    return "PR opened"

def scan(gh,owner,state_path,drafts,max_repos=7,max_prs=2,open_prs=False):
    repos=gh.repos(owner)
    previous=json.loads(state_path.read_text()) if state_path.exists() else {}
    cursor=int(previous.get("cursor",0))
    changed=[];processed=0;prs=0
    drafts.mkdir(parents=True,exist_ok=True)
    for shift in range(min(len(repos),max_repos)):
        if gh.used+12>gh.budget:break
        repo=repos[(cursor+shift)%len(repos)]
        name=repo["name"]
        current=gh.file(owner,name,"vitrine/meta.json")
        if current:
            try:
                meta=json.loads(current)
                if meta.get("id")!=name:raise ValueError("ID mismatch")
                status="author-owned vitrine"
            except (ValueError,TypeError):
                status="invalid vitrine";meta=None
        else:
            meta=inferred(repo,gh,owner);status="generated draft"
            if open_prs and prs<max_prs:
                try:
                    status=propose(gh,owner,repo,meta)
                    if status=="PR opened":prs+=1
                except (urllib.error.HTTPError,RuntimeError) as exc:
                    status="PR unavailable: "+str(exc)
        processed+=1
        if isinstance(meta,dict):
            (drafts/(name+".json")).write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        changed.append({"repo":name,"status":status,"private":bool(repo.get("private"))})
    state_path.parent.mkdir(parents=True,exist_ok=True)
    state_path.write_text(json.dumps({"cursor":(cursor+processed)%len(repos) if repos else 0,
       "last_scan":int(time.time())},indent=2)+"\n",encoding="utf-8")
    return {"total":len(repos),"inspected":processed,"opened_prs":prs,"requests":gh.used,"items":changed}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--owner",default="musikfed")
    p.add_argument("--max-repos",type=int,default=7)
    p.add_argument("--max-prs",type=int,default=2)
    p.add_argument("--budget",type=int,default=160)
    p.add_argument("--propose-prs",action="store_true")
    p.add_argument("--state",type=Path,default=ROOT/"data"/"discovery-state.json")
    p.add_argument("--drafts",type=Path,default=ROOT/"data"/"drafts")
    a=p.parse_args()
    if not 1<=a.max_repos<=30 or not 0<=a.max_prs<=4 or not 30<=a.budget<=500:p.error("Invalid limits")
    token=os.getenv("PL_CODESTORE_TOKEN") or os.getenv("GITHUB_TOKEN")
    print(json.dumps(scan(Git(token,a.budget),a.owner,a.state,a.drafts,
                          a.max_repos,a.max_prs,a.propose_prs),ensure_ascii=False,indent=2))
if __name__=="__main__":main()

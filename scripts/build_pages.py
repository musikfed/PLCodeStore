#!/usr/bin/env python3
"""Generate GitHub Pages from opt-in vitrine/meta.json of source repositories.

Does NOT read view_my_prj. The only source of truth is each project's own
vitrine/meta.json on its default branch. Private repository content is reduced
to author-approved display fields; an original source link is never published.
"""
from __future__ import annotations
import argparse
import html
import json
import os
import re
import shutil
from pathlib import Path
from urllib.parse import quote, urlsplit
from scripts.auto_vitrine import Git
from scripts.vitrine_cover import cover
from scripts.review_queue import review_items, write_queue

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://musikfed.github.io/PLCodeStore/"
ID_RE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")

def h(value):
    return html.escape(str(value if value is not None else ""),quote=True)

def allowed_picture(value, owner, repo, branch):
    if not isinstance(value,str) or not value.strip():return None
    # Public source media only; private repo images are always omitted.
    parsed=urlsplit(value)
    if parsed.scheme=="https" and parsed.hostname=="raw.githubusercontent.com":
        prefix="/"+owner+"/"+repo+"/"+quote(branch,safe="")+"/"
        if parsed.path.startswith(prefix) and parsed.username is None:
            return value
    if not parsed.scheme and not value.startswith(("/","\\")) and ".." not in Path(value).parts:
        if re.fullmatch(r"[A-Za-z0-9_./ -]+\.(png|jpg|jpeg|webp|svg)",value,re.I):
            return "https://raw.githubusercontent.com/"+owner+"/"+repo+"/"+quote(branch,safe="")+"/"+quote(value,safe="/")
    return None

def approved_record(repo: dict, raw: dict):
    """Allowlist what GitHub Pages may receive from one approved source."""
    if not isinstance(raw,dict) or raw.get("publication") not in ("approved", "publish_on_merge"):return None
    if raw.get("visibility")=="internal":return None
    if raw.get("id")!=repo.get("name") or not ID_RE.fullmatch(str(raw.get("id",""))):
        return None
    private=bool(repo.get("private")) or raw.get("visibility")=="private"
    if private and raw.get("public_private_approved") is not True:return None
    title=str(raw.get("title") or repo["name"])[:180]
    version=str(raw.get("version") or "—")[:65]
    status=str(raw.get("status") or ("В разработке" if repo.get("size",0)==0 else "Продукт"))[:150]
    # A merged proposal is no longer waiting for the author's review.
    if status=="Черновик — ожидает проверки":status="В разработке"
    elif status=="Активная разработка · ожидает решения автора":status="Активная разработка"
    description=str(raw.get("description") or "")[:1000]
    mode=str(raw.get("display_mode") or ("development" if repo.get("size",0)==0 else "diagram"))
    tags=[str(x)[:60] for x in raw.get("tags",[])[:12] if isinstance(x,str)]
    record={"id":repo["name"],"title":title,"version":version,"status":status,
            "description":description,"tagline":description[:150],"tags":tags,
            "kind":tags[0] if tags else "Software","created_at":str(repo.get("created_at") or ""),
            "visibility":"private" if private else "public","display_mode":mode,
            "image":None,"images":[],"repo_url":None if private else repo.get("html_url")}
    if not private:
        shots=raw.get("screenshots",[])
        if not isinstance(shots,list):shots=[]
        for item in shots[:8]:
            img=allowed_picture(item,repo["owner"]["login"],repo["name"],repo.get("default_branch","main"))
            if img and img not in record["images"]:
                record["images"].append(img)
        if record["images"]:
            record["image"]=record["images"][0]
    return record

def collect(gh: Git, owner: str, max_repos: int = 120, repositories=None):
    accepted=[]
    repositories=repositories if repositories is not None else gh.repos(owner)
    for repo in repositories[:max_repos]:
        if gh.used+2>=gh.budget:break
        rawtext=gh.file(owner,repo["name"],"vitrine/meta.json")
        if rawtext is None:continue
        try:
            raw=json.loads(rawtext)
            card=approved_record(repo,raw)
        except (ValueError,TypeError,KeyError):
            continue
        if card is not None:accepted.append(card)
    return sorted(accepted,key=lambda x:x["created_at"],reverse=True)

def image_markup(p, prefix):
    if p.get("image") and p["visibility"]=="public":
        return '<img loading="lazy" decoding="async" src="'+h(p["image"])+'" alt="Экран проекта '+h(p["title"])+'">'
    return '<img loading="lazy" decoding="async" src="'+h(prefix)+'assets/covers/'+quote(p["id"])+'.svg" alt="Дизайнерская обложка '+h(p["title"])+'">'

def card_html(p):
    pid=h(p["id"])
    search=h(" ".join([p["title"],p["description"],p["kind"],*p["tags"]]))
    return ('<article class="product-card" data-title="'+h(p["title"])+'" data-search="'+search+'" data-created="'+h(p["created_at"])+'" data-kind="'+h(p["kind"])+'">'
        '<a class="product-image" href="projects/'+pid+'/" aria-label="Продукт '+h(p["title"])+'">'+image_markup(p,"")
        +'<span class="source-ribbon">VITRINE / '+("CLOSED SOURCE" if p["visibility"]=="private" else "OPEN SOURCE")+'</span></a>'
        '<div class="product-body"><div class="product-meta">'+h(p["kind"])+' · '+h(p["status"])+'</div>'
        '<h3>'+h(p["title"])+'</h3><p>'+h(p["description"][:150])+'</p>'
        '<div class="product-links"><a href="projects/'+pid+'/">Открыть презентацию ↗</a><span>'+h(p["version"])+'</span></div></div></article>')

def details_html(p):
    pid=h(p["id"])
    cta=(' <a href="'+h(p["repo_url"])+'" target="_blank" rel="noopener noreferrer">Исходный код ↗</a>'
         if p["visibility"]=="public" and p.get("repo_url") else "")
    return ('<!doctype html><html lang="ru"><head><meta charset="utf-8">'
      '<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark">'
      '<title>'+h(p["title"])+' · PL Code Store</title><meta name="description" content="'+h(p["description"][:160])+'">'
      '<link rel="canonical" href="'+BASE+'projects/'+pid+'/">'
      '<link rel="icon" href="../../assets/icon.svg" type="image/svg+xml">'
      '<link rel="stylesheet" href="../../assets/detail.css"></head>'
      '<body><header><a class="back" href="../../">← PL CODE STORE</a><span>PRODUCT VITRINE / '+pid+'</span></header>'
      '<main><div class="eyebrow">PRESENTATION · '+h(p["kind"])+'</div><h1>'+h(p["title"])+'</h1>'
      '<p class="intro">'+h(p["description"])+'</p><div class="scene">'+image_markup(p,"../../")+'</div>'
      '<div class="project-screens">'+''.join('<figure><img loading="lazy" decoding="async" src="'+h(img)+'" alt="Изображение проекта '+h(p["title"])+'"><figcaption>Материал из vitrine/ проекта</figcaption></figure>' for img in p.get("images",[])[1:6])+'</div>'
      '<div class="metadata"><div><small>ВЕРСИЯ</small><p>'+h(p["version"])+'</p></div>'
      '<div><small>СТАТУС</small><p>'+h(p["status"])+'</p></div>'
      '<div><small>ТИП</small><p>'+("Закрытый код" if p["visibility"]=="private" else "Открытый код")+'</p></div></div>'
      '<nav><a href="../../#gallery">← Все продукты</a>'+cta+'</nav>'
      '<p class="note">Данные представлены по авторскому стандарту vitrine/meta.json. '
      'Обложки — самостоятельная графика, не имитация интерфейса.</p></main>'
      '<footer><a href="../../">PL CODE STORE</a><span>Маркетинг — это папка.</span></footer></body></html>')

def build(projects: list[dict], output: Path, review=None):
    out=Path(output).resolve()
    out.mkdir(parents=True,exist_ok=True)
    shutil.copytree(ROOT/"docs"/"assets",out/"assets",dirs_exist_ok=True)
    template=(ROOT/"templates"/"public_index.html").read_text(encoding="utf-8")
    for marker in ("<!--PROJECT_CARDS-->","<!--PROJECT_COUNT-->","<!--CATEGORY_OPTIONS-->"):
        if marker not in template:raise ValueError("Marketing template marker missing: "+marker)
    kinds=sorted({x["kind"] for x in projects})
    options="".join('<option value="'+h(k)+'">'+h(k)+'</option>' for k in kinds)
    page=(template.replace("<!--PROJECT_CARDS-->","\n".join(card_html(p) for p in projects))
         .replace("<!--PROJECT_COUNT-->",str(len(projects)))
         .replace("<!--CATEGORY_OPTIONS-->",options))
    (out/"index.html").write_text(page,encoding="utf-8")
    (out/"review").mkdir(exist_ok=True)
    shutil.copyfile(ROOT/"templates"/"review_index.html",out/"review"/"index.html")
    write_queue(out, review or [])
    (out/"data").mkdir(exist_ok=True)
    (out/"data"/"projects.json").write_text(
        json.dumps({"source":"author-approved vitrine/meta.json from GitHub","projects":projects},
                   ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"assets"/"covers").mkdir(parents=True,exist_ok=True)
    urls=[BASE]
    for p in projects:
        if not ID_RE.fullmatch(p["id"]):raise ValueError("Invalid project ID")
        name=p["id"]
        (out/"assets"/"covers"/(name+".svg")).write_text(
            cover(p["title"],p["version"],p["display_mode"],p["visibility"],p["kind"]),
            encoding="utf-8")
        dest=out/"projects"/name
        dest.mkdir(parents=True,exist_ok=True)
        (dest/"index.html").write_text(details_html(p),encoding="utf-8")
        urls.append(BASE+"projects/"+quote(name)+"/")
    (out/"robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: "+BASE+"sitemap.xml\n",encoding="utf-8")
    (out/"sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
      +"\n".join("<url><loc>"+html.escape(url)+"</loc></url>" for url in urls)
      +'\n</urlset>\n',encoding="utf-8")
    (out/".nojekyll").write_text("",encoding="utf-8")
    return len(projects)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--owner",default="musikfed")
    parser.add_argument("--out",type=Path,default=ROOT/"_site")
    parser.add_argument("--budget",type=int,default=160)
    parser.add_argument("--max-repos",type=int,default=120)
    args=parser.parse_args()
    token=os.getenv("PL_CODESTORE_TOKEN") or os.getenv("GITHUB_TOKEN")
    gh=Git(token,budget=args.budget)
    repos=gh.repos(args.owner)
    items=collect(gh,args.owner,args.max_repos,repositories=repos)
    # Public review queue comes from genuine open source-repo PRs,
    # never from the mockup and never from private repositories.
    pending=review_items(gh,args.owner,repos,args.max_repos)
    build(items,args.out,review=pending)
    print("Published",len(items),"approved products; review queue",len(pending))
if __name__=="__main__":main()

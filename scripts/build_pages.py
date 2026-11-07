#!/usr/bin/env python3
"""Build the public PL Code Store Pages entirely inside Git CI.
Only the already-public, author-curated view_my_prj catalog is imported.
No repository code or private metadata is accessed or executed.
"""
from __future__ import annotations
import argparse
import html
import json
import re
import shutil
import urllib.request
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = "https://raw.githubusercontent.com/musikfed/view_my_prj/main/docs/data/projects.json"
BASE = "https://musikfed.github.io/PLCodeStore/"
KIND = {"writing":"Книги и контент","music":"Музыка","factory":"Системы сборки","arcade":"Игры и зрение","robot":"Робототехника","storage":"Инженерные инструменты","camera":"Камеры","linux":"Операционные системы","electronics":"Электроника","infra":"Инфраструктура","analytics":"Аналитика","reserved":"Идеи и прототипы"}
ALLOWED = {"id","title","tagline","description","kind","status","image","preview","stack","created_at"}
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}T")

def h(value):
    return html.escape(str(value if value is not None else ""), quote=True)

def prepare(source):
    if not isinstance(source, dict) or source.get("publishedOnly") is not True:
        raise ValueError("Only an explicitly published public catalog can be imported")
    projects = source.get("projects")
    if not isinstance(projects, list):
        raise ValueError("Missing projects array")
    result = []
    seen = set()
    for raw in projects:
        if not isinstance(raw, dict):
            raise ValueError("Invalid project")
        if raw.get("visibility") in ("private", "internal") or raw.get("publication") == "disabled":
            continue
        p = {key: raw[key] for key in ALLOWED if key in raw}
        pid = p.get("id")
        if not isinstance(pid, str) or not ID.fullmatch(pid) or pid in seen:
            raise ValueError("Invalid or repeated ID: " + repr(pid))
        if not all(isinstance(p.get(k), str) and p.get(k) for k in ("title", "description", "kind")):
            raise ValueError("Missing public metadata: " + pid)
        seen.add(pid)
        p["title"] = p["title"][:180]
        p["description"] = p["description"][:1000]
        p["tagline"] = str(p.get("tagline") or "")[:190]
        p["status"] = str(p.get("status") or "")[:200]
        p["stack"] = [v[:60] for v in p.get("stack", [])[:16] if isinstance(v, str)]
        p["created_at"] = str(p.get("created_at") or "")
        if p["created_at"] and not DATE.match(p["created_at"]):
            p["created_at"] = ""
        if not isinstance(p.get("image"), str) or not p["image"].startswith("https://raw.githubusercontent.com/musikfed/"):
            p.pop("image", None)
        if not isinstance(p.get("preview"), str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", p["preview"]):
            p.pop("preview", None)
        result.append(p)
    return sorted(result, key=lambda p:p["created_at"], reverse=True)

def media(p):
    title=h(p["title"])
    if p.get("image"):
        return '<img loading="lazy" decoding="async" src="'+h(p["image"])+'" alt="Настоящий экран проекта '+title+'">'
    if p.get("preview"):
        url="https://musikfed.github.io/view_my_prj/previews/"+quote(p["preview"])+"/"
        return '<iframe loading="lazy" tabindex="-1" sandbox="" aria-label="Статическое превью '+title+'" src="'+h(url)+'"></iframe>'
    return '<div class="code-cover"><span>SOURCE CODE / DOCUMENTATION</span><strong>'+title+'</strong><span>NO FABRICATED SCREENS</span></div>'

def card(p):
    pid=h(p["id"])
    label=h(KIND.get(p["kind"], p["kind"]))
    search=h(" ".join((p["title"],p["description"],p["kind"]," ".join(p["stack"]))))
    d=h(p["created_at"][:10])
    return ('<article class="product-card" data-title="'+h(p["title"])+'" data-search="'+search+'" data-created="'+d+'" data-kind="'+h(p["kind"])+'">'
            '<a class="product-image" href="projects/'+pid+'/" aria-label="Подробнее: '+h(p["title"])+'">'+media(p)+'<span class="source-ribbon">VERIFIED SOURCE</span></a>'
            '<div class="product-body"><div class="product-meta">'+label+' · '+h(p["status"])+'</div><h3>'+h(p["title"])+'</h3><p>'+h(p["tagline"] or p["description"][:145])+'</p>'
            '<div class="product-links"><a href="projects/'+pid+'/">Открыть карточку ↗</a><span>'+d+'</span></div></div></article>')

def detail(p):
    pid=h(p["id"])
    repo="https://github.com/musikfed/"+quote(p["id"])
    old="https://musikfed.github.io/view_my_prj/projects/"+quote(p["id"])+"/"
    if p["id"]=="pitools":
        old="https://musikfed.github.io/view_my_prj/pitools/"
    return ('<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
      '<meta name="color-scheme" content="dark"><meta name="robots" content="index,follow"><title>'+h(p["title"])+' · PL Code Store</title>'
      '<meta name="description" content="'+h(p["description"][:160])+'"><link rel="canonical" href="'+BASE+'projects/'+pid+'/">'
      '<link rel="icon" href="../../assets/icon.svg" type="image/svg+xml"><link rel="stylesheet" href="../../assets/detail.css"></head>'
      '<body><header><a class="back" href="../../">← PL CODE STORE</a><span>PROJECT / '+pid+'</span></header><main>'
      '<div class="eyebrow">SOURCE-BACKED PROJECT · '+h(KIND.get(p["kind"],p["kind"]))+'</div><h1>'+h(p["title"])+'</h1>'
      '<p class="intro">'+h(p["description"])+'</p><div class="scene">'+media(p)+'</div><div class="metadata">'
      '<div><small>СТАТУС</small><p>'+h(p["status"])+'</p></div><div><small>ТЕХНОЛОГИИ</small><p>'+h(" · ".join(p["stack"]))+'</p></div>'
      '<div><small>СОЗДАН</small><p>'+h(p["created_at"][:10])+'</p></div></div><nav>'
      '<a href="'+h(repo)+'" rel="noopener noreferrer" target="_blank">Исходный репозиторий ↗</a>'
      '<a href="'+h(old)+'" rel="noopener noreferrer" target="_blank">Оригинальная витрина ↗</a><a href="../../#gallery">Все проекты</a></nav>'
      '<p class="note">Демонстрационная страница PL Code Store, основанная на уже опубликованных данных PEGINELAB. '
      'Прототипы, форки и экспериментальные разработки не выдаются за готовые коммерческие продукты.</p></main>'
      '<footer><a href="../../">PL CODE STORE</a><span>Маркетинг — это папка. Публикация — решение автора.</span></footer></body></html>')

def build(projects, out):
    out=Path(out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    shutil.copytree(ROOT/"docs"/"assets",out/"assets",dirs_exist_ok=True)
    template=(ROOT/"templates"/"public_index.html").read_text(encoding="utf-8")
    cats=sorted({p["kind"] for p in projects},key=lambda k:KIND.get(k,k))
    options="".join('<option value="'+h(k)+'">'+h(KIND.get(k,k))+'</option>' for k in cats)
    for token in ("<!--PROJECT_CARDS-->","<!--PROJECT_COUNT-->","<!--CATEGORY_OPTIONS-->"):
        if token not in template:raise ValueError("Missing template placeholder: "+token)
    page=template.replace("<!--PROJECT_CARDS-->","\n".join(card(p) for p in projects)).replace("<!--PROJECT_COUNT-->",str(len(projects))).replace("<!--CATEGORY_OPTIONS-->",options)
    (out/"index.html").write_text(page,encoding="utf-8")
    (out/"data").mkdir(exist_ok=True)
    (out/"data"/"projects.json").write_text(json.dumps({"source":UPSTREAM,"import_type":"curated_public","projects":projects},ensure_ascii=False,indent=2),encoding="utf-8")
    urls=[BASE]
    for p in projects:
        loc=out/"projects"/p["id"]
        loc.mkdir(parents=True,exist_ok=True)
        (loc/"index.html").write_text(detail(p),encoding="utf-8")
        urls.append(BASE+"projects/"+quote(p["id"])+"/")
    (out/"robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: "+BASE+"sitemap.xml\n",encoding="utf-8")
    (out/"sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+"\n".join("<url><loc>"+html.escape(u,quote=False)+"</loc></url>" for u in urls)+"\n</urlset>\n",encoding="utf-8")
    (out/".nojekyll").write_text("",encoding="utf-8")

def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--refresh",action="store_true")
    arg.add_argument("--out",type=Path,default=ROOT/"docs")
    arg.add_argument("--source",type=Path,default=ROOT/"data"/"catalog-source.json")
    args=arg.parse_args()
    if args.refresh:
        req=urllib.request.Request(UPSTREAM,headers={"User-Agent":"PLCodeStore-Pages/0.1"})
        with urllib.request.urlopen(req,timeout=20) as response:
            source=json.loads(response.read(1_000_000).decode("utf-8"))
    else:
        source=json.loads(args.source.read_text(encoding="utf-8"))
    projects=prepare(source)
    if not projects:raise ValueError("No authorized public records")
    build(projects,args.out)
    print("Built",len(projects),"public product pages in",args.out)

if __name__=="__main__":
    main()

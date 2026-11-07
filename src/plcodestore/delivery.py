"""Build escaped, offline-ready static HTML from published snapshots only."""
from __future__ import annotations
import json
import re
from pathlib import Path
from jinja2 import Environment, select_autoescape
from .standards import public_snapshot

_TEMPLATE="""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Software products reviewed by their authors"><title>{{ title }}</title>
<style>body{font:16px/1.55 system-ui;background:#0b1119;color:#eff4f9;margin:0}header,main,footer{max-width:1150px;margin:auto;padding:28px 20px}header{border-bottom:1px solid #283545}h1{letter-spacing:-.04em;font-size:clamp(2rem,5vw,4rem);margin:.2em 0}p{color:#aebdca}section{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:18px}article{background:#141f2b;border:1px solid #344253;border-radius:16px;padding:20px;min-width:0}a{color:#8addd8}input{border:1px solid #668094;background:#101b27;color:#fff;padding:12px;border-radius:9px;width:min(100%,410px);box-sizing:border-box}small{color:#bdb1a0}img{max-width:100%;border-radius:10px}nav{display:flex;gap:16px}</style>
</head><body><header><small>PL CODE STORE · APPROVED RELEASES</small><h1>{{ title }}</h1><p>Маркетинг — это папка. Публикация — это решение автора.</p><input id="search" placeholder="Найти проект..." aria-label="Поиск проекта"></header>
<main><section id="catalog">{% for p in projects %}<article data-search="{{ (p.title ~ ' ' ~ p.description ~ ' ' ~ p.tags|join(' '))|lower }}">
<h2><a href="projects/{{ p.id }}/">{{ p.title }}</a></h2><small>{{ p.version }} · {{ p.tags|join(' · ') }}</small><p>{{ p.description }}</p>
<nav>{% if p.repo_url %}<a href="{{ p.repo_url }}" rel="noopener noreferrer">Исходники</a>{% endif %}{% if p.demo_url %}<a href="{{ p.demo_url }}" rel="noopener noreferrer">Демо</a>{% endif %}</nav></article>{% endfor %}</section></main>
<footer>PL Code Store · Only author-approved publication snapshots</footer>
<script>document.querySelector('#search').addEventListener('input',e=>{const q=e.target.value.toLocaleLowerCase();document.querySelectorAll('#catalog article').forEach(c=>c.hidden=!c.dataset.search.includes(q))})</script>
</body></html>"""
_DETAIL="""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ p.title }}</title><meta name="description" content="{{ p.description[:160] }}"><style>body{background:#0b1119;color:#eff4f9;font:16px/1.65 system-ui;max-width:780px;padding:30px;margin:auto}a{color:#8addd8}img{max-width:100%;border-radius:14px}p{color:#bdcbd8}</style></head><body><a href="../../">← Каталог</a><h1>{{ p.title }}</h1><p>{{ p.description }}</p><p>Версия {{ p.version }} · {{ p.tags|join(', ') }}</p>{% if p.repo_url %}<p><a href="{{ p.repo_url }}" rel="noopener noreferrer">Исходный код</a></p>{% endif %}{% if p.demo_url %}<p><a href="{{ p.demo_url }}" rel="noopener noreferrer">Демонстрация</a></p>{% endif %}</body></html>"""

def build(published: list[dict], destination: Path, title: str="PL Code Store"):
    destination=Path(destination)
    env=Environment(autoescape=select_autoescape(["html"]))
    projects=[]
    for item in published:
        # Revalidate even if data entered from other sources
        if item.get("publication")=="approved":
            item=public_snapshot(item)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", item.get("id","")):
            raise ValueError("Invalid project identifier")
        projects.append(item)
    destination.mkdir(parents=True, exist_ok=True)
    (destination/"index.html").write_text(env.from_string(_TEMPLATE).render(projects=projects,title=title),encoding="utf-8")
    for p in projects:
        location=destination/"projects"/p["id"]
        location.mkdir(parents=True,exist_ok=True)
        (location/"index.html").write_text(env.from_string(_DETAIL).render(p=p),encoding="utf-8")
    (destination/"registry.json").write_text(json.dumps(projects,ensure_ascii=False,indent=2),encoding="utf-8")
    (destination/"robots.txt").write_text("User-agent: *\nAllow: /\n",encoding="utf-8")
    return len(projects)

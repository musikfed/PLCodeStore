"""Local-only review UI; cross-origin calls are refused."""
from __future__ import annotations
import html
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from .review import ReviewStore, CHECKS

app=FastAPI(title="PL Code Store Review Studio",version="0.1.0")
_store: ReviewStore | None = None

def configure(db_path: Path):
    global _store
    _store=ReviewStore(db_path)

def store():
    global _store
    if _store is None:
        configure(Path.home()/".local"/"share"/"plcodestore"/"review.sqlite3")
    return _store

class Decision(BaseModel):
    digest: str
    action: str
    comment: str = Field(default="",max_length=4000)
    checks: list[str] = Field(default_factory=list)

@app.middleware("http")
async def local_only(request: Request, call_next):
    # Defensive origin guard; network binding must also be loopback only.
    origin=request.headers.get("origin")
    if origin:
        from urllib.parse import urlsplit
        o=urlsplit(origin)
        if o.hostname not in ("localhost","127.0.0.1","::1"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail":"Cross-origin write refused"},status_code=403)
    return await call_next(request)

@app.get("/api/cards")
def cards():
    return {"cards":store().cards(),"checks":CHECKS}

@app.post("/api/cards/{project_id}/decision")
def decision(project_id: str, body: Decision):
    try:
        store().decide(project_id,body.digest,body.action,body.comment,body.checks)
    except KeyError:
        raise HTTPException(status_code=404,detail="Unknown project")
    except ValueError as exc:
        raise HTTPException(status_code=409,detail=str(exc))
    return {"ok":True}

@app.post("/api/cards/{project_id}/publish")
def publish(project_id: str):
    try:
        item=store().publish(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=409,detail=str(exc))
    return {"ok":True,"published":item["id"]}

@app.get("/api/cards/{project_id}/history")
def history(project_id: str):
    return {"history":store().history(project_id)}

@app.get("/",response_class=HTMLResponse)
def index():
    return """<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PL Code Store · Review Studio</title>
<style>:root{color-scheme:dark}body{background:#0b111a;color:#f5f0e7;font:16px/1.5 system-ui;margin:0}main{max-width:880px;margin:2rem auto;padding:0 1rem}header{display:flex;justify-content:space-between;align-items:center}small{color:#9cacbb}article{border:1px solid #354658;background:linear-gradient(145deg,#162635,#111923);border-radius:22px;padding:28px;box-shadow:0 20px 70px #0005;margin-top:20px;touch-action:pan-y}h1{font-size:clamp(2rem,5vw,3rem);margin:0}h2{font-size:2rem;margin:.3em 0}p{color:#b9c5d0}button{border:1px solid #617081;border-radius:12px;padding:13px 18px;color:white;background:#253748;font-weight:650;cursor:pointer}button:disabled{opacity:.4;cursor:not-allowed}button.yes{background:#1a7757}button.no{background:#7c3645}button.later{background:#33435c}.actions{display:flex;gap:10px;flex-wrap:wrap}label{display:block;padding:7px}textarea{box-sizing:border-box;width:100%;min-height:90px;background:#0b1520;color:white;border:1px solid #546477;border-radius:8px;padding:12px}section{display:grid;grid-template-columns:1fr 1fr}code{color:#e9b76d}a{color:#8addd8}@media(max-width:500px){section{grid-template-columns:1fr}article{padding:18px}}</style></head>
<body><main><header><div><small>PEGINELAB · LOCAL REVIEW</small><h1>PL Code Store</h1><p>❤️ вправо — одобрить · 🛑 влево — на доработку · ⏳ позже</p></div><small id="counter"></small></header><article id="card" aria-live="polite"></article><p id="feedback" role="status"></p></main>
<script>
const checks=['identity','description','real_screenshots','working_links','privacy','security','seo'];
const labels=['Название','Описание','Настоящие скриншоты','Рабочие ссылки','Приватность','Безопасность','SEO'];
let queue=[], current=0, touch=0;
const card=document.getElementById('card'), feedback=document.getElementById('feedback');
function esc(x){return String(x??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]))}
async function reload(){const d=await (await fetch('/api/cards')).json();queue=d.cards.filter(c=>c.state!=='published'&&c.state!=='approved');current=0;render()}
function render(){document.getElementById('counter').textContent=queue.length?(current+1)+' / '+queue.length:'0';if(current>=queue.length){card.innerHTML='<h2>Очередь проверена</h2><p>Новых черновиков нет. Одобренные карточки ожидают отдельной публикации через CLI или API.</p><button onclick="reload()">Обновить</button>';return}
const c=queue[current],m=c.meta;card.innerHTML='<small>'+esc(c.state)+' · '+esc(m.version)+' · '+esc(m.visibility)+'</small><h2>'+esc(m.title)+'</h2><p>'+esc(m.description)+'</p><p><code>'+esc((m.tags||[]).join(' · '))+'</code></p><section>'+checks.map((k,i)=>'<label><input type="checkbox" value="'+k+'"> '+labels[i]+'</label>').join('')+'</section><p><textarea id="comment" placeholder="Что необходимо доработать?"></textarea></p><div class="actions"><button class="no" id="reject">🛑 Влево</button><button class="later" id="defer">⏳ Позже</button><button class="yes" id="approve">❤️ Вправо</button></div><small>Одобрение не публикует проект. Для приватных карточек требуется отдельное разрешение.</small>';
document.getElementById('reject').onclick=()=>act('changes_requested');document.getElementById('defer').onclick=()=>act('deferred');document.getElementById('approve').onclick=()=>act('approved')}
async function act(action){const c=queue[current];if(!c)return;const comment=document.getElementById('comment').value;const selected=Array.from(card.querySelectorAll('input:checked')).map(x=>x.value);if(action==='changes_requested'&&!comment.trim()){feedback.textContent='Для доработки обязательно напиши замечание';return}if(action==='approved'&&selected.length!==checks.length){feedback.textContent='Перед одобрением проверь все пункты';return}
const r=await fetch('/api/cards/'+encodeURIComponent(c.id)+'/decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({digest:c.digest,action,comment,checks:selected})});if(!r.ok){feedback.textContent=(await r.json()).detail;return}feedback.textContent=action==='approved'?'Карточка одобрена; публикация отдельно':action==='deferred'?'Отложено':'Отправлено на доработку';current++;render()}
card.addEventListener('touchstart',e=>touch=e.touches[0].clientX,{passive:true});
card.addEventListener('touchend',e=>{if(!queue[current])return;const delta=e.changedTouches[0].clientX-touch;if(Math.abs(delta)>110){if(delta>0)act('approved');else act('changes_requested')}},{passive:true});
document.addEventListener('keydown',e=>{if(e.target.matches('input,textarea'))return;if(e.key==='ArrowRight')act('approved');if(e.key==='ArrowLeft')act('changes_requested');if(e.key==='ArrowDown')act('deferred')});
reload().catch(e=>feedback.textContent=String(e));
</script></body></html>"""

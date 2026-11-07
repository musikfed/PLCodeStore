(()=>{'use strict';
const cards=Array.from(document.querySelectorAll('#catalog-grid .product-card'));
const search=document.getElementById('catalog-search');
const kind=document.getElementById('catalog-kind');
const sort=document.getElementById('catalog-sort');
const grid=document.getElementById('catalog-grid');
const count=document.getElementById('visible-count');
const empty=document.getElementById('catalog-empty');
const normalize=v=>String(v||'').toLocaleLowerCase('ru');
function updateCatalog(){
 if(!grid)return;
 const q=normalize(search?.value).trim();
 const category=kind?.value||'all';
 const order=sort?.value||'newest';
 const arranged=cards.slice().sort((a,b)=>{
  if(order==='name')return a.dataset.title.localeCompare(b.dataset.title,'ru');
  const d=(a.dataset.created||'').localeCompare(b.dataset.created||'');
  return order==='oldest'?d:-d;
 });
 let n=0;
 for(const item of arranged){
  const match=(!q||normalize(item.dataset.search).includes(q))&&(category==='all'||item.dataset.kind===category);
  item.hidden=!match;if(match)n++;
  grid.appendChild(item);
 }
 if(count)count.textContent=String(n);
 if(empty)empty.hidden=n!==0;
 try{sessionStorage.setItem('plcs-search',search.value);sessionStorage.setItem('plcs-category',category);sessionStorage.setItem('plcs-sort',order);}catch(_){}
}
if(grid){
 try{if(search)search.value=sessionStorage.getItem('plcs-search')||'';
 const c=sessionStorage.getItem('plcs-category'),s=sessionStorage.getItem('plcs-sort');
 if(c&&Array.from(kind.options).some(o=>o.value===c))kind.value=c;
 if(s&&['newest','oldest','name'].includes(s))sort.value=s;
 }catch(_){}
 [search,kind,sort].forEach(x=>x?.addEventListener(x===search?'input':'change',updateCatalog));
 updateCatalog();
}
const demoData=[
 {title:'ACHEWIW',version:'v0.9',desc:'Типография и редактор книг — настоящий авторский проект.',tags:['Python','Ollama','FastAPI']},
 {title:'YadroKreator',version:'v0.1',desc:'Инструменты сборки ядер и прошивок для инженерных стендов.',tags:['Linux','Python','Buildroot']},
 {title:'Pocket Orchestra',version:'v0.1',desc:'Алгоритмическая студия музыкальной композиции и аранжировки.',tags:['Python','MIDI','MusicXML']}
];
const rules=[['title','Название'],['description','Описание'],['screens','Настоящие материалы'],['links','Рабочие ссылки'],['privacy','Приватность'],['security','Безопасность'],['seo','SEO']];
const el=document.getElementById('review-surface');
const number=document.getElementById('demo-count');
let decisions={};let comments={};let current=0;let sx=null;
try{const saved=JSON.parse(localStorage.getItem('plcs-review-demo')||'{}');
 if(saved&&typeof saved==='object'){decisions=saved.decisions||{};comments=saved.comments||{};}
}catch(_){}
function persist(){try{localStorage.setItem('plcs-review-demo',JSON.stringify({decisions,comments}));}catch(_){}}
function next(){current=0;while(current<demoData.length&&decisions[current])current++;}
function esc(v){return String(v||'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[x]));}
function render(){
 if(!el)return;next();number.textContent=String(Math.min(current+1,demoData.length)).padStart(2,'0')+' / 0'+demoData.length;
 if(current>=demoData.length){
  const yes=Object.values(decisions).filter(x=>x==='yes').length;
  const no=Object.values(decisions).filter(x=>x==='no').length;
  const later=Object.values(decisions).filter(x=>x==='later').length;
  el.innerHTML='<div class="demo-done"><div><div style="font-size:3rem;color:#74d3a9">✓</div><b>Очередь проверена</b><p>'+yes+' одобрено · '+no+' на доработку · '+later+' отложено</p><p>Решения сохранены только в вашем браузере. Это демонстрация, не реальная публикация.</p><button id="demo-reset">Начать заново</button><button id="demo-undo" style="margin:7px">Отменить последнее</button></div></div>';
  el.querySelector('#demo-reset').onclick=()=>{decisions={};comments={};current=0;persist();render();};
  el.querySelector('#demo-undo').onclick=undo;return;
 }
 const c=demoData[current];
 el.innerHTML='<div class="review-card-header"><small>PROJECT / '+String(current+1).padStart(2,'0')+'</small><b>● READY FOR REVIEW</b></div><h3 class="review-card-title">'+esc(c.title)+'</h3><p class="review-card-desc">'+esc(c.desc)+'</p><div class="review-tags">'+c.tags.map(t=>'<span>'+esc(t)+'</span>').join('')+'<span>'+esc(c.version)+'</span></div><div class="checks-title">ПРОВЕРКА ПЕРЕД ОДОБРЕНИЕМ</div><div class="checks-grid">'+rules.map(([k,label])=>'<label><input type="checkbox" name="'+k+'"> '+esc(label)+'</label>').join('')+'</div><textarea class="demo-comment" id="demo-comment" placeholder="Комментарий для доработки (обязателен при отклонении)"></textarea><div class="demo-actions"><button type="button" class="reject" id="demo-reject">✕ Стоп</button><button type="button" class="defer" id="demo-defer">◷ Позже</button><button type="button" class="approve" id="demo-approve" disabled>♥ Да</button></div><small class="demo-feedback" id="demo-feedback" role="status"></small><div style="text-align:right"><button type="button" id="demo-undo" style="border:0;background:transparent;color:#91a6b2;font-size:.68rem">↶ отменить последнее</button></div>';
 const approve=el.querySelector('#demo-approve');
 el.querySelectorAll('input[type=checkbox]').forEach(i=>i.addEventListener('change',()=>{
  approve.disabled=el.querySelectorAll('input[type=checkbox]:checked').length!==rules.length;
 }));
 el.querySelector('#demo-reject').onclick=()=>decide('no');
 el.querySelector('#demo-defer').onclick=()=>decide('later');
 approve.onclick=()=>decide('yes');
 el.querySelector('#demo-undo').onclick=undo;
}
function decide(choice){
 if(!el||current>=demoData.length)return;
 const fb=el.querySelector('#demo-feedback');
 const msg=el.querySelector('#demo-comment')?.value.trim()||'';
 if(choice==='no'&&!msg){fb.textContent='Укажи, что именно нужно исправить.';el.querySelector('#demo-comment')?.focus();return;}
 if(choice==='yes'&&el.querySelectorAll('input[type=checkbox]:checked').length!==rules.length){fb.textContent='Сначала проверь все семь пунктов.';return;}
 decisions[current]=choice;comments[current]=msg;persist();render();
}
function undo(){
 const keys=Object.keys(decisions).map(Number).filter(Number.isFinite).sort((a,b)=>b-a);
 if(!keys.length)return;
 delete decisions[keys[0]];delete comments[keys[0]];persist();render();
}
if(el){
 render();
 el.addEventListener('pointerdown',e=>{if(e.target.closest('button,input,textarea,a'))return;sx=e.clientX;});
 el.addEventListener('pointerup',e=>{if(sx===null)return;const dx=e.clientX-sx;sx=null;if(Math.abs(dx)<100)return;decide(dx>0?'yes':'no');});
 document.addEventListener('keydown',e=>{if(document.activeElement&&/^(INPUT|TEXTAREA|SELECT|BUTTON)$/.test(document.activeElement.tagName))return;
  if(e.key==='ArrowRight')decide('yes');else if(e.key==='ArrowLeft')decide('no');else if(e.key==='ArrowDown')decide('later');
 });
}
document.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',()=>{}));
})();
/* Real public PR queue: GitHub credentials never enter this page. */
(()=>{'use strict';
const checks=[
 ['meaning','Название и описание соответствуют проекту'],
 ['visual','Внешний вид и обложка подходят'],
 ['publication','Информацию разрешено публиковать (без секретов и личных контактов)']];
const work=document.getElementById('review-workspace');
const card=document.getElementById('review-work-card');
const status=document.getElementById('review-status');
const empty=document.getElementById('review-empty');
const total=document.getElementById('review-available');
let queue=[],selected=0,touched=null;
const safe=(v)=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
function key(item){return 'plcs-review-v2:'+item.repository+':'+item.number+':'+(item.revision||'');}
function getState(item){try{return JSON.parse(localStorage.getItem(key(item))||'{}')}catch(_){return {}}}
function setState(item,obj){try{localStorage.setItem(key(item),JSON.stringify(obj))}catch(_){}}
function remaining(){return queue.map((x,i)=>({x,i})).filter(y=>!getState(y.x).deferred)}
function showMessage(s){const m=document.getElementById('review-message');if(m)m.textContent=s;else status.textContent=s;}
function targetOf(item,part){
 const url=part==='edit'?item.edit_url:item.pr_url;
 if(!/^https:\/\/github\.com\/musikfed\/[A-Za-z0-9._-]+\//.test(url))return null;
 return url;
}
function decisionUrl(item,action,note){
 // GitHub pre-fills the Issue, and the logged-in author confirms with Submit new issue.
 // No access token or write credentials are ever embedded in static Pages.
 const url=new URL('https://github.com/musikfed/PLCodeStore/issues/new');
 url.searchParams.set('title','PLCS REVIEW '+action+' '+item.repository+'#'+item.number);
 url.searchParams.set('body','Revision: '+item.revision+'\nChecks: '+(action==='APPROVE'?'3/3':'not required')+'\n\nЗамечания (необязательно):\n'+(note||''));
 return url.toString();
}
function openReal(item,url,feedback){
 if(!url){showMessage('Ссылка на GitHub недоступна.');return}
 window.open(url,'_blank','noopener,noreferrer');
 showMessage(feedback);
}
function render(){
 if(!work||!card)return;
 const available=remaining();total.textContent=String(available.length);
 const deferredCount=queue.length-available.length;
 const restore=document.getElementById('review-unhide');
 if(restore){restore.disabled=deferredCount===0;restore.textContent=deferredCount?'Вернуть отложенные ('+deferredCount+')':'Нет отложенных';}
 if(!available.length){
  work.hidden=true;empty.hidden=false;
  document.getElementById('review-empty-title').textContent=deferredCount?'Все карточки отложены':'Очередь на сегодня пуста';
  document.getElementById('review-empty-description').textContent=deferredCount
   ? 'Карточки скрыты только в этом браузере. Нажми «Вернуть отложенные», чтобы снова их рассмотреть. В GitHub PR остаются открытыми.'
   : 'Публичных предложений пока нет. После Discover и сборки Pages здесь появятся карточки для проверки.';
  status.textContent=deferredCount?'Отложено в этом браузере: '+deferredCount:'Открытых публичных предложений пока нет.';
  return;
 }
 work.hidden=false;empty.hidden=true;selected=Math.min(selected,available.length-1);
 const item=available[selected].x,review=getState(item),checked=review.checks||[];
 card.innerHTML='';
 const outer=document.createElement('div');
 // All values written to HTML are escaped; links are checked again below.
 const img=item.image||('../assets/covers/review-'+encodeURIComponent(item.id)+'.svg');
 const photo=/^(https:\/\/raw\.githubusercontent\.com\/musikfed\/|..\/assets\/covers\/review-)/.test(img)?img:'../assets/icon.svg';
 const verifiedImages=(Array.isArray(item.images)?item.images:[])
  .filter(url=>typeof url==='string'&&/^https:\/\/raw\.githubusercontent\.com\/musikfed\/[A-Za-z0-9._-]+\//.test(url)).slice(0,4);
 const thumbHtml=verifiedImages.length>1
  ?'<div class="review-thumbnails" aria-label="Реальные материалы проекта">'+
   verifiedImages.map((url,i)=>'<button type="button" class="review-thumb" data-image-index="'+i+'" aria-label="Изображение '+(i+1)+' из '+verifiedImages.length+'"><img loading="lazy" alt="" src="'+safe(url)+'"></button>').join('')+
   '</div>':'';
 outer.innerHTML='<div class="review-card-top"><span>PROPOSAL / '+safe(item.id)+'</span><span>'+String(selected+1).padStart(2,'0')+' / '+String(available.length).padStart(2,'0')+'</span></div>'+
  '<h2 class="review-card-title">'+safe(item.title)+'</h2>'+
  '<p class="review-card-description">'+safe(item.description)+'</p>'+
  '<div class="review-tags"><span>'+safe(item.version && !['0.0.0','—','unknown'].includes(item.version) ? 'v'+item.version : 'Версия не указана')+'</span>'+item.tags.map(t=>'<span>'+safe(t)+'</span>').join('')+'</div>'+
  '<figure class="review-art"><img loading="lazy" src="'+safe(photo)+'" alt="Материалы проекта '+safe(item.title)+'"><figcaption>'+safe(item.image_caption||'Сгенерированная графическая обложка — не скриншот программы')+'</figcaption></figure>'+thumbHtml+
  '<div class="review-card-links"><a id="review-git-pr" target="_blank" rel="noopener noreferrer">Открыть PR в GitHub ↗</a><a id="review-git-edit" target="_blank" rel="noopener noreferrer">Редактировать meta.json ↗</a></div>'+
  '<div class="checks-title">ТРИ ПРОВЕРКИ ДЛЯ ПУБЛИКАЦИИ</div>'+
  '<div class="review-checks">'+checks.map(([k,label])=>'<label><input type="checkbox" data-check="'+safe(k)+'" '+(checked.includes(k)?'checked':'')+'> '+safe(label)+'</label>').join('')+'</div>'+
  '<div class="review-note"><label for="review-comment">Комментарий или замечания (необязательно)</label><textarea id="review-comment" maxlength="4000" placeholder="Можно оставить пустым или описать, что улучшить…">'+safe(review.comment||'')+'</textarea></div>'+
  '<div class="review-action-buttons"><button type="button" id="review-reject" class="reject">🛑 На доработку</button><button type="button" id="review-defer">⏭ Пропустить на потом</button><button type="button" id="review-approve" class="approve">❤️ Одобрить через GitHub</button></div>'+
  '<p class="review-message" id="review-message" role="status"></p>'+
  '<div class="review-pagination"><button id="review-previous" type="button">← Предыдущая</button><span class="review-break">GitHub попросит подтвердить готовую заявку</span><button id="review-next" type="button">Следующая →</button></div>';
 card.appendChild(outer);
 if(verifiedImages.length>1){
  const mainPhoto=card.querySelector('.review-art img');
  const figCaption=card.querySelector('.review-art figcaption');
  card.querySelectorAll('.review-thumb').forEach((button,i)=>{
   button.addEventListener('click',()=>{
    mainPhoto.src=verifiedImages[i];
    figCaption.textContent=verifiedImages[i].toLowerCase().endsWith('.svg')
      ?'Векторный макет из исходного репозитория'
      :'Изображение из исходного репозитория';
    card.querySelectorAll('.review-thumb').forEach((node,j)=>node.classList.toggle('is-active',j===i));
   });
   button.classList.toggle('is-active',i===0);
  });
 }
 const pr=card.querySelector('#review-git-pr'),edit=card.querySelector('#review-git-edit');
 pr.href=targetOf(item,'pr')||'#';edit.href=targetOf(item,'edit')||'#';
 const boxes=Array.from(card.querySelectorAll('input[type=checkbox]'));
 const approve=card.querySelector('#review-approve');
 const comment=card.querySelector('#review-comment');
 const update=()=>{
  const current=boxes.filter(b=>b.checked).map(b=>b.dataset.check);
  approve.disabled=current.length!==checks.length;
  setState(item,{...getState(item),checks:current,comment:comment.value});
 };
 boxes.forEach(b=>b.addEventListener('change',update));
 comment.addEventListener('input',update);
 update();
 function act(type){
  if(type==='defer'){setState(item,{...getState(item),deferred:true});selected=Math.min(selected,Math.max(0,remaining().length-1));render();status.textContent='Пропущена на потом. В GitHub PR не изменился. Вернуть можно кнопкой «Вернуть отложенные».';return;}
  if(type==='approve'){
   if(approve.disabled){showMessage('Отметь три обязательные проверки.');return;}
   openReal(item,decisionUrl(item,'APPROVE',comment.value.trim()),
     'GitHub открыл предварительно заполненное решение. Нажми «Submit new issue» — Actions сам обновит JSON и объединит PR.');
   return;
  }
  if(type==='reject'){
   openReal(item,decisionUrl(item,'REWORK',comment.value.trim()),
     'GitHub открыл готовое замечание. Нажми «Submit new issue» — Actions оставит PR на доработку. Комментарий необязателен.');
  }
 }
 card.querySelector('#review-reject').onclick=()=>act('reject');
 card.querySelector('#review-defer').onclick=()=>act('defer');
 approve.onclick=()=>act('approve');
 card.querySelector('#review-previous').disabled=selected===0;
 card.querySelector('#review-previous').onclick=()=>{selected=Math.max(0,selected-1);render()};
 card.querySelector('#review-next').disabled=selected===available.length-1;
 card.querySelector('#review-next').onclick=()=>{selected=Math.min(available.length-1,selected+1);render()}; // Просто перелистывает, не откладывая
 card.onpointerdown=e=>{if(e.target.closest('button,a,input,textarea,label'))return;touched=e.clientX};
 card.onpointerup=e=>{if(touched===null)return;const delta=e.clientX-touched;touched=null;if(Math.abs(delta)>115)act(delta>0?'approve':'reject')};
 status.textContent='Реальные предложения PR из публичных репозиториев. '+(selected+1)+' из '+available.length;
}
async function load(){
 status.textContent='Загрузка актуальной очереди из сборки Pages…';
 try{
  const result=await fetch('../data/review_queue.json',{cache:'no-store'});
  if(!result.ok)throw Error('HTTP '+result.status);
  const json=await result.json();
  queue=Array.isArray(json.items)?json.items.filter(p=>
   p&&typeof p.repository==='string'&&typeof p.id==='string'&&
   Array.isArray(p.tags)&&typeof p.pr_url==='string'&&typeof p.edit_url==='string'&&
   /^https:\/\/github\.com\/musikfed\/[A-Za-z0-9._-]+\/pull\/\d+$/.test(p.pr_url)&&
   /^https:\/\/github\.com\/musikfed\/[A-Za-z0-9._-]+\/edit\//.test(p.edit_url)
  ):[];
  selected=0;render();
 }catch(e){queue=[];render();status.textContent='Не удалось загрузить очередь: '+e.message+'. Проверь сборку Pages.'}
}
document.getElementById('review-refresh')?.addEventListener('click',load);
document.getElementById('review-unhide')?.addEventListener('click',()=>{
 for(const q of queue){const state=getState(q);if(state.deferred)setState(q,{...state,deferred:false})}
 selected=0;render();
});
load();
})();
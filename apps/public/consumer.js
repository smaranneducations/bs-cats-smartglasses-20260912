const feed=document.querySelector('#feed');
const panel=document.querySelector('#panel');
const panelContent=document.querySelector('#panelContent');
const preview=location.hostname==='127.0.0.1'||location.hostname==='localhost'||new URLSearchParams(location.search).get('preview')==='1';
const accents=['#ff653c','#c9ff38','#45c8ff','#ffce3a','#ff76bd','#73f0cf'];
let manifest={assets:[],policy:{}};
let cards=[];
let videos=[];

const esc=(value='')=>String(value).replace(/[&<>'"]/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
const words=value=>String(value||'').replaceAll('_',' ').trim();
const unwrap=raw=>raw?.payload||raw?.object||raw;
const claimText=claim=>String(claim?.statement||claim?.display_value||claim?.value||claim||'Unknown');
const claimValue=claim=>{const text=claimText(claim);const split=text.split(/:\s+/);return split.length>1?split.slice(1).join(': '):text};
const claimLabel=claim=>{const explicit=claim?.label||claim?.field_key||claim?.attribute;if(explicit)return words(explicit);const text=claimText(claim);const tail=text.includes(':')?text.split(':').slice(1).join(':'):text;return words(tail.split('=')[0].trim()||'Evidence')};
const productFor=card=>{const explicit=card.product_name||card.subject_name||card.product_label;if(explicit)return explicit;const text=claimText(cardClaims(card)[0]);const match=text.match(/(?:states|reported) for\s+(.+?):\s/i);return match?.[1]||words(String(card.product_id||'smart glasses').replace(/^product_/,''))};
const titleFor=(card,index)=>{
  const theme=words(card.theme||card.content_theme||card.segment||'Smart glasses');
  const hooks={
    'fit and wearability':'Will you forget they are there?',
    'visual workspace':'A screen that travels with you',
    'motion and stability':'Does the picture stay put?',
    'compatibility':'Will your devices play along?',
    'ownership':'The price after checkout',
    'mobile use':'Pocket less. See more.',
    'communication':'Your messages, eyes up',
    'privacy':'Smart without oversharing'
  };
  return card.hook||card.title||hooks[theme.toLowerCase()]||(['See the difference','Look beyond the spec','Would this fit your day?'][index%3]);
};
const impactFor=card=>card.why_it_matters||card.impact||card.summary||card.caption||'One sourced detail that can change how this product fits your real day.';
const normalizedCards=payload=>{
  const list=Array.isArray(payload)?payload:(payload?.cards??payload?.items??payload?.feed??payload?.results);
  if(!Array.isArray(list))throw new Error('Invalid feed response');
  const records=list.map(unwrap);
  if(records.some(item=>!item||typeof item!=='object'||Array.isArray(item)))throw new Error('Invalid feed record');
  return records;
};
const assetFor=(card,index)=>{
  const theme=String(card.theme||card.content_theme||'').toLowerCase();
  const preferred=theme.includes('fit')?0:theme.includes('visual')?2:theme.includes('mobile')?3:1;
  return manifest.assets[(preferred+index)%Math.max(manifest.assets.length,1)]||{};
};
const cardId=card=>card.card_id||card.object_id||card.id||card.slug||'unknown-card';
const cardClaims=card=>(card.claims||card.attributes||card.facts||[]).slice(0,3);

function renderVideos(){
  feed.innerHTML=videos.map((item,index)=>`<article class="poster video-poster" data-content-id="${esc(item.package_id)}" style="--accent:${accents[index%accents.length]}">
    <video controls playsinline preload="metadata" poster="${esc(item.poster_url)}" src="${esc(item.video_url)}"></video>
    <div class="video-copy"><p class="eyebrow">${esc(words(item.content_shape||'evidence story'))}</p><h1 class="video-title">${esc(item.title)}</h1><p>${esc(item.summary)}</p><div class="actions"><button class="action video-react" data-kind="like">USEFUL</button><button class="action secondary video-react" data-kind="dislike">NOT FOR ME</button><button class="action secondary video-comment">COMMENT</button><span class="counter">${index+1} / ${videos.length}</span></div><p data-interaction-status role="status" aria-live="polite"></p></div>
  </article>`).join('');
}

function render(){
  if(!cards.length){
    showFeedMessage('empty');
    return;
  }
  feed.innerHTML=cards.map((card,index)=>{
    const asset=assetFor(card,index);
    const claims=cardClaims(card);
    const product=productFor(card);
    const hook=titleFor(card,index);
    const highlighted=hook.split(' ').map((w,i)=>i===hook.split(' ').length-1?`<em>${esc(w)}</em>`:esc(w)).join(' ');
    return `<article class="poster" data-card-id="${esc(cardId(card))}" style="--accent:${accents[index%accents.length]};--photo:url('${esc(asset.local_path||'')}');--focus:${index%2?'center':'55% center'}">
      <span class="number">${String(index+1).padStart(2,'0')}</span>
      <span class="context-label">CATEGORY CONTEXT: ${esc(asset.product_identity||'illustrative image')}<br>NOT ${esc(product)}</span>
      <div class="poster-content">
        <p class="eyebrow">${esc(product)} / ${esc(words(card.theme||card.content_theme||'buyer lens'))}</p>
        <h1 class="hook">${highlighted}</h1>
        <p class="impact">${esc(impactFor(card))}</p>
        <ul class="facts">${claims.map(claim=>`<li class="fact"><strong>${esc(claimValue(claim))}</strong><small>${esc(claimLabel(claim))}</small></li>`).join('')}</ul>
        <div class="actions">
          <button class="action react" data-kind="like">USEFUL</button>
          <button class="action secondary react" data-kind="dislike">NOT FOR ME</button>
          <button class="action secondary evidence">WHY?</button>
          <span class="counter">${index+1} / ${cards.length}</span>
        </div>
        <p data-interaction-status role="status" aria-live="polite"></p>
      </div>
    </article>`;
  }).join('');
}

function showCard(card,index){
  const asset=assetFor(card,index);
  const evidence=(cardClaims(card)).map(claim=>`<li><b>${esc(claimLabel(claim))}</b><br>${esc(claimText(claim))}${claim?.confidence?`<br><small>Confidence: ${esc(claim.confidence)}</small>`:''}</li>`).join('');
  const sources=(card.source_urls||card.evidence_urls||card.sources||[]).map(source=>typeof source==='string'?source:(source.url||source.source_url)).filter(Boolean);
  panelContent.innerHTML=`<p class="eyebrow">THE RECEIPTS</p><h2>${esc(titleFor(card,index))}</h2><p>These are the governed claims behind the poster. Manufacturer-stated information is not hands-on testing.</p><h3>Evidence used</h3><ul class="evidence-list">${evidence||'<li>No claim details were returned.</li>'}</ul>${sources.length?`<h3>Source links</h3>${sources.map(url=>`<p><a href="${esc(url)}" target="_blank" rel="noopener">Open evidence source</a></p>`).join('')}`:''}<h3>Image identity and rights</h3><p><b>${esc(asset.title||'Category image')}</b> depicts ${esc(asset.product_identity||'a category example')}, not the product evaluated in this card.</p><p>${esc(asset.attribution||'')}</p><p><a href="${esc(asset.source_page||'#')}" target="_blank" rel="noopener">Image record</a> · <a href="${esc(asset.license_url||'#')}" target="_blank" rel="noopener">${esc(asset.license||'License')}</a></p><h3>Tell us what is missing</h3><form class="comment-box" data-comment-card="${esc(cardId(card))}"><input name="comment" maxlength="500" placeholder="One useful correction or question"><button>Send</button></form>`;
  panelContent.innerHTML+='<p data-interaction-status role="status" aria-live="polite"></p>';
  panel.showModal();
}

function showFeedMessage(state){
  const unavailable=state==='unavailable';
  const title=unavailable?'Stories are temporarily unavailable':preview?'No cards ready yet':'First stories are on the way';
  const detail=unavailable?'We could not load the feed. You can try loading it again.':preview?'Compose and review content in the operator workspace. Only approved content belongs in the public feed.':'We are preparing useful, evidence-led stories. Read how we check claims and images while the first stories are being prepared.';
  const action=unavailable?'<button class="action" data-retry-feed>Try again</button>':preview?'<a class="action" href="/operator#generate">Open content studio</a>':'<button class="action" data-open-sources>Our evidence approach</button>';
  feed.innerHTML=`<section class="empty"><div><p class="eyebrow">${preview?'PRIVATE PREVIEW':'EVIDENCE OVER HYPE'}</p><h1>${title}</h1><p>${detail}</p>${action}</div></section>`;
}

async function readJSON(url){
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),10000);
  try{
    const response=await fetch(url,{signal:controller.signal});
    if(!response.ok)throw new Error('Request unavailable');
    return await response.json();
  }finally{clearTimeout(timeout);}
}

async function submitInteraction(payload){
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),10000);
  try{
    payload.session_id=sessionStorage.lensbriefSession||(sessionStorage.lensbriefSession=crypto.randomUUID());
    const response=await fetch('/v1/public/events',{method:'POST',headers:{'content-type':'application/json','x-workspace-action':'1'},body:JSON.stringify(payload),signal:controller.signal});
    if(!response.ok)return {ok:false};
    return {ok:true};
  }catch{return {ok:false};}
  finally{clearTimeout(timeout);}
}

async function interaction(card,kind,body=''){
  return submitInteraction({card_id:cardId(card),event_type:kind,text:body||null});
}

async function videoInteraction(item,kind,body=''){
  return submitInteraction({content_id:item.package_id,event_type:kind,text:body||null});
}

function feedbackStatus(container,message){
  const status=container.querySelector('[data-interaction-status]');
  if(status)status.textContent=message;
}

async function reactToContent(button,poster,send){
  if(button.disabled||button.classList.contains('liked'))return;
  button.disabled=true;
  const result=await send();
  if(result.ok){button.classList.add('liked');button.setAttribute('aria-pressed','true');}
  feedbackStatus(poster,result.ok?'Feedback received.':'Could not confirm your feedback. It has not been marked as received.');
  button.disabled=false;
}

function showVideoComment(item){
  panelContent.innerHTML=`<p class="eyebrow">YOUR FEEDBACK</p><h2>${esc(item.title)}</h2><p>Share a useful question or correction. Comments are submitted for moderation.</p><form class="comment-box" data-comment-content="${esc(item.package_id)}"><input name="comment" maxlength="500" required placeholder="One useful correction or question"><button>Send</button></form><p data-interaction-status role="status" aria-live="polite"></p>`;
  panel.showModal();
}

feed.addEventListener('click',async event=>{
  if(event.target.closest('[data-retry-feed]')){await boot();return;}
  if(event.target.closest('[data-open-sources]')){showSources();return;}
  const videoPoster=event.target.closest('.video-poster');
  if(videoPoster){
    const index=[...feed.querySelectorAll('.video-poster')].indexOf(videoPoster);
    const item=videos[index];
    const reaction=event.target.closest('.video-react');
    if(reaction)await reactToContent(reaction,videoPoster,()=>videoInteraction(item,reaction.dataset.kind));
    if(event.target.closest('.video-comment'))showVideoComment(item);
    return;
  }
  const poster=event.target.closest('.poster');
  if(!poster)return;
  const index=[...feed.querySelectorAll('.poster')].indexOf(poster);
  const card=cards[index];
  if(event.target.closest('.evidence'))showCard(card,index);
  const react=event.target.closest('.react');
  if(react)await reactToContent(react,poster,()=>interaction(card,react.dataset.kind));
});
panel.addEventListener('submit',async event=>{
  event.preventDefault();
  const input=event.target.elements.comment;
  if(!input?.value.trim())return;
  const button=event.target.querySelector('button');
  if(button?.disabled)return;
  const card=cards.find(item=>cardId(item)===event.target.dataset.commentCard);
  const video=videos.find(item=>item.package_id===event.target.dataset.commentContent);
  if(!card&&!video)return;
  if(button)button.disabled=true;
  const result=card?await interaction(card,'comment',input.value.trim()):await videoInteraction(video,'comment',input.value.trim());
  if(result.ok){input.value='';input.placeholder='One useful correction or question';}
  feedbackStatus(panelContent,result.ok?'Submitted for moderation.':'Could not confirm submission. Your text has been kept; it has not been marked as received.');
  if(button)button.disabled=false;
});
document.querySelector('#closePanel').addEventListener('click',()=>panel.close());
document.querySelector('#aboutButton').addEventListener('click',showSources);
document.querySelector('#openSources').addEventListener('click',showSources);
function showSources(){panelContent.innerHTML=`<p class="eyebrow">VISUAL INVENTORY</p><h2>Images with receipts</h2><p>${esc(manifest.policy?.exact_product_gap||'Every image is governed by its own license record.')}</p>${manifest.assets.map(asset=>`<div class="source-card"><b>${esc(asset.title)}</b><small>${esc(asset.product_identity)} · ${esc(asset.license)}</small><p>${esc(asset.attribution)}</p><a href="${esc(asset.source_page)}" target="_blank" rel="noopener">Verify original record</a></div>`).join('')}`;panel.showModal();}

async function boot(){
  const [mediaResult,videoResult,feedResult]=await Promise.allSettled([
    readJSON('/discover-assets/assets/media/manifest.json'),
    readJSON('/v1/public/videos'),
    readJSON(preview?'/v1/audience/preview':'/v1/public/feed')
  ]);
  manifest=mediaResult.status==='fulfilled'&&Array.isArray(mediaResult.value?.assets)?mediaResult.value:{assets:[],policy:{exact_product_gap:'The image inventory is temporarily unavailable. No image rights are inferred from that absence.'}};
  const videoReady=videoResult.status==='fulfilled'&&Array.isArray(videoResult.value?.videos);
  videos=videoReady?videoResult.value.videos:[];
  let feedReady=false;
  cards=[];
  if(feedResult.status==='fulfilled'){
    try{cards=normalizedCards(feedResult.value);feedReady=true;}catch{/* An invalid response is not an empty feed. */}
  }
  if(videos.length)renderVideos();
  else if(cards.length)render();
  else if(!videoReady||!feedReady)showFeedMessage('unavailable');
  else render();
}
boot();

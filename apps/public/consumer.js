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
  const list=Array.isArray(payload)?payload:(payload.cards||payload.items||payload.feed||payload.results||[]);
  return list.map(unwrap).filter(Boolean);
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
    <div class="video-copy"><p class="eyebrow">${esc(item.content_shape.replaceAll('_',' '))}</p><h1 class="video-title">${esc(item.title)}</h1><p>${esc(item.summary)}</p><div class="actions"><button class="action video-react" data-kind="like">USEFUL</button><button class="action secondary video-react" data-kind="dislike">NOT FOR ME</button><button class="action secondary video-comment">COMMENT</button><span class="counter">${index+1} / ${videos.length}</span></div></div>
  </article>`).join('');
}

function render(){
  if(!cards.length){
    feed.innerHTML=`<section class="empty"><div><p class="eyebrow">PRIVATE PREVIEW</p><h1>No cards ready yet</h1><p>Compose governed cards in the admin workspace, then return here.</p><a class="action" href="/#content">Open content studio</a></div></section>`;
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
      </div>
    </article>`;
  }).join('');
}

function showCard(card,index){
  const asset=assetFor(card,index);
  const evidence=(cardClaims(card)).map(claim=>`<li><b>${esc(claimLabel(claim))}</b><br>${esc(claimText(claim))}${claim?.confidence?`<br><small>Confidence: ${esc(claim.confidence)}</small>`:''}</li>`).join('');
  const sources=(card.source_urls||card.evidence_urls||card.sources||[]).map(source=>typeof source==='string'?source:(source.url||source.source_url)).filter(Boolean);
  panelContent.innerHTML=`<p class="eyebrow">THE RECEIPTS</p><h2>${esc(titleFor(card,index))}</h2><p>These are the governed claims behind the poster. Manufacturer-stated information is not hands-on testing.</p><h3>Evidence used</h3><ul class="evidence-list">${evidence||'<li>No claim details were returned.</li>'}</ul>${sources.length?`<h3>Source links</h3>${sources.map(url=>`<p><a href="${esc(url)}" target="_blank" rel="noopener">Open evidence source</a></p>`).join('')}`:''}<h3>Image identity and rights</h3><p><b>${esc(asset.title||'Category image')}</b> depicts ${esc(asset.product_identity||'a category example')}, not the product evaluated in this card.</p><p>${esc(asset.attribution||'')}</p><p><a href="${esc(asset.source_page||'#')}" target="_blank" rel="noopener">Image record</a> · <a href="${esc(asset.license_url||'#')}" target="_blank" rel="noopener">${esc(asset.license||'License')}</a></p><h3>Tell us what is missing</h3><form class="comment-box" data-comment-card="${esc(cardId(card))}"><input name="comment" maxlength="500" placeholder="One useful correction or question"><button>Send</button></form>`;
  panel.showModal();
}

async function interaction(card,kind,body=''){
  const payload={card_id:cardId(card),event_type:kind,text:body||null,session_id:sessionStorage.lensbriefSession||(sessionStorage.lensbriefSession=crypto.randomUUID())};
  try{await fetch('/v1/public/events',{method:'POST',headers:{'content-type':'application/json','x-workspace-action':'1'},body:JSON.stringify(payload)});}catch(error){console.info('Interaction remains local-only unavailable',error);}
}

async function videoInteraction(item,kind,body=''){
  const payload={content_id:item.package_id,event_type:kind,text:body||null,session_id:sessionStorage.lensbriefSession||(sessionStorage.lensbriefSession=crypto.randomUUID())};
  try{await fetch('/v1/public/events',{method:'POST',headers:{'content-type':'application/json','x-workspace-action':'1'},body:JSON.stringify(payload)});}catch(error){console.info('Interaction unavailable',error);}
}

feed.addEventListener('click',event=>{
  const videoPoster=event.target.closest('.video-poster');
  if(videoPoster){
    const index=[...feed.querySelectorAll('.video-poster')].indexOf(videoPoster);
    const item=videos[index];
    const reaction=event.target.closest('.video-react');
    if(reaction){reaction.classList.toggle('liked');videoInteraction(item,reaction.dataset.kind);}
    if(event.target.closest('.video-comment')){const text=prompt('Share one useful correction or question');if(text?.trim())videoInteraction(item,'comment',text.trim());}
    return;
  }
  const poster=event.target.closest('.poster');
  if(!poster)return;
  const index=[...feed.querySelectorAll('.poster')].indexOf(poster);
  const card=cards[index];
  if(event.target.closest('.evidence'))showCard(card,index);
  const react=event.target.closest('.react');
  if(react){react.classList.toggle('liked');interaction(card,react.dataset.kind);}
});
panel.addEventListener('submit',event=>{event.preventDefault();const input=event.target.elements.comment;const card=cards.find(item=>cardId(item)===event.target.dataset.commentCard);if(input.value.trim()&&card){interaction(card,'comment',input.value.trim());input.value='';input.placeholder='Received for moderation';}});
document.querySelector('#closePanel').addEventListener('click',()=>panel.close());
document.querySelector('#aboutButton').addEventListener('click',showSources);
document.querySelector('#openSources').addEventListener('click',showSources);
function showSources(){panelContent.innerHTML=`<p class="eyebrow">VISUAL INVENTORY</p><h2>Images with receipts</h2><p>${esc(manifest.policy?.exact_product_gap||'Every image is governed by its own license record.')}</p>${manifest.assets.map(asset=>`<div class="source-card"><b>${esc(asset.title)}</b><small>${esc(asset.product_identity)} · ${esc(asset.license)}</small><p>${esc(asset.attribution)}</p><a href="${esc(asset.source_page)}" target="_blank" rel="noopener">Verify original record</a></div>`).join('')}`;panel.showModal();}

async function boot(){
  try{
    const [manifestResponse,videoResponse,feedResponse]=await Promise.all([
      fetch('/discover-assets/assets/media/manifest.json'),
      fetch('/v1/public/videos'),
      fetch(preview?'/v1/audience/preview':'/v1/public/feed')
    ]);
    if(!manifestResponse.ok||!videoResponse.ok||!feedResponse.ok)throw new Error(`Feed ${feedResponse.status}; video ${videoResponse.status}; manifest ${manifestResponse.status}`);
    manifest=await manifestResponse.json();
    videos=(await videoResponse.json()).videos||[];
    cards=normalizedCards(await feedResponse.json());
    if(videos.length)renderVideos();else render();
  }catch(error){feed.innerHTML=`<section class="empty"><div><p class="eyebrow">LOCAL PREVIEW</p><h1>Feed needs a quick restart</h1><p>${esc(error.message)}</p><a class="action" href="/?preview=1#content">Open content studio</a></div></section>`;}
}
boot();

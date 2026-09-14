(() => {
  'use strict';
  function assertionText(value) {
    if (!value || value.value_state === 'unknown') return 'Not available';
    const scalar = value.value_boolean ?? value.value_number ?? value.value_text;
    return scalar == null ? 'Not available' : String(scalar) + (value.unit ? ' ' + value.unit : '');
  }
  function selectedConcepts(definitions, keys) {
    if (!keys.length || keys.length > 25 || new Set(keys).size !== keys.length) throw Error('Choose one to 25 distinct concepts.');
    const known = new Set(definitions.map(value => value.key));
    if (keys.some(key => !known.has(key))) throw Error('A selected concept is not in the current ontology.');
    return keys;
  }
  if (typeof module !== 'undefined') module.exports = {assertionText, selectedConcepts};
  if (typeof document === 'undefined') return;
  const make = (tag, text) => { const node = document.createElement(tag); if (text != null) node.textContent = text; return node; };
  const dialog = make('dialog'); dialog.className = 'inspection-dialog'; dialog.id = 'operatorInspection';
  const header = make('header'), title = make('h2'), close = make('button', 'Close inspection'); close.type = 'button';
  header.append(title, close); const status = make('p'), content = make('div'); status.setAttribute('role', 'status');
  dialog.append(header, status, content); document.body.append(dialog);
  let generation = 0, urls = [], controller;
  function dispose() { generation++; controller?.abort(); content.querySelectorAll('video').forEach(video => {video.pause(); video.removeAttribute('src'); video.load();}); urls.forEach(URL.revokeObjectURL); urls = []; }
  close.addEventListener('click', () => dialog.close()); dialog.addEventListener('close', dispose);
  function open(label) { dispose(); controller = new AbortController(); title.textContent = label; status.textContent = 'Loading the authenticated workspace...'; content.replaceChildren(); if (!dialog.open) dialog.showModal(); return generation; }
  async function api(path, options = {}) { const response = await fetch(path, {...options, signal:controller.signal, headers:{'X-Workspace-Action':'1', ...(options.body ? {'Content-Type':'application/json'} : {}), ...options.headers}}); if (!response.ok) { let message = 'Request failed (' + response.status + ').'; try { const value = await response.json(); if (typeof value.detail === 'string') message = value.detail; } catch {} throw Error(message); } return response; }
  const json = async (path, options) => (await api(path, options)).json();
  function error(err, run) { if (run !== generation || err.name === 'AbortError') return; status.textContent = err.message; status.setAttribute('role','alert'); }
  function sources(values) { for (const source of values || []) { try { const url = new URL(source.uri); if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) continue; const link = make('a', source.title || source.publisher || url.hostname); link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer'; content.append(link); } catch {} } }
  function table(labels, rows) { const wrapper = make('div'); wrapper.className = 'inspection-scroll'; wrapper.tabIndex = 0; const table = make('table'), head = make('thead'), row = make('tr'), body = make('tbody'); labels.forEach(text => {const cell=make('th',text);cell.scope='col';row.append(cell);}); head.append(row); rows.forEach(values => { const tr=make('tr'); values.forEach(value => { const td=make('td'); if(typeof value==='string')td.textContent=value; else {td.append(make('strong',assertionText(value))); if(value)td.append(make('small',value.conditions || 'Conditions not recorded'),make('small','Observed: '+(value.observed_at || 'Not recorded')),make('small','Confidence: '+(value.confidence ?? 'Not assessed')));}tr.append(td);});body.append(tr);});table.append(head,body);wrapper.append(table);return wrapper; }
  async function inspectProduct(id) { const run=open('Product evidence'); try { const data=await json('/v1/semantic/products/'+encodeURIComponent(id)+'/assertions'); if(run!==generation)return; title.textContent=data.title+' / v'+data.version;status.textContent='Source-bound statements, not independent testing. Unknown values remain unknown.';content.append(table(['Concept','Value and conditions'],data.assertions.map(value=>[value.concept_id.replace(/^concept_/,''),value])));sources(data.sources); } catch(err){error(err,run);} }
  async function comparison() {
    const run=open('Compare governed products');
    try { const [workflow,ontology]=await Promise.all([json('/v1/operator/workflow'),json('/v1/semantic/ontology')]); if(run!==generation)return;
      const form=make('form'), products=make('fieldset'), concepts=make('fieldset'); products.append(make('legend','Choose two to four products')); concepts.append(make('legend','All ontology concepts (choose up to 25)'));
      const pgrid=make('div'), cgrid=make('div');pgrid.className=cgrid.className='inspection-choices';
      for(const product of workflow.products){const label=make('label'), input=make('input');input.type='checkbox';input.name='product';input.value=product.object_id;label.append(input,make('span',product.title));pgrid.append(label);}
      for(const definition of ontology.items){const label=make('label'), input=make('input');input.type='checkbox';input.name='concept';input.value=definition.key;input.checked=['weight_g','fov_deg','refresh_hz'].includes(definition.key);label.title=definition.description;label.append(input,make('span',definition.label+(definition.unit?' ('+definition.unit+')':'')));cgrid.append(label);}
      products.append(pgrid);concepts.append(cgrid);const submit=make('button','Compare selected products');submit.type='submit';const results=make('div');form.append(products,concepts,submit);content.append(form,results);status.textContent='Every active definition is available. Markets, variants and evidence limitations remain explicit.';
      form.addEventListener('submit',async event=>{event.preventDefault();submit.disabled=true;try{const data=new FormData(form), ids=data.getAll('product'), keys=selectedConcepts(ontology.items,data.getAll('concept'));if(ids.length<2||ids.length>4)throw Error('Choose two to four products.');const compared=await json('/v1/semantic/compare',{method:'POST',body:JSON.stringify({product_ids:ids,concepts:keys})});if(run!==generation)return;results.replaceChildren(table(['Concept',...compared.products.map(product=>product.title)],compared.rows.map(row=>[row.concept.label,...row.cells.map(cell=>cell.assertion)])));status.textContent=compared.caveat;for(const product of compared.products)results.append(make('p',product.title+': '+product.market+' / '+(product.variant||'Variant not recorded')));}catch(err){error(err,run);}finally{submit.disabled=false;}});
    }catch(err){error(err,run);}
  }
  async function media(id) {
    const run=open('Private artifact review');
    try {
      const base='/v1/media/artifacts/'+encodeURIComponent(id), data=await json(base);if(run!==generation)return;
      title.textContent=data.title;status.textContent='Private draft. Playback never grants publication approval.';
      const video=make('video');video.controls=true;video.playsInline=true;video.preload='metadata';video.setAttribute('aria-label','Private governed video');content.append(video);
      const details=make('details'), metadata=make('pre',JSON.stringify(data.payload.publish_metadata,null,2));details.append(make('summary','Exact metadata and artifact identity'),metadata,make('pre',JSON.stringify({version:data.version,video_sha256:data.payload.video_sha256,metadata_sha256:data.payload.metadata_sha256},null,2)));content.append(details);sources(data.sources);
      const response=await api(base+'/video');const length=Number(response.headers.get('content-length'));if(!Number.isFinite(length)||length<=0||length>64*1024*1024)throw Error('Video size is unavailable or exceeds the private preview limit.');const blob=await response.blob();if(blob.size!==length)throw Error('Video download did not match its declared size.');if(run!==generation)return;const url=URL.createObjectURL(blob);urls.push(url);video.src=url;
      const manifest=await json(base+'/manifest');if(run!==generation)return;const evidence=make('details');evidence.append(make('summary','Verified render manifest'),make('pre',JSON.stringify(manifest,null,2)));content.append(evidence);
      const checkStatus=make('p','Checking separate release gates...');content.append(checkStatus);
      try { const {packet}=await json(base+'/release-review');if(run!==generation)return;checkStatus.textContent=packet.summary;const list=make('dl');for(const check of packet.checks){list.append(make('dt',check.check_id.replaceAll('_',' ')+' / '+check.state),make('dd',check.reason));}content.append(list); }catch(err){checkStatus.textContent='Release checks remain unavailable: '+err.message;}
    }catch(err){error(err,run);}
  }
  document.addEventListener('click',event=>{const link=event.target.closest('a[href]');if(!link || event.button!==0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)return;const url=new URL(link.href,location.href);if(url.origin!==location.origin)return;let match=url.pathname.match(/^\/media-review\/(render_[0-9a-f]{32})$/);if(match){event.preventDefault();media(match[1]);return;}if(url.pathname==='/intelligence'){event.preventDefault();match=url.hash.match(/^#product\/([A-Za-z0-9_-]+)$/);match?inspectProduct(match[1]):comparison();}});
  function mount(){if(location.hash!=='#dataset')return;const area=document.querySelector('#stageDetail');if(!area||area.querySelector('#comparisonLauncher'))return;const button=make('button','Compare products using the ontology');button.id='comparisonLauncher';button.className='inspection-launcher';button.addEventListener('click',comparison);area.prepend(button);}
  new MutationObserver(mount).observe(document.querySelector('#stageDetail'),{childList:true,subtree:true});window.addEventListener('hashchange',mount);mount();
  const id=new URLSearchParams(location.search).get('artifact');if(id&&/^render_[0-9a-f]{32}$/.test(id))media(id);
})();

const api = async (path, options = {}) => { const response = await fetch(path, {...options, headers:{'Content-Type':'application/json','X-Workspace-Action':'1',...(options.headers || {})}}); const data = await response.json(); if (!response.ok) throw new Error(data.detail || 'Request failed'); return data; };
const html = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const label = value => String(value || '').replaceAll('_',' ').replace(/\b\w/g, letter => letter.toUpperCase());
const groups = {
  dataset: {title:'Governed data library', description:'Search, filter, create, update and safely retire the records that form the commercial intelligence asset.', types:['product','market_observation','source_policy','media_asset']},
  direction: {title:'Creative system', description:'Standing creative direction, reusable scene primitives and evidence-bound story plans.', types:['__creative_profile','__primitives','content_brief']},
  generate: {title:'Generated content library', description:'Draft cards, bundles, Shorts, storyboards, recipes and reproducible render outputs.', types:['content_card','card_bundle','shorts_plan','storyboard','render_recipe']},
  release: {title:'Review and publication library', description:'Exact rendered artifacts, release packets, commercial evidence and publication boundaries.', types:['render_artifact','release_review_packet','commerce_path','commerce_assessment','commerce_evidence']},
  learn: {title:'Learning and improvement library', description:'Feedback, decisions, documentation and their traceable effect on the intelligence engine.', types:['feedback','decision_record','__capabilities']}
};
const primitiveList = [
  ['question_hook','Open with the buyer question'],['product_card','Introduce one governed product'],['feature_callout','Explain one feature and impact'],['comparison_table','Show matched differences without an automatic winner'],['decision_map','Connect needs to checks'],['metric_card','Make one sourced number legible'],['timeline','Explain dated change'],['compatibility_chain','Show device and accessory dependencies'],['question_reveal','Turn an audience question into a story'],['evidence_note','Surface provenance or a critical caveat'],['uncertainty_card','Make an unknown explicit'],['takeaway','Close with a useful next action']
];
const adminState = {objects:[], schema:{object_types:{}}, workflow:{}, view:null};
const recordsFor = type => adminState.objects.filter(item => item.object_type === type);
function columns(type) { const records = recordsFor(type); const keys = new Set(); records.slice(0,10).forEach(item => Object.keys(item.payload || {}).forEach(key => keys.add(key))); const descriptor = adminState.schema.object_types?.[type] || {}; const declared = descriptor.payload_columns || descriptor.columns || descriptor.fields || descriptor.properties; if (Array.isArray(declared)) declared.forEach(item => keys.add(typeof item === 'string' ? item : item.name || item.key)); else if (declared && typeof declared === 'object') Object.keys(declared).forEach(key => keys.add(key)); return [...keys].filter(Boolean); }
function syntheticCount(type) { if (type === '__primitives') return primitiveList.length; if (type === '__creative_profile') return adminState.workflow.creative ? 1 : 0; if (type === '__capabilities') return adminState.workflow.capabilities?.capabilities?.length || 0; return recordsFor(type).length; }
function rerender() { document.querySelector('#stageDataWorkspace')?.remove(); mount(); }
function landing(stage, group) { return `<section id="stageDataWorkspace" class="stage-data managed-workspace"><div class="ontology-hero"><p class="kicker">${html(stage === 'learn' ? 'LEARNING CONTROL PLANE' : 'STAGE DATA TREE')}</p><h3>${html(group.title)}</h3><p>${html(group.description)}</p></div><div class="managed-tree"><div class="tree-root"><span>ROOT</span><b>${html(group.title)}</b><small>${group.types.length} dataset branches</small></div>${group.types.map(type => `<button type="button" class="tree-branch" data-managed-type="${html(type)}"><span>${type === '__capabilities' ? 'EVALUATED INTEGRATIONS' : type.startsWith('__') ? 'CREATIVE CONFIGURATION' : 'VERSIONED DATASET'}</span><b>${html(label(type.replace('__','')))}</b><p>${html(type === '__capabilities' ? 'Adopted, gated and deferred capabilities with explicit cost and data boundaries.' : type === '__primitives' ? 'Reusable visual grammar used across cards and kinetic video.' : type === '__creative_profile' ? 'Standing visual, audio, editorial and runtime direction.' : columns(type).slice(0,6).join(' / ') || 'No active columns yet.')}</p><small>${syntheticCount(type)} current item${syntheticCount(type) === 1 ? '' : 's'}</small></button>`).join('')}</div></section>`; }
function branch(stage, group, type) { if (type === '__primitives') return primitiveBranch(group); if (type === '__creative_profile') return profileBranch(group); if (type === '__capabilities') return capabilityBranch(group); const records = recordsFor(type); const statuses = [...new Set(records.map(item => item.status || 'captured'))].sort(); return `<section id="stageDataWorkspace" class="stage-data managed-workspace"><button class="text-back" data-managed-home>Back to ${html(group.title)}</button><div class="ontology-branch-head"><div><p class="kicker">VERSIONED DATASET</p><h3>${html(label(type))}</h3><p>${html(columns(type).join(' / ') || 'No active columns yet.')}</p></div><button type="button" data-create-record="${html(type)}">Create new</button></div><div class="record-tools"><label>Search<input id="recordSearch" type="search" placeholder="Search title, ID or data"></label><label>Status<select id="recordStatus"><option value="all">All statuses</option>${statuses.map(status => `<option value="${html(status)}">${html(label(status))}</option>`).join('')}</select></label><span id="recordCount" role="status">${records.length} records</span></div><p id="recordNoResults" hidden>No records match these filters.</p><div class="managed-records">${records.map(item => `<article class="managed-record" data-status="${html(item.status || 'captured')}" data-search="${html(JSON.stringify([item.object_id,item.title,item.payload]).toLowerCase())}"><div><span>${html(label(item.status || 'captured'))}</span><b>${html(item.title || item.object_id)}</b><small>${html(item.object_id)} / v${item.version}</small></div><div class="record-actions"><button type="button" class="quiet" data-edit-record="${html(item.object_id)}">Edit</button>${item.status === 'archived' ? `<button type="button" class="quiet" data-restore-record="${html(item.object_id)}">Restore</button>` : `<button type="button" class="retire" data-retire-record="${html(item.object_id)}">Retire</button>`}</div></article>`).join('') || '<div class="dataset-empty"><b>No records yet</b><p>Create the first governed record when its required evidence and lineage are available.</p></div>'}</div></section>`; }
function primitiveBranch(group) { return `<section id="stageDataWorkspace" class="stage-data managed-workspace"><button class="text-back" data-managed-home>Back to ${html(group.title)}</button><div class="ontology-branch-head"><div><p class="kicker">CREATIVE PRIMITIVE REGISTRY</p><h3>Scene primitives</h3><p>Reusable visual grammar. Story agents combine these primitives; they do not reinvent every video from scratch.</p></div><button type="button" data-creative-proposal="new primitive">Propose new primitive</button></div><div class="primitive-grid">${primitiveList.map(([id,purpose]) => `<article><span>${html(id)}</span><h4>${html(label(id))}</h4><p>${html(purpose)}</p><div><button type="button" class="quiet" data-creative-proposal="change ${html(id)}">Propose change</button><button type="button" class="retire" data-creative-proposal="retire ${html(id)}">Propose retirement</button></div></article>`).join('')}</div></section>`; }
function capabilityBranch(group) { const registry = adminState.workflow.capabilities || {}; const items = registry.capabilities || []; return `<section id="stageDataWorkspace" class="stage-data managed-workspace"><button class="text-back" data-managed-home>Back to ${html(group.title)}</button><div class="ontology-branch-head"><div><p class="kicker">CAPABILITY INTEGRATION REGISTRY</p><h3>External capabilities</h3><p>Each project is admitted through the existing policy, object, cost and audit boundaries. Repository popularity never grants runtime authority.</p></div><a class="text-link" href="/operator/docs/platform-architecture.html" target="_blank" rel="noopener">Open architecture map</a></div><div class="capability-grid">${items.map(item => `<article class="capability-card" data-decision="${html(item.decision)}"><div><span>${html(label(item.status))}</span><small>${html(item.license)}</small></div><h4>${html(item.label)}</h4><p>${html(item.purpose)}</p><dl><dt>Decision</dt><dd>${html(label(item.decision))}</dd><dt>Integration</dt><dd>${html(item.integration)}</dd><dt>Cost</dt><dd>${html(item.cost)}</dd><dt>Data boundary</dt><dd>${html(item.data_boundary)}</dd><dt>Next gate</dt><dd>${html(item.next_gate)}</dd></dl><a href="${html(item.source_url)}" target="_blank" rel="noopener noreferrer">Review source repository</a></article>`).join('')}</div><p class="runtime-boundary"><strong>Admission policy:</strong> ${html(registry.policy?.admission_rule || 'External capabilities remain disabled until admitted.')}</p></section>`; }
function profileBranch(group) { const profile = adminState.workflow.creative || {}; return `<section id="stageDataWorkspace" class="stage-data managed-workspace"><button class="text-back" data-managed-home>Back to ${html(group.title)}</button><div class="ontology-branch-head"><div><p class="kicker">CREATIVE PROFILE</p><h3>${html(profile.profile_id || 'Standing creative direction')}</h3><p>Version ${html(profile.revision || 'unavailable')} / ${html(profile.scope || 'domain content')}</p></div><button type="button" data-creative-proposal="creative profile">Propose profile update</button></div><div class="profile-grid">${['visuals','audio','editorial','runtime_settings'].map(key => `<article><h4>${html(label(key))}</h4><dl>${Object.entries(profile[key] || {}).map(([name,value]) => `<dt>${html(label(name))}</dt><dd>${html(typeof value === 'object' ? JSON.stringify(value) : value)}</dd>`).join('') || '<dd>Not configured</dd>'}</dl></article>`).join('')}</div></section>`; }
function selectManagedType(type) { const stage = location.hash.slice(1); if (!groups[stage]?.types.includes(type)) return; adminState.view = {stage,type}; rerender(); }
function mount() { const stage = location.hash.slice(1); const group = groups[stage]; if (!group) return; if (adminState.view?.stage !== stage) adminState.view = {stage,type:null}; const card = document.querySelector('#stageDetail .stage-card'); if (!card || card.querySelector('.managed-workspace')) return; card.querySelector('#stageDataWorkspace')?.remove(); card.insertAdjacentHTML('beforeend', adminState.view.type ? branch(stage,group,adminState.view.type) : landing(stage,group)); bind(); }
function filterRecords() { const query = (document.querySelector('#recordSearch')?.value || '').toLowerCase(); const status = document.querySelector('#recordStatus')?.value || 'all'; const rows = document.querySelectorAll('.managed-record'); let visible = 0; rows.forEach(row => { row.hidden = !(row.dataset.search.includes(query) && (status === 'all' || row.dataset.status === status)); if (!row.hidden) visible++; }); const count = document.querySelector('#recordCount'); if (count) count.textContent = `${visible} of ${rows.length} records`; const empty = document.querySelector('#recordNoResults'); if (empty) empty.hidden = visible !== 0; }
function dialog() { let node = document.querySelector('#recordAdminDialog'); if (!node) { node = document.createElement('dialog'); node.id='recordAdminDialog'; node.className='object-dialog'; node.innerHTML='<button type="button" class="dialog-close">Close</button><div class="record-dialog-body"></div>'; node.querySelector('button').onclick=()=>node.close(); document.body.appendChild(node); } return node; }
function resolveFieldSchema(property, root) {
  let result = {...(property || {})};
  if (result.$ref?.startsWith('#/$defs/')) {
    const key = result.$ref.slice(8).replaceAll('~1','/').replaceAll('~0','~');
    result = {...(root.$defs?.[key] || {}), ...result};
    delete result.$ref;
  }
  if (Array.isArray(result.allOf) && result.allOf.length === 1) result = {...resolveFieldSchema(result.allOf[0],root),...result};
  const choices = result.anyOf || result.oneOf;
  if (Array.isArray(choices)) {
    const resolved = choices.map(item => resolveFieldSchema(item,root));
    const concrete = resolved.filter(item => item.type !== 'null');
    if (concrete.length === 1) result = {...concrete[0],...result, nullable:resolved.some(item => item.type === 'null')};
    else result = {...result, type:'json', nullable:resolved.some(item => item.type === 'null')};
  }
  if (Array.isArray(result.type)) {
    const types = result.type.filter(item => item !== 'null');
    result = {...result, nullable:result.type.includes('null'), type:types.length===1?types[0]:'json'};
  }
  return result;
}
function payloadSchema(type) { return adminState.schema.object_types?.[type] || {}; }
function initialPayload(type,current) {
  const schema = payloadSchema(type);
  const existing = current?.payload || {};
  return Object.fromEntries([...new Set([...Object.keys(schema.properties || {}),...Object.keys(existing)])].map(key => {
    if (Object.hasOwn(existing,key)) return [key,existing[key]];
    const definition = resolveFieldSchema(schema.properties?.[key],schema);
    return [key,Object.hasOwn(definition,'default')?structuredClone(definition.default):Object.hasOwn(definition,'const')?definition.const:undefined];
  }));
}
function control(key,value,definition={},required=false) {
  const title = definition.title || label(key);
  const hint = definition.description ? `<small>${html(definition.description)}</small>` : '';
  const head = `<span>${html(title)}</span><code>${html(key)}</code>${hint}`;
  const nullable = definition.nullable === true || definition.type === 'null';
  const empty = nullable?'null':required?'error':'omit';
  const base = `name="${html(key)}" aria-label="${html(title)}" data-empty="${empty}"${required&&!nullable?' required':''}`;
  if (Object.hasOwn(definition,'const')) {
    return `<label class="object-field">${head}<input ${base} value="${html(JSON.stringify(definition.const))}" data-kind="json" readonly></label>`;
  }
  if (Array.isArray(definition.enum)) {
    const values = [...definition.enum];
    if (nullable && !values.includes(null)) values.unshift(null);
    const selected = JSON.stringify(value);
    const options = values.map(choice => `<option value="${html(JSON.stringify(choice))}"${JSON.stringify(choice)===selected?' selected':''}>${html(choice===null?'Not available':typeof choice==='string'?label(choice):String(choice))}</option>`).join('');
    return `<label class="object-field">${head}<select ${base} data-kind="enum"><option value=""${value===undefined?' selected':''}>Choose ${html(title.toLowerCase())}</option>${options}</select></label>`;
  }
  const kind = definition.type || (value && typeof value==='object'?'object':typeof value==='boolean'?'boolean':typeof value==='number'?'number':'string');
  if (kind==='boolean') {
    return `<label class="object-field">${head}<select ${base} data-kind="boolean"><option value=""${value===undefined?' selected':''}>Choose ${html(title.toLowerCase())}</option>${nullable?`<option value="null"${value===null?' selected':''}>Not available</option>`:''}<option value="true"${value===true?' selected':''}>True</option><option value="false"${value===false?' selected':''}>False</option></select></label>`;
  }
  if (kind==='number' || kind==='integer') {
    const min = definition.minimum === undefined?'':` min="${html(definition.minimum)}"`;
    const max = definition.maximum === undefined?'':` max="${html(definition.maximum)}"`;
    return `<label class="object-field">${head}<input ${base} type="number" step="${kind==='integer'?'1':'any'}" value="${html(value)}" data-kind="${kind}"${min}${max}></label>`;
  }
  if (kind==='array' || kind==='object' || kind==='json') {
    return `<label class="object-field object-field--wide">${head}<textarea ${base} rows="6" data-kind="json" placeholder="${kind==='array'?'[]':kind==='object'?'{}':'JSON value'}">${value===undefined?'':html(JSON.stringify(value,null,2))}</textarea></label>`;
  }
  const limits = (definition.minLength===undefined?'':` minlength="${html(definition.minLength)}"`)+(definition.maxLength===undefined?'':` maxlength="${html(definition.maxLength)}"`);
  const format = definition.format==='date-time'?' placeholder="2026-09-14T12:00:00Z"':'';
  const textEmpty = value===''?'text':empty;
  return `<label class="object-field">${head}<input name="${html(key)}" aria-label="${html(title)}" value="${html(value)}" data-kind="text" data-empty="${textEmpty}"${required&&!nullable?' required':''}${limits}${format}></label>`;
}
function inputValue(input) {
  if (input.value==='') {
    if (input.dataset.empty==='null') return null;
    if (input.dataset.empty==='omit') return undefined;
    if (input.dataset.empty==='error') throw new Error(label(input.name)+' is required.');
    return '';
  }
  if (input.dataset.kind==='json' || input.dataset.kind==='enum') {
    try { return JSON.parse(input.value); } catch { throw new Error(label(input.name)+' must contain valid JSON.'); }
  }
  if (input.dataset.kind==='boolean') {
    if (input.value==='null' && input.dataset.empty==='null') return null;
    if (!['true','false'].includes(input.value)) throw new Error(label(input.name)+' must be true or false.');
    return input.value==='true';
  }
  if (input.dataset.kind==='number' || input.dataset.kind==='integer') {
    const value=Number(input.value);
    if (!Number.isFinite(value) || (input.dataset.kind==='integer'&&!Number.isInteger(value))) throw new Error(label(input.name)+' must contain a valid '+input.dataset.kind+'.');
    return value;
  }
  return input.value;
}
function collectPayload(form) {
  const next={};
  form.querySelectorAll('[name]:not([name^="__"])').forEach(input => {
    const value=inputValue(input);
    if (value!==undefined) next[input.name]=value;
  });
  return next;
}
function stableWriteKey(state,path,body) {
  const fingerprint=JSON.stringify([path,body]);
  if (state.fingerprint!==fingerprint) {state.fingerprint=fingerprint;state.key='admin-record-'+crypto.randomUUID();}
  return state.key;
}
function recordForm(type,id=null) {
  const current=id?adminState.objects.find(item=>item.object_id===id):null;
  const schema=payloadSchema(type),payload=initialPayload(type,current),node=dialog();
  if (!schema.properties && !current) {
    node.querySelector('.record-dialog-body').innerHTML='<h2>Schema unavailable</h2><p>This record cannot be created until its registered schema is available.</p>';
    node.showModal();return;
  }
  node.querySelector('.record-dialog-body').innerHTML=`<p class="kicker">${current?'EDIT VERSIONED RECORD':'CREATE GOVERNED RECORD'}</p><h2>${html(current?.title || label(type))}</h2><form id="recordAdminForm"><div class="object-form-grid"><label class="object-field object-field--wide"><span>Title</span><input name="__title" value="${html(current?.title || '')}" required maxlength="240"></label><label class="object-field object-field--wide"><span>Purpose</span><textarea name="__purpose" required maxlength="1000">${html(current?.purpose || '')}</textarea></label>${Object.entries(payload).map(([key,value])=>control(key,value,resolveFieldSchema(schema.properties?.[key],schema),(schema.required || []).includes(key))).join('')}</div><label class="object-field object-field--wide"><span>Revision reason</span><textarea name="__reason" required></textarea></label><button type="submit">${current?'Save new version':'Create record'}</button><p class="form-status" role="status"></p></form>`;
  const writeState={inFlight:false,fingerprint:null,key:null};
  node.querySelector('form').onsubmit=async event=>{
    event.preventDefault();if(writeState.inFlight)return;
    const form=event.currentTarget,status=form.querySelector('.form-status'),submit=form.querySelector('[type="submit"]');
    try {
      const next=collectPayload(form);
      const path=current?'/v1/objects/'+encodeURIComponent(current.object_id)+'/curate':'/v1/objects';
      const body=current?{expected_version:current.version,patch:{title:form.elements.__title.value,purpose:form.elements.__purpose.value,payload:next,metadata:{...(current.metadata||{}),last_revision_reason:form.elements.__reason.value},sources:current.sources||[]}}:{object_type:type,domain:adminState.workflow.domain?.domain || current?.domain || 'smart_glasses',title:form.elements.__title.value,purpose:form.elements.__purpose.value,payload:next,metadata:{creation_reason:form.elements.__reason.value},source:[],sources:[]};
      const key=stableWriteKey(writeState,path,body);
      writeState.inFlight=true;submit.disabled=true;status.textContent='Saving...';
      await api(path,{method:'POST',headers:{'Idempotency-Key':key},body:JSON.stringify(body)});
      status.textContent='Saved. Reloading the governed record list...';location.reload();
    } catch(error) {status.textContent=error.message;}
    finally {writeState.inFlight=false;submit.disabled=false;}
  };
  node.showModal();
}
async function lifecycle(id,action) { const item=adminState.objects.find(record=>record.object_id===id); if(!item)return; const verb=action==='archive'?'retire':'restore'; const reason=prompt(`Reason to ${verb} ${item.title}:`); if(!reason)return; if(action==='archive'&&!confirm('Retire this record? History is preserved and the record can be restored.'))return; try{await api('/v1/objects/'+encodeURIComponent(id)+'/'+action,{method:'POST',headers:{'Idempotency-Key':'admin-life-'+crypto.randomUUID()},body:JSON.stringify({expected_version:item.version,reason})});location.reload();}catch(error){alert(error.message);}}
function creativeProposal(target) { const node=dialog(); node.querySelector('.record-dialog-body').innerHTML=`<p class="kicker">CREATIVE SYSTEM CHANGE</p><h2>${html(label(target))}</h2><form id="creativeProposal"><label class="object-field"><span>Requested change</span><textarea name="change" required></textarea></label><label class="object-field"><span>Expected benefit and affected outputs</span><textarea name="impact" required></textarea></label><button>Record governed proposal</button><p class="form-status"></p></form>`; node.querySelector('form').onsubmit=async event=>{event.preventDefault();const form=event.currentTarget,status=form.querySelector('.form-status');try{await api('/v1/objects',{method:'POST',headers:{'Idempotency-Key':'creative-change-'+crypto.randomUUID()},body:JSON.stringify({object_type:'feedback',domain:'smart_glasses',title:'Creative change: '+label(target),purpose:'Capture a governed creative-system change without silently mutating renderer behavior.',tags:['creative_system'],source:[],sources:[],payload:{summary:'Creative system change for '+target,input:form.elements.change.value,classification:'operating_directive',target_ids:[],proposed_improvement:form.elements.impact.value,system_area:'content_editorial',authority:'operating_directive'}})});location.reload();}catch(error){status.textContent=error.message;}};node.showModal();}
function bind(){document.querySelectorAll('[data-managed-type]').forEach(button=>button.onclick=()=>selectManagedType(button.dataset.managedType));document.querySelector('[data-managed-home]')?.addEventListener('click',()=>{adminState.view.type=null;rerender();});document.querySelector('#recordSearch')?.addEventListener('input',filterRecords);document.querySelector('#recordStatus')?.addEventListener('change',filterRecords);document.querySelectorAll('[data-create-record]').forEach(button=>button.onclick=()=>recordForm(button.dataset.createRecord));document.querySelectorAll('[data-edit-record]').forEach(button=>button.onclick=()=>recordForm(adminState.objects.find(item=>item.object_id===button.dataset.editRecord)?.object_type,button.dataset.editRecord));document.querySelectorAll('[data-retire-record]').forEach(button=>button.onclick=()=>lifecycle(button.dataset.retireRecord,'archive'));document.querySelectorAll('[data-restore-record]').forEach(button=>button.onclick=()=>lifecycle(button.dataset.restoreRecord,'restore'));document.querySelectorAll('[data-creative-proposal]').forEach(button=>button.onclick=()=>creativeProposal(button.dataset.creativeProposal));}
async function start(){try{const [objects,schema,workflow]=await Promise.all([api('/v1/objects'),api('/v1/schema'),api('/v1/operator/workflow')]);adminState.objects=Array.isArray(objects)?objects:(objects.items||objects.objects||[]);adminState.schema=schema;adminState.workflow=workflow;}catch(error){adminState.error=error.message;}new MutationObserver(mount).observe(document.querySelector('#stageDetail'),{childList:true,subtree:true});window.addEventListener('hashchange',()=>{adminState.view=null;mount();});mount();}
start();

const $=selector=>document.querySelector(selector);
const esc=(value='')=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
const pretty=value=>String(value||'').replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
const key=()=>crypto.randomUUID();
let state={};let events=[];let selected='domain';

async function request(url,options={}){const headers=new Headers(options.headers||{});if(options.body!==undefined&&!headers.has('Content-Type'))headers.set('Content-Type','application/json');headers.set('X-Workspace-Action','1');const response=await fetch(url,{...options,headers});if(!response.ok){let message=`Request failed (${response.status})`;try{const body=await response.json();message=typeof body.detail==='string'?body.detail:JSON.stringify(body.detail||body);}catch{}throw new Error(message)}return response.status===204?{}:response.json()}
async function refresh(){const [workflow,audience]=await Promise.all([request('/v1/operator/workflow'),request('/v1/audience/events').catch(()=>({events:[]}))]);state=workflow;events=audience.events||audience.items||[];selected=location.hash.slice(1)&&state.stages.some(s=>s.id===location.hash.slice(1))?location.hash.slice(1):(selected||state.current_stage);render()}
const chips=items=>`<div class="chips">${items.map(item=>`<span>${esc(pretty(item))}</span>`).join('')}</div>`;
const empty=text=>`<div class="empty-inline">${esc(text)}</div>`;
function stageButton(stage){return `<button class="stage-button ${esc(stage.state)} ${stage.id===selected?'selected':''}" data-stage="${esc(stage.id)}"><b>${esc(stage.number)}</b><span>${esc(stage.label)}</span><i></i></button>`}
function panel(stage){
  if(stage.id==='domain')return `<div class="inside"><h3>Buyer jobs</h3>${chips(state.domain.buyer_jobs||[])}<h3>Reusable content lenses</h3>${chips(state.domain.content_lenses||[])}<p class="note">Changing the active domain replaces this pack; it does not rebuild the engine or copy credentials.</p></div>`;
  if(stage.id==='research')return `<div class="inside"><div class="mini-head"><h3>Source policies</h3><span>${state.source_policies.length}</span></div>${state.source_policies.length?state.source_policies.map(item=>`<article class="row"><div><b>${esc(item.title)}</b><small>${esc(item.summary)}</small></div><span>${esc(item.commercial_reuse||'reuse unrecorded')}</span></article>`).join(''):empty('No source policies recorded yet.')}</div>`;
  if(stage.id==='ontology')return `<div class="inside"><div class="mini-head"><h3>Semantic definitions</h3><span>${state.ontology.length}</span></div><div class="definition-grid">${state.ontology.map(item=>`<article><b>${esc(item.label)}</b><code>${esc(item.key)}</code><p>${esc(item.description)}</p><small>${esc(item.value_type)}${item.unit?' / '+esc(item.unit):''}</small></article>`).join('')}</div><details class="inline-form"><summary>Add a missing concept</summary><form id="ontologyForm"><label>Machine key<input name="field_key" pattern="[a-z][a-z0-9_]+" placeholder="monthly_subscription" required></label><label>Human label<input name="label" placeholder="Monthly subscription" required></label><label>Description<textarea name="description" required placeholder="What this concept means and when it applies"></textarea></label><div class="form-grid"><label>Value type<select name="value_type"><option>text</option><option>number</option><option>boolean</option></select></label><label>Unit<input name="unit" placeholder="optional"></label></div><button>Record additive concept</button></form></details></div>`;
  if(stage.id==='dataset')return `<div class="inside"><div class="mini-head"><h3>Current products</h3><span>${state.products.length}</span></div><div class="product-grid">${state.products.map(item=>`<a href="/intelligence#product/${esc(item.object_id)}"><b>${esc(item.title)}</b><span>${esc(item.market||'market pending')} / ${esc(item.variant||'variant pending')}</span><strong>${item.field_count} fields</strong></a>`).join('')}</div><p class="note">Routine records are automatically monitored. Missing values remain unknown rather than becoming admin tasks.</p></div>`;
  if(stage.id==='direction'){const agent=state.agent_roster.agents.find(a=>a.agent_id==='content_composer');return `<div class="inside"><h3>Standing themes</h3>${chips(state.domain.content_lenses||[])}<h3>Content composer instruction</h3><blockquote>${esc(agent?.instructions||'No instruction loaded.')}</blockquote><button class="subtle-button" data-edit-agent="content_composer">Review or update instruction</button></div>`}
  if(stage.id==='generate')return `<div class="inside"><form id="generateForm" class="generate"><label>Product<select name="product_id">${state.products.map(item=>`<option value="${esc(item.object_id)}">${esc(item.title)}</option>`).join('')}</select></label><label>Posters<select name="max_cards"><option>3</option><option selected>6</option><option>9</option></select></label><label>Short length<select name="duration"><option>30</option><option selected>60</option><option>90</option></select></label><button ${state.products.length?'':'disabled'}>Generate governed package</button></form><div class="mini-head"><h3>Generated plans</h3><span>${state.content.length}</span></div>${state.content.slice(-12).reverse().map(item=>`<article class="row"><div><b>${esc(item.title)}</b><small>${esc(pretty(item.object_type))} / v${item.version}</small></div><span>${esc(item.status)}</span></article>`).join('')||empty('No content generated yet.')}<a class="text-link" href="/discover?preview=1">Open audience preview</a></div>`;
  if(stage.id==='release')return `<div class="inside"><div class="mini-head"><h3>Exact artifacts</h3><span>${state.artifacts.length}</span></div>${state.artifacts.map(item=>`<article class="artifact"><div><b>${esc(item.title)}</b><small>${esc(item.duration_seconds||'?')} seconds / v${item.version}</small></div><div><span class="gate">Rights: ${esc(item.rights_gate||'not cleared')}</span><span class="gate">Facts: ${esc(item.factual_gate||'not cleared')}</span></div><a href="/media-review/${esc(item.object_id)}">Inspect exact artifact</a></article>`).join('')||empty('Generate an artifact before release review.')}<p class="note">Publishing controls appear only when one exact artifact, metadata packet, evidence set and rights manifest are ready.</p></div>`;
  if(stage.id==='learn')return `<div class="inside"><div class="mini-head"><h3>Feedback and decisions</h3><span>${state.feedback.length+events.length}</span></div>${[...events.slice(-8).reverse().map(item=>({title:pretty(item.event_type||item.type||'Audience event'),summary:item.text||item.status||'Captured audience signal'})),...state.feedback.slice(-12).reverse()].map(item=>`<article class="row"><div><b>${esc(item.title)}</b><small>${esc(item.summary)}</small></div><span>${esc(item.classification||item.status||'captured')}</span></article>`).join('')||empty('No feedback captured yet.')}<a class="text-link" href="/discover?preview=1">Test audience feedback</a></div>`;
  return '';
}
function renderStage(){const stage=state.stages.find(item=>item.id===selected)||state.stages[0];$('#stageDetail').innerHTML=`<article class="stage-card" data-number="${esc(stage.number)}"><span class="status ${esc(stage.state)}">${esc(stage.state)}</span><h2>${esc(stage.label)}</h2><p class="evidence">${esc(stage.evidence)}</p><div class="roles"><section class="role"><h3>Agent handles</h3><p>${esc(stage.agent)}</p></section><section class="role human"><h3>You are needed only when</h3><p>${esc(stage.human)}</p></section></div>${panel(stage)}</article>`}
function renderExceptions(){const items=state.exceptions;$('#exceptions').innerHTML=`<div class="section-head"><h2>Questions that truly need you</h2><span>${items.length} open</span></div>`+(items.length?items.map(item=>`<article class="exception"><span class="category">${esc(item.category)}</span><div><h3>${esc(item.title)}</h3><p>${esc(item.reason)}</p></div><div class="decision-actions"><button data-review-id="${esc(item.object_id)}" data-version="${item.version}" data-decision="approved">Approve</button><a href="/#object/${esc(item.object_id)}">Inspect</a></div></article>`).join(''):`<div class="clear"><b>No human decision needed now.</b><span>The agents continue routine governed work. You do not need to review individual records.</span></div>`)}
function renderAgents(){const roster=state.agent_roster;$('#agents').innerHTML=`<div class="section-head"><div><p class="kicker">INTELLIGENCE CONTROL PLANE</p><h2>Agent roster</h2></div><span>${roster.agents.length} task-scoped roles</span></div><p class="section-copy">Review purpose, autonomy, model tier and standing instructions. Tool and authority boundaries remain locked.</p><div class="agent-grid">${roster.agents.map(agent=>`<article class="agent ${agent.enabled?'':'disabled'}"><div><span>${esc(pretty(agent.workflow_stage))}</span><small>profile v${agent.object_version}</small></div><h3>${esc(agent.label)}</h3><p>${esc(agent.purpose)}</p><dl><dt>Autonomy</dt><dd>${esc(pretty(agent.autonomy))}</dd><dt>Model tier</dt><dd>${esc(pretty(agent.model_tier))}</dd></dl><button data-edit-agent="${esc(agent.agent_id)}">Review instructions</button></article>`).join('')}</div><details class="locked"><summary>Locked agent boundaries</summary><ul>${roster.locked_boundaries.map(item=>`<li>${esc(item)}</li>`).join('')}</ul></details>`}
function render(){selected=selected||state.current_stage;$('#operatingRule').textContent=state.operating_rule;$('#domain').innerHTML=`<strong>${esc(state.domain.label)}</strong><span>Active domain pack v${esc(state.domain.version)} / replaceable without rebuilding the engine</span>`;$('#stageNav').innerHTML=state.stages.map(stageButton).join('');renderStage();renderExceptions();renderAgents()}
function toast(message,error=false){const node=$('#toast');node.textContent=message;node.className=error?'show error':'show';setTimeout(()=>node.className='',4000)}
function openAgent(agentId){const agent=state.agent_roster.agents.find(item=>item.agent_id===agentId);if(!agent)return;const dialog=$('#agentDialog');dialog.dataset.agentId=agentId;dialog.querySelector('h2').textContent=agent.label;dialog.querySelector('[name=instructions]').value=agent.instructions;dialog.querySelector('[name=model_tier]').value=agent.model_tier;dialog.querySelector('[name=enabled]').checked=agent.enabled;dialog.querySelector('[name=expected_version]').value=agent.object_version;dialog.querySelector('.agent-purpose').textContent=agent.purpose;dialog.querySelector('.agent-io').textContent=`Inputs: ${agent.inputs.join(', ')}. Outputs: ${agent.outputs.join(', ')}.`;dialog.querySelector('.agent-escalation').textContent=`Escalates: ${agent.escalates_when.join('; ')}.`;dialog.showModal()}
document.addEventListener('click',async event=>{const stage=event.target.closest('[data-stage]');if(stage){selected=stage.dataset.stage;location.hash=selected;render()}const edit=event.target.closest('[data-edit-agent]');if(edit)openAgent(edit.dataset.editAgent);const review=event.target.closest('[data-review-id]');if(review){try{await request(`/v1/objects/${review.dataset.reviewId}/review`,{method:'POST',headers:{'content-type':'application/json','Idempotency-Key':key()},body:JSON.stringify({decision:review.dataset.decision,expected_version:Number(review.dataset.version),notes:'Approved from the prepared exception queue.'})});toast('Decision recorded.');await refresh()}catch(error){toast(error.message,true)}}});
document.addEventListener('submit',async event=>{event.preventDefault();if(event.target.id==='generateForm'){const data=new FormData(event.target);try{await request('/v1/audience/compose',{method:'POST',headers:{'content-type':'application/json','Idempotency-Key':key()},body:JSON.stringify({product_id:data.get('product_id'),max_cards:Number(data.get('max_cards')),short_duration_seconds:Number(data.get('duration'))})});toast('New governed cards and Shorts plan prepared.');await refresh()}catch(error){toast(error.message,true)}}if(event.target.id==='ontologyForm'){const data=new FormData(event.target),field=String(data.get('field_key')).trim();try{await request('/v1/objects',{method:'POST',headers:{'content-type':'application/json','Idempotency-Key':key()},body:JSON.stringify({object_id:`field_${field}`,object_type:'field_definition',domain:state.domain.domain_id.replaceAll('-','_'),title:String(data.get('label')),purpose:'Add a reusable semantic concept requested through the operator workflow.',payload:{key:field,label:String(data.get('label')),description:String(data.get('description')),value_type:String(data.get('value_type')),unit:String(data.get('unit'))||null,category:'all',summary:`Additive ontology concept: ${field}`}})});toast('Concept recorded and available to generated forms.');await refresh()}catch(error){toast(error.message,true)}}if(event.target.id==='agentForm'){const dialog=$('#agentDialog'),data=new FormData(event.target);try{await request(`/v1/operator/agents/${dialog.dataset.agentId}`,{method:'POST',headers:{'content-type':'application/json','Idempotency-Key':key()},body:JSON.stringify({expected_version:Number(data.get('expected_version')),instructions:String(data.get('instructions')),model_tier:String(data.get('model_tier')),enabled:data.get('enabled')==='on',change_reason:String(data.get('change_reason'))})});dialog.close();toast('Agent profile version saved.');await refresh()}catch(error){toast(error.message,true)}}});
$('#closeAgent').addEventListener('click',()=>$('#agentDialog').close());
window.addEventListener('hashchange',()=>{const next=location.hash.slice(1);if(state.stages?.some(stage=>stage.id===next)){selected=next;render();}});
refresh().catch(error=>{$('#stageDetail').innerHTML=`<article class="stage-card"><h2>Workflow unavailable</h2><p>${esc(error.message)}</p></article>`});

/* Stage-scoped data and schema workspace. The guided operator is the only admin surface. */
(() => {
  const stageTypes = {
    domain: [],
    research: ['source_policy', 'refresh_job', 'media_asset', 'market_observation'],
    ontology: ['field_definition'],
    dataset: ['product'],
    direction: ['content_brief'],
    generate: ['content_card', 'card_bundle', 'shorts_plan', 'storyboard', 'render_recipe'],
    release: ['render_artifact', 'release_review_packet', 'commerce_path', 'commerce_assessment', 'commerce_evidence'],
    learn: ['feedback', 'decision_record']
  };
  const catalog = { objects: [], schema: { object_types: {} }, ontology: { items: [], concepts: [], definitions: [] }, ready: false, error: '' };
  let ontologyView = null;
  const pretty = value => String(value || '').replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase());
  const safe = value => esc(value == null ? '' : value);
  const currentStage = () => {
    const candidate = location.hash.slice(1);
    return Object.prototype.hasOwnProperty.call(stageTypes, candidate) ? candidate : 'domain';
  };
  const asObjects = data => Array.isArray(data) ? data : (data?.items || data?.objects || []);

  async function loadStageCatalog() {
    try {
      const [objects, schema, ontology] = await Promise.all([request('/v1/objects'), request('/v1/schema'), request('/v1/semantic/ontology')]);
      catalog.objects = asObjects(objects);
      catalog.schema = schema || { object_types: {} };
      catalog.ontology = ontology || { items: [], concepts: [], definitions: [] };
      catalog.ready = true;
      catalog.error = '';
    } catch (error) {
      catalog.ready = false;
      catalog.error = error.message || 'The object catalogue is unavailable.';
    }
    document.querySelector('#stageDataWorkspace')?.remove();
    injectStageWorkspace();
  }

  function columnsFor(type, records) {
    const descriptor = catalog.schema.object_types?.[type] || {};
    const declared = descriptor.payload_columns || descriptor.columns || descriptor.fields || descriptor.properties;
    if (Array.isArray(declared)) return declared.map(item => typeof item === 'string' ? item : item.name || item.key).filter(Boolean);
    if (declared && typeof declared === 'object') return Object.keys(declared);
    const keys = new Set();
    records.slice(0, 8).forEach(record => Object.keys(record.payload || {}).forEach(key => keys.add(key)));
    return [...keys];
  }

  const ontologyBranches = [
    { id: 'product', label: 'Product catalogue', types: ['product', 'field_definition'], description: 'Buyer-facing product attributes, values, units and comparison meanings.', governed: true },
    { id: 'evidence', label: 'Evidence and rights', types: ['source_policy', 'refresh_job', 'media_asset', 'market_observation'], description: 'Sources, observations, permissions, provenance and refresh policy.' },
    { id: 'content', label: 'Content and media', types: ['content_brief', 'content_card', 'card_bundle', 'shorts_plan', 'storyboard', 'render_recipe', 'render_artifact'], description: 'Reusable stories, cards, scenes, recipes and rendered assets.' },
    { id: 'commerce', label: 'Commerce and release', types: ['commerce_path', 'commerce_assessment', 'commerce_evidence', 'release_review_packet'], description: 'Offers, eligibility, evidence, release gates and publication packets.' },
    { id: 'governance', label: 'Feedback and governance', types: ['feedback', 'decision_record'], description: 'Human input, decisions, policies and traceable system improvement.' }
  ];

  function contractConcepts(branch) {
    const concepts = [];
    branch.types.forEach(type => {
      const records = catalog.objects.filter(item => item.object_type === type);
      columnsFor(type, records).forEach(key => concepts.push({
        concept_id: `contract_${type}_${key}`,
        canonical_name: key,
        label: pretty(key),
        value_type: 'contract field',
        canonical_unit: null,
        category: type,
        status: 'contract_only',
        description: `${pretty(key)} is a payload field in the ${pretty(type)} object contract. It is not yet promoted into the governed semantic registry.`
      }));
    });
    return concepts;
  }

  function conceptsForBranch(branch) {
    if (!branch.governed) return contractConcepts(branch);
    const definitions = new Map((catalog.ontology.definitions || []).map(item => [item.concept_id, item]));
    return (catalog.ontology.concepts || []).map(concept => ({
      ...concept,
      description: definitions.get(concept.concept_id)?.definition || (catalog.ontology.items || []).find(item => item.concept_id === concept.concept_id)?.description || 'Definition unavailable'
    }));
  }

  function ontologyWorkspaceMarkup() {
    if (!ontologyView) {
      return `<section class="stage-data ontology-workspace" id="stageDataWorkspace"><div class="ontology-hero"><p class="kicker">ONTOLOGY MAP</p><h3>The shared language of the business</h3><p>An ontology gives every dataset stable concepts, versioned definitions, relationships and rules. Agents, forms, comparisons and content use this layer instead of guessing what raw columns mean.</p></div><div class="ontology-layers"><article><b>Concepts</b><p>Stable identities, such as weight or subscription requirement.</p></article><article><b>Definitions</b><p>Versioned meaning, data type, unit, scope and constraints.</p></article><article><b>Relationships</b><p>How products, evidence, claims, content and decisions connect.</p></article><article><b>Rules</b><p>Validation, compatibility and revalidation behavior.</p></article></div><div class="ontology-tree"><div class="tree-root"><span>ROOT</span><b>Smart-glasses intelligence ontology</b><small>${ontologyBranches.length} dataset branches</small></div>${ontologyBranches.map(branch => { const concepts = conceptsForBranch(branch); const records = catalog.objects.filter(item => branch.types.includes(item.object_type)); return `<button type="button" class="tree-branch" data-ontology-branch="${branch.id}"><span>${branch.governed ? 'ACTIVE SEMANTIC MODEL' : 'CONTRACT SCHEMA'}</span><b>${safe(branch.label)}</b><p>${safe(branch.description)}</p><small>${records.length} records / ${concepts.length} concepts or contract fields</small></button>`; }).join('')}</div><p class="runtime-boundary"><strong>Current boundary:</strong> Product concepts and definitions are active in the local semantic API. Other branches expose their object-contract fields until those meanings are promoted. Warehouse tables for concepts, definitions, relationships and rules are defined but are not yet the active application store.</p></section>`;
    }
    const branch = ontologyBranches.find(item => item.id === ontologyView.branch) || ontologyBranches[0];
    const page = ontologyView.page || 'concepts';
    const concepts = conceptsForBranch(branch);
    return `<section class="stage-data ontology-workspace" id="stageDataWorkspace"><button type="button" class="text-back" data-ontology-home>Ontology overview</button><div class="ontology-branch-head"><div><p class="kicker">DATASET ONTOLOGY</p><h3>${safe(branch.label)}</h3><p>${safe(branch.description)}</p></div><span>${branch.governed ? 'Governed semantic registry' : 'Contract schema awaiting semantic promotion'}</span></div><nav class="ontology-tabs" aria-label="Ontology dataset pages"><button type="button" class="${page === 'concepts' ? 'active' : ''}" data-ontology-page="concepts">Concepts <span>${concepts.length}</span></button><button type="button" class="${page === 'definitions' ? 'active' : ''}" data-ontology-page="definitions">Definitions <span>${concepts.length}</span></button></nav>${page === 'concepts' ? `<div class="concept-page"><p class="data-intro">Concept identities remain stable when wording or constraints change. Records and assertions reference these identities.</p><div class="concept-table"><div class="concept-row concept-head"><b>Stable identity</b><b>Type / unit</b><b>Status</b></div>${concepts.map(concept => `<div class="concept-row"><span><b>${safe(concept.label)}</b><code>${safe(concept.concept_id)}</code></span><span>${safe(concept.value_type)}${concept.canonical_unit ? ' / ' + safe(concept.canonical_unit) : ''}<small>${safe(pretty(concept.category))}</small></span><span class="concept-status">${safe(pretty(concept.status))}</span></div>`).join('')}</div></div>` : `<div class="definition-page"><p class="data-intro">Definitions can evolve, but every change needs a reason and an impact plan so dependent comparisons and content can be revalidated.</p><div class="definition-list">${concepts.map(concept => `<article><div><b>${safe(concept.label)}</b><code>${safe(concept.concept_id)}</code><p>${safe(concept.description)}</p></div>${branch.governed ? `<button type="button" class="quiet" data-definition-edit="${safe(concept.concept_id)}">Propose definition change</button>` : `<button type="button" class="quiet" data-dataset="${safe(concept.category)}">Open dataset form</button>`}</article>`).join('')}</div></div>`}</section>`;
  }

  function rerenderOntology() {
    document.querySelector('#stageDataWorkspace')?.remove();
    injectStageWorkspace();
  }

  function renderDefinitionEditor(conceptId) {
    ensureDialog();
    const item = (catalog.ontology.items || []).find(entry => entry.concept_id === conceptId);
    if (!item) return;
    const custom = catalog.objects.find(record => record.object_type === 'field_definition' && record.payload?.key === item.key);
    const body = document.querySelector('#stageObjectDialogBody');
    body.innerHTML = `<p class="kicker">ONTOLOGY DEFINITION</p><h2>${safe(item.label)}</h2><p class="object-id">${safe(item.concept_id)} / ${(item.definition_hash || '').slice(0, 12)}</p><div class="form-note"><b>${custom ? 'Versioned custom definition' : 'Protected core definition'}</b><span>${custom ? 'Saving creates a new governed definition version.' : 'The stable concept remains unchanged. This records a change proposal with impact analysis rather than silently overwriting a core meaning.'}</span></div><form id="definitionEditForm"><div class="object-form-grid"><label class="object-field"><span>Label</span><input name="label" value="${safe(item.label)}" required></label><label class="object-field"><span>Value type</span><select name="value_type"><option${item.value_type === 'text' ? ' selected' : ''}>text</option><option${item.value_type === 'number' ? ' selected' : ''}>number</option><option${item.value_type === 'boolean' ? ' selected' : ''}>boolean</option></select></label><label class="object-field object-field--wide"><span>Definition</span><textarea name="description" rows="5" required>${safe(item.description)}</textarea></label><label class="object-field"><span>Canonical unit</span><input name="unit" value="${safe(item.unit || '')}" placeholder="No unit"></label><label class="object-field"><span>Applies to</span><select name="category"><option value="all"${item.category === 'all' ? ' selected' : ''}>All products</option><option value="display"${item.category === 'display' ? ' selected' : ''}>Display</option><option value="camera_audio"${item.category === 'camera_audio' ? ' selected' : ''}>Camera and audio</option><option value="ar"${item.category === 'ar' ? ' selected' : ''}>AR</option></select></label><label class="object-field"><span>Minimum</span><input name="minimum" type="number" step="any" value="${safe(item.minimum ?? '')}"></label><label class="object-field"><span>Maximum</span><input name="maximum" type="number" step="any" value="${safe(item.maximum ?? '')}"></label><label class="object-field object-field--wide"><span>Reason and evidence</span><textarea name="reason" rows="4" required placeholder="Why is the current definition insufficient or incorrect?"></textarea></label><label class="object-field object-field--wide"><span>Compatibility and affected outputs</span><textarea name="compatibility" rows="4" required placeholder="Which records, comparisons, cards, videos or rules must be revalidated?"></textarea></label></div><button type="submit">${custom ? 'Save new definition version' : 'Record change proposal'}</button><p class="form-status" role="status"></p></form>`;
    body.querySelector('#definitionEditForm').onsubmit = async event => {
      event.preventDefault();
      const form = event.currentTarget;
      const status = form.querySelector('.form-status');
      const proposed = { key: item.key, label: form.elements.label.value, description: form.elements.description.value, value_type: form.elements.value_type.value, unit: form.elements.unit.value || null, category: form.elements.category.value, minimum: form.elements.minimum.value === '' ? null : Number(form.elements.minimum.value), maximum: form.elements.maximum.value === '' ? null : Number(form.elements.maximum.value) };
      try {
        status.textContent = 'Recording a traceable ontology change...';
        const headers = { 'Idempotency-Key': 'ontology-change-' + crypto.randomUUID() };
        if (custom) {
          await request('/v1/objects/' + encodeURIComponent(custom.object_id) + '/curate', { method: 'POST', headers, body: JSON.stringify({ expected_version: custom.version, patch: { title: proposed.label, payload: proposed, sources: custom.sources || [], metadata: { ...(custom.metadata || {}), change_reason: form.elements.reason.value, compatibility_plan: form.elements.compatibility.value } } }) });
        } else {
          await request('/v1/objects', { method: 'POST', headers, body: JSON.stringify({ object_type: 'feedback', domain: 'smart_glasses', title: 'Definition change: ' + item.label, purpose: 'Capture a governed semantic-definition change without mutating its stable concept identity.', tags: ['ontology', 'definition_change'], source: [], sources: [], metadata: { concept_id: item.concept_id, current_definition_hash: item.definition_hash }, payload: { summary: 'Revise the definition of ' + item.label, input: JSON.stringify({ current: { label: item.label, description: item.description, value_type: item.value_type, unit: item.unit, category: item.category, minimum: item.minimum, maximum: item.maximum }, proposed, reason: form.elements.reason.value, compatibility: form.elements.compatibility.value }), classification: 'correction', target_ids: [item.concept_id], proposed_improvement: 'Create a new definition version, preserve the concept identity, run compatibility checks, and revalidate affected outputs. ' + form.elements.compatibility.value, system_area: 'ontology_schema', authority: 'operating_directive' } }) });
        }
        await loadStageCatalog();
        await refresh();
        document.querySelector('#stageObjectDialog').close();
        document.querySelector('#toast').textContent = custom ? 'Definition saved as a new governed version.' : 'Definition change captured for impact review.';
      } catch (error) {
        status.textContent = error.message || 'The ontology change could not be recorded.';
      }
    };
    document.querySelector('#stageObjectDialog').showModal();
  }

  function stageWorkspaceMarkup(stage) {
    const types = stageTypes[stage];
    if (!catalog.ready) return `<section id="stageDataWorkspace" class="stage-data"><div class="data-heading"><div><p class="kicker">DATA &amp; SCHEMA</p><h3>Stage workspace</h3></div></div><p class="note">${safe(catalog.error || 'Loading governed records...')}</p></section>`;
    if (stage === 'ontology') return ontologyWorkspaceMarkup();
    const cards = types.map(type => {
      const records = catalog.objects.filter(item => item.object_type === type);
      const columns = columnsFor(type, records);
      return `<article class="dataset-card"><div class="dataset-card__top"><div><span class="dataset-type">${safe(type)}</span><h4>${safe(pretty(type))}</h4></div><strong>${records.length}</strong></div><p>${columns.length ? safe(columns.slice(0, 7).join(' / ')) : 'No payload columns are active yet.'}</p><button type="button" class="quiet" data-dataset="${safe(type)}">Inspect${records.length ? ' and edit' : ''}</button></article>`;
    }).join('');
    const empty = stage === 'domain' ? '<div class="dataset-empty"><b>Domain pack</b><p>The domain definition above configures this engine. Its governed datasets begin in Research and remain visible in every following stage.</p></div>' : '';
    return `<section class="stage-data" id="stageDataWorkspace"><div class="data-heading"><div><p class="kicker">DATA &amp; SCHEMA</p><h3>What this stage reads and writes</h3></div><div class="data-actions"><button type="button" class="quiet" data-schema-editor>View all schema</button><button type="button" class="quiet" data-ontology-editor>Edit semantic fields</button></div></div><p class="data-intro">Inspect versioned records here without leaving the workflow. Forms are generated from each record's current payload; evidence and source links are preserved.</p><div class="dataset-grid">${cards}${empty}</div></section>`;
  }

  function ensureDialog() {
    if (document.querySelector('#stageObjectDialog')) return;
    document.body.insertAdjacentHTML('beforeend', '<dialog id="stageObjectDialog" class="object-dialog"><button type="button" class="dialog-close" aria-label="Close">Close</button><div id="stageObjectDialogBody"></div></dialog>');
    const dialog = document.querySelector('#stageObjectDialog');
    dialog.querySelector('.dialog-close').onclick = () => dialog.close();
  }

  function renderSchemaCatalogue() {
    ensureDialog();
    const body = document.querySelector('#stageObjectDialogBody');
    const knownTypes = [...new Set([...Object.keys(catalog.schema.object_types || {}), ...catalog.objects.map(item => item.object_type)])].sort();
    body.innerHTML = `<p class="kicker">SYSTEM CATALOGUE</p><h2>Datasets and object contracts</h2><p>All contracts remain versioned and attributable. Choose a workflow stage to work with records in context.</p><div class="schema-table"><div class="schema-row schema-head"><b>Dataset</b><b>Records</b><b>Payload columns</b></div>${knownTypes.map(type => { const records = catalog.objects.filter(item => item.object_type === type); return `<div class="schema-row"><span><b>${safe(pretty(type))}</b><code>${safe(type)}</code></span><strong>${records.length}</strong><span>${safe(columnsFor(type, records).join(', ') || 'No active columns')}</span></div>`; }).join('')}</div>`;
    document.querySelector('#stageObjectDialog').showModal();
  }

  function renderDataset(type) {
    ensureDialog();
    const records = catalog.objects.filter(item => item.object_type === type);
    const body = document.querySelector('#stageObjectDialogBody');
    body.innerHTML = `<p class="kicker">${safe(type)}</p><h2>${safe(pretty(type))}</h2><p>${records.length} current versioned record${records.length === 1 ? '' : 's'}. Select a record to inspect and edit through its generated form.</p>${records.length ? `<div class="record-list">${records.map(item => `<article><div><b>${safe(item.title || item.object_id)}</b><small>v${safe(item.version)} / ${safe(pretty(item.review_state || item.state || 'captured'))}</small></div><button type="button" class="quiet" data-record="${safe(item.object_id)}">Open form</button></article>`).join('')}</div>` : '<div class="dataset-empty"><b>No records yet</b><p>The responsible agent can create this object type when its evidence and workflow prerequisites are satisfied.</p></div>'}`;
    body.querySelectorAll('[data-record]').forEach(button => button.onclick = () => renderRecord(button.dataset.record));
    document.querySelector('#stageObjectDialog').showModal();
  }

  function fieldControl(key, value) {
    const label = `<span>${safe(pretty(key))}</span><code>${safe(key)}</code>`;
    if (typeof value === 'boolean') return `<label class="object-field">${label}<select name="${safe(key)}" data-kind="boolean"><option value="true"${value ? ' selected' : ''}>True</option><option value="false"${!value ? ' selected' : ''}>False</option></select></label>`;
    if (typeof value === 'number') return `<label class="object-field">${label}<input name="${safe(key)}" type="number" step="any" value="${safe(value)}" data-kind="number"></label>`;
    if (value && typeof value === 'object') return `<label class="object-field object-field--wide">${label}<textarea name="${safe(key)}" rows="7" data-kind="json">${safe(JSON.stringify(value, null, 2))}</textarea></label>`;
    return `<label class="object-field">${label}<input name="${safe(key)}" value="${safe(value)}" data-kind="text"></label>`;
  }

  function renderRecord(id) {
    const item = catalog.objects.find(record => record.object_id === id);
    if (!item) return;
    const body = document.querySelector('#stageObjectDialogBody');
    body.innerHTML = `<button type="button" class="text-back">Back to ${safe(pretty(item.object_type))}</button><p class="kicker">VERSIONED OBJECT / V${safe(item.version)}</p><h2>${safe(item.title || item.object_id)}</h2><p class="object-id">${safe(item.object_id)}</p><form id="stageObjectForm"><label class="object-field object-field--wide"><span>Record title</span><input name="__title" value="${safe(item.title || '')}" required></label><div class="object-form-grid">${Object.entries(item.payload || {}).map(([key, value]) => fieldControl(key, value)).join('')}</div><div class="form-note"><b>Preserved automatically</b><span>${(item.sources || []).length} source reference${(item.sources || []).length === 1 ? '' : 's'}, object identity, history and attribution.</span></div><label class="object-field object-field--wide"><span>Revision reason</span><textarea name="__reason" required placeholder="What changed and why"></textarea></label><button type="submit">Save a new version</button><p class="form-status" role="status"></p></form>`;
    body.querySelector('.text-back').onclick = () => renderDataset(item.object_type);
    body.querySelector('#stageObjectForm').onsubmit = async event => {
      event.preventDefault();
      const form = event.currentTarget;
      const status = form.querySelector('.form-status');
      const payload = { ...(item.payload || {}) };
      try {
        form.querySelectorAll('[name]:not([name^="__"])').forEach(control => {
          if (control.dataset.kind === 'json') payload[control.name] = JSON.parse(control.value);
          else if (control.dataset.kind === 'boolean') payload[control.name] = control.value === 'true';
          else if (control.dataset.kind === 'number') payload[control.name] = control.value === '' ? null : Number(control.value);
          else payload[control.name] = control.value;
        });
        status.textContent = 'Saving a traceable version...';
        await request('/v1/objects/' + encodeURIComponent(item.object_id) + '/curate', { method: 'POST', headers: { 'Idempotency-Key': 'operator-edit-' + crypto.randomUUID() }, body: JSON.stringify({ expected_version: item.version, patch: { title: form.elements.__title.value, payload, sources: item.sources || [], metadata: { ...(item.metadata || {}), last_revision_reason: form.elements.__reason.value } } }) });
        await loadStageCatalog();
        await refresh();
        document.querySelector('#stageObjectDialog').close();
        document.querySelector('#toast').textContent = 'Saved as a new governed version.';
      } catch (error) {
        status.textContent = error.message || 'The change could not be saved.';
      }
    };
  }

  function openOntologyEditor() {
    location.hash = 'ontology';
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const details = document.querySelector('#ontologyForm')?.closest('details');
      if (details) {
        details.open = true;
        details.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }));
  }

  function bindStageWorkspace() {
    document.querySelectorAll('[data-dataset]').forEach(button => button.onclick = () => renderDataset(button.dataset.dataset));
    document.querySelectorAll('[data-ontology-branch]').forEach(button => button.onclick = () => { ontologyView = { branch: button.dataset.ontologyBranch, page: 'concepts' }; rerenderOntology(); });
    document.querySelectorAll('[data-ontology-page]').forEach(button => button.onclick = () => { ontologyView.page = button.dataset.ontologyPage; rerenderOntology(); });
    document.querySelector('[data-ontology-home]')?.addEventListener('click', () => { ontologyView = null; rerenderOntology(); });
    document.querySelectorAll('[data-definition-edit]').forEach(button => button.onclick = () => renderDefinitionEditor(button.dataset.definitionEdit));
    document.querySelector('[data-schema-editor]')?.addEventListener('click', renderSchemaCatalogue);
    document.querySelector('[data-ontology-editor]')?.addEventListener('click', openOntologyEditor);
  }

  function injectStageWorkspace() {
    const card = document.querySelector('#stageDetail .stage-card');
    if (!card || card.querySelector('#stageDataWorkspace')) return;
    card.classList.toggle('ontology-redesigned', currentStage() === 'ontology');
    card.insertAdjacentHTML('beforeend', stageWorkspaceMarkup(currentStage()));
    bindStageWorkspace();
  }

  const stageRoot = document.querySelector('#stageDetail');
  if (stageRoot) new MutationObserver(injectStageWorkspace).observe(stageRoot, { childList: true, subtree: true });
  window.addEventListener('hashchange', injectStageWorkspace);
  ensureDialog();
  injectStageWorkspace();
  loadStageCatalog();
})();

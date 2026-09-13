(function () {
  'use strict';
  let bridge;
  let active = null;
  let position = 0;
  let startedAt = 0;
  let playing = false;
  let frame = 0;
  let shown = -1;
  const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const pretty = value => String(value || '').replaceAll('_', ' ');
  const record = object => '#object/' + encodeURIComponent(object.object_id);
  const date = value => value ? new Date(value).toLocaleString() : 'Not recorded';
  const lookup = id => bridge.state.objects.find(object => object.object_id === id);
  const ofType = type => bridge.state.objects.filter(object => object.object_type === type);
  const retained = object => !['archived', 'rejected', 'deprecated'].includes(object.status);
  const chip = text => '<span class="chip">' + esc(text) + '</span>';
  const warning = text => '<div class="callout">' + esc(text) + '</div>';

  function notice(message) {
    const node = document.getElementById('notice');
    node.textContent = message;
    node.hidden = false;
    setTimeout(() => { if (node.textContent === message) node.hidden = true; }, 6500);
  }
  function stale(object) {
    if (object.object_type === 'storyboard') {
      const brief = lookup(object.payload.brief_object_id);
      return !brief || brief.version !== object.payload.brief_version || stale(brief);
    }
    return Object.entries(object.payload.input_versions || object.metadata.source_versions || {})
      .some(([id, version]) => lookup(id)?.version !== version);
  }
  function sceneMarkup(scene, index, count) {
    return '<div class="scene-watermark">PRIVATE DRAFT / NOT A HANDS-ON TEST</div>' +
      '<div class="scene-kicker">' + esc(pretty(scene.primitive)) + '</div>' +
      '<div class="scene-copy"><h2>' + esc(scene.heading) + '</h2><div class="scene-lines">' +
      scene.lines.map(line => '<p>' + esc(line) + '</p>').join('') +
      '</div></div><span class="scene-number" aria-hidden="true">' + String(index + 1).padStart(2, '0') +
      '</span><div class="scene-footer"><span>ORIGINAL ABSTRACT GRAPHICS / NOT PRODUCT PHOTOGRAPHY</span><span>' +
      (index + 1) + ' / ' + count + '</span></div>';
  }
  function notesMarkup(scene) {
    const notes = Array.isArray(scene.notes) ? scene.notes : (scene.notes ? [scene.notes] : []);
    return '<h3>Evidence and caveats for this scene</h3>' +
      (notes.length ? '<ul>' + notes.map(note => '<li>' + esc(note) + '</li>').join('') + '</ul>' :
        '<p class="muted">Editorial framing, not a new product assertion.</p>') +
      '<p class="small">Claim references: ' + esc((scene.claim_ids || []).join(', ') || 'No factual claim IDs in this scene') + '</p>';
  }
  function sceneAt(seconds) {
    let elapsed = 0;
    for (let index = 0; index < active.payload.scenes.length; index++) {
      elapsed += active.payload.scenes[index].duration_seconds;
      if (seconds < elapsed) return index;
    }
    return active.payload.scenes.length - 1;
  }
  function update(force) {
    if (!active) return;
    const stage = document.getElementById('production-stage');
    if (!stage) { stop(); return; }
    const index = sceneAt(position);
    const scene = active.payload.scenes[index];
    if (index !== shown || force) {
      shown = index;
      stage.className = 'production-stage palette-' + index % 3 + ' primitive-' + scene.primitive +
        (active.payload.aspect_ratio === '9:16' ? ' portrait' : '');
      stage.innerHTML = sceneMarkup(scene, index, active.payload.scenes.length);
      document.getElementById('production-notes').innerHTML = notesMarkup(scene);
    }
    document.getElementById('production-progress').value = position;
    document.getElementById('production-clock').textContent =
      Math.floor(position) + 's / ' + active.payload.duration_seconds + 's';
    document.getElementById('production-play').textContent = playing ? 'Pause' : 'Play preview';
  }
  function tick(now) {
    if (!playing || !active) return;
    position = Math.min((now - startedAt) / 1000, active.payload.duration_seconds);
    if (position >= active.payload.duration_seconds) playing = false;
    update(false);
    if (playing) frame = requestAnimationFrame(tick);
  }
  function stop() { cancelAnimationFrame(frame); playing = false; }
  function seek(index) {
    stop();
    position = active.payload.scenes.slice(0, Math.max(0, Math.min(index, active.payload.scenes.length - 1)))
      .reduce((sum, scene) => sum + scene.duration_seconds, 0);
    update(true);
  }
  function render(object) {
    stop();
    active = object;
    position = 0;
    shown = 0;
    const payload = object.payload;
    const first = payload.scenes[0];
    return warning('Animated storyboard preview only. No MP4 export, narration, product-photo licence or publication approval is implied.') +
      '<article class="card production-player"><div class="production-stage palette-0 primitive-' +
      esc(first.primitive) + (payload.aspect_ratio === '9:16' ? ' portrait' : '') +
      '" id="production-stage">' + sceneMarkup(first, 0, payload.scenes.length) +
      '</div><div class="actions production-controls"><button id="production-play" data-production-action="play">Play preview</button>' +
      '<button class="quiet" data-production-action="previous">Previous scene</button>' +
      '<button class="quiet" data-production-action="next">Next scene</button>' +
      '<button class="quiet" data-production-action="restart">Restart</button>' +
      '<span id="production-clock">0s / ' + payload.duration_seconds + 's</span></div>' +
      '<progress id="production-progress" max="' + payload.duration_seconds + '" value="0" aria-label="Preview progress"></progress>' +
      '<div id="production-notes" class="production-notes">' + notesMarkup(first) + '</div></article>' +
      '<article class="card"><h3>Reusable scene plan</h3><p class="small">Family: ' + esc(pretty(payload.workflow_family)) +
      ' / ' + esc(payload.aspect_ratio) + ' / No narration</p><ol>' +
      payload.scenes.map(scene => '<li><strong>' + esc(scene.heading) + '</strong> <span class="muted">' +
        scene.duration_seconds + ' seconds / ' + esc(pretty(scene.primitive)) + '</span></li>').join('') + '</ol></article>';
  }
  async function sourcePage() {
    const response = await bridge.api('/sources/refresh-plan');
    const jobs = ofType('refresh_job');
    return '<div class="page-heading"><div><p class="eyebrow">MAINTAIN THE EVIDENCE</p><h1>Sources &amp; refresh planning</h1></div>' +
      '<button data-queue-refresh="1">Prepare update queue</button></div>' +
      warning('This is a planning queue, not a running collector. It makes no source requests and spends no API budget. Routine jobs do not need human factual approval; source permissions still do.') +
      '<div class="grid">' + response.items.map(plan => {
        const policy = lookup(plan.source_policy_id);
        return '<article class="card">' + chip(plan.state) + '<h2>' + esc(policy.title) +
          '</h2><p><a target="_blank" rel="noopener noreferrer" href="' + esc(plan.source_uri) + '">Source page</a></p>' +
          '<dl class="source-plan-meta"><dt>Next planned update</dt><dd>' + esc(date(plan.planned_for)) +
          '</dd><dt>Permission review expires</dt><dd>' + esc(date(policy.payload.permission_expires_at)) +
          '</dd><dt>Policy revision</dt><dd>' + policy.version + '</dd></dl><h3>What prevents collection</h3><ul>' +
          plan.blockers.map(blocker => '<li>' + esc(blocker) + '</li>').join('') +
          '</ul><div class="actions"><button class="quiet" data-edit-source="' + esc(policy.object_id) +
          '">Propose policy update</button><a href="' + record(policy) + '">Evidence &amp; history</a></div></article>';
      }).join('') + '</div><h2>Saved planning jobs</h2><p class="muted">Policy changes require a new plan. Nothing here starts a network worker.</p>' +
      '<div class="grid">' + (jobs.map(job => '<article class="card">' +
        chip(lookup(job.payload.source_policy_id)?.version === job.payload.source_policy_version ? 'blocked / no execution' : 'superseded policy') +
        '<h3><a href="' + record(job) + '">' + esc(job.title) + '</a></h3><p class="small">' +
        esc(date(job.payload.planned_for)) + '</p></article>').join('') || '<p>No plans saved yet.</p>') + '</div>';
  }
  function reviewInbox() {
    const route = object => { const p = object.payload || {}, t = String(object.object_type || '').toLowerCase(), reserved = { publication_request: 'Publication', publication_decision: 'Publication', release_authorization: 'Publication', spend_authorization: 'Financial', budget_change: 'Financial', credential_transfer: 'Security', account_consent: 'Account', contract_acceptance: 'Legal' }; if (reserved[t]) return { required: true, category: reserved[t] }; if (p.human_review_required === true) return { required: true, category: pretty(p.review_category || 'Explicit exception') }; const kind = [p.decision_type, p.kind, p.proposal_type, p.change_class].filter(Boolean).join(' ').toLowerCase(); if (/publish|release_authorization|spend|budget_increase|contract|credential/.test(kind)) return { required: true, category: 'Reserved decision' }; if (p.breaking_change === true || p.meaning_change === true || p.permission_expansion === true) return { required: true, category: 'Ontology or policy' }; const issue = [p.evidence_state, p.conflict_state, p.validation_state, p.source_state].filter(Boolean).join(' ').toLowerCase(); if ((p.consequential === true || p.decision_critical === true) && /conflict|contradict|unresolved|failed/.test(issue)) return { required: true, category: 'Evidence conflict' }; const rights = [p.rights_state, p.permission_state, p.commercial_reuse, p.license_state].filter(Boolean).join(' ').toLowerCase(); if (/unresolved|unknown|denied|expired|restricted/.test(rights) && p.rights_question_resolved !== true) return { required: true, category: 'Rights and legal' }; if (p.account_holder_action_required === true) return { required: true, category: 'Account' }; if (p.exact_artifact_publication_candidate === true) return { required: true, category: 'Publication' }; return { required: false, category: 'Automatic' }; };
    const items = bridge.state.objects.filter(object => ['captured', 'proposed'].includes(object.status) && route(object).required);
    return '<div class="page-heading"><div><p class="eyebrow">EXCEPTIONS, NOT DATA ENTRY</p><h1>Decision inbox</h1></div>' + chip(items.length + ' decisions') +
      '</div><p class="muted">Routine facts, concepts, analyses, feedback and private drafts are policy-routed and monitored automatically. Only consequential unresolved boundaries come here.</p><div class="grid">' +
      (items.map(object => '<article class="card">' + chip(route(object).category) + '<h2><a href="' + record(object) + '">' + esc(object.title) +
        '</a></h2><p>' + esc(object.payload.review_reason || object.payload.summary || object.purpose) + '</p>' + chip(stale(object) ? 'inputs changed' : 'decision prepared') + '</article>').join('') ||
        '<article class="card"><h2>No human action needed</h2><p>The exception queue is clear. Work continues automatically and remains fully auditable.</p></article>') + '</div>';
  }
  function contentStudio() {
    const briefs = ofType('content_brief').filter(object => object.payload.workflow_family && object.payload.input_versions && retained(object) && !stale(object));
    const plans = ofType('storyboard').filter(retained);
    return '<div class="page-heading"><div><p class="eyebrow">ONE EVIDENCE BASE / MANY STORIES</p><h1>Make the evidence move</h1></div>' + chip('Local / no generation cost') +
      '</div><p class="lead">Product stories, feature explainers and fair comparisons share reusable visual primitives, not identical scripts.</p>' +
      warning('These are private, silent animated storyboards with original abstract backgrounds. They are not final rendered videos or evidence of licensed product photography.') +
      '<article class="card"><h2>Turn a current brief into a preview</h2><div class="plan-control-grid"><label>Source-linked brief<select id="storyboard-brief">' +
      briefs.map(brief => '<option value="' + esc(brief.object_id) + '">' + esc(brief.title) + '</option>').join('') +
      '</select></label><label>Canvas<select id="storyboard-aspect"><option value="16:9">Landscape / 16:9</option><option value="9:16">Portrait / 9:16</option></select></label>' +
      '<button data-create-storyboard="1"' + (briefs.length ? '' : ' disabled') + '>Prepare animated preview</button></div>' +
      (!briefs.length ? '<p class="muted">Compose a source-linked brief below first.</p>' : '') + '</article><div class="grid">' +
      plans.map(plan => '<article class="card">' + chip(pretty(plan.payload.workflow_family)) +
        '<h2><a href="' + record(plan) + '">' + esc(plan.title) + '</a></h2><p>' + plan.payload.duration_seconds + ' seconds / ' +
        esc(plan.payload.aspect_ratio) + ' / ' + plan.payload.scenes.length + ' scenes</p><p class="small">' +
        (stale(plan) ? 'Inputs changed. Rebuild before review.' : 'Private draft. Facts and layout still need review.') +
        '</p><a class="button" href="' + record(plan) + '">Open animated preview</a></article>').join('') +
      '</div><hr class="production-divider"><h2>Compose another story</h2>';
  }
  const field = (label, name, value, type = 'text') => '<label>' + esc(label) + '<input name="' + esc(name) +
    '" type="' + type + '" value="' + esc(value || '') + '"' + (type === 'number' ? ' min="1" max="365" step="1"' : '') + '></label>';
  const area = (label, name, value) => '<label>' + esc(label) + '<textarea name="' + esc(name) + '" rows="3">' + esc(value || '') + '</textarea></label>';
  const choice = (label, name, value, values) => '<label>' + esc(label) + '<select name="' + name + '">' +
    values.map(option => '<option value="' + option + '"' + (option === value ? ' selected' : '') + '>' + esc(pretty(option)) + '</option>').join('') + '</select></label>';
  function editPolicy(id) {
    const policy = lookup(id);
    const payload = policy.payload;
    const dialog = document.getElementById('editor');
    document.getElementById('editor-body').innerHTML = '<h2>Propose a source-policy update</h2>' +
      warning('Record documented permission, not an assumption. Saving creates a proposal and resets review. This form cannot grant permission or enable a collector.') +
      '<form id="production-policy-form" class="editor-form">' + area('Summary', 'summary', payload.summary) +
      field('Terms or permission URL', 'terms_uri', payload.terms_uri, 'url') +
      area('Documented rights basis', 'rights_basis', payload.rights_basis) + area('Required attribution', 'attribution', payload.attribution) +
      choice('Access method', 'access', payload.access, ['manual_excerpt', 'api', 'licensed_feed']) +
      ['automation', 'commercial_reuse', 'media_reuse'].map(name => choice(pretty(name), name, payload[name], ['pending', 'allowed', 'denied'])).join('') +
      field('Refresh interval in days', 'refresh_days', payload.refresh_days, 'number') +
      field('Permission review expiry, ISO timestamp with timezone', 'permission_expires_at', payload.permission_expires_at) +
      '<p class="small">Changing policy does not change when the source was last observed.</p><button type="submit">Save proposal</button></form>';
    const form = document.getElementById('production-policy-form');
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const submit = form.querySelector('button[type="submit"]');
      submit.disabled = true;
      try {
        const values = Object.fromEntries(new FormData(form));
        await bridge.api('/objects/' + encodeURIComponent(id) + '/curate', {
          method: 'POST', headers: {'Idempotency-Key': crypto.randomUUID()}, body: JSON.stringify({expected_version: policy.version, patch: {payload: {
            ...payload, ...values, refresh_days: Number(values.refresh_days),
            terms_uri: values.terms_uri.trim() || null, permission_expires_at: values.permission_expires_at.trim() || null
          }}})
        });
        dialog.close();
        await bridge.reload();
        notice('Policy proposal saved. Review and collection permissions remain separate.');
      } catch (error) { notice(error.message); }
      finally { submit.disabled = false; }
    });
    dialog.showModal();
  }
  document.addEventListener('click', async event => {
    const button = event.target.closest('button');
    if (!button) return;
    const action = button.dataset.productionAction;
    if (action) {
      event.stopImmediatePropagation();
      if (!active) return;
      if (action === 'play') {
        if (playing) { stop(); update(false); }
        else {
          if (position >= active.payload.duration_seconds) position = 0;
          playing = true; startedAt = performance.now() - position * 1000;
          update(false); frame = requestAnimationFrame(tick);
        }
      } else if (action === 'restart') seek(0);
      else seek(sceneAt(position) + (action === 'next' ? 1 : -1));
      return;
    }
    if (!bridge || (!button.dataset.queueRefresh && !button.dataset.editSource && !button.dataset.createStoryboard)) return;
    event.stopImmediatePropagation();
    button.disabled = true;
    try {
      if (button.dataset.editSource) { editPolicy(button.dataset.editSource); return; }
      if (button.dataset.queueRefresh) {
        await bridge.api('/sources/refresh-plan', {method: 'POST'});
        await bridge.reload(); notice('Planning jobs saved. No collection worker was started.'); return;
      }
      const brief = lookup(document.getElementById('storyboard-brief').value);
      if (!brief) throw new Error('Choose a current content brief first.');
      const result = await bridge.api('/content/storyboards', {method: 'POST', body: JSON.stringify({
        brief_object_id: brief.object_id, expected_version: brief.version,
        aspect_ratio: document.getElementById('storyboard-aspect').value
      })});
      await bridge.reload();
      location.hash = record(result);
      notice('Private storyboard prepared. No video was published.');
    } catch (error) { notice(error.message); }
    finally { button.disabled = false; }
  }, true);
  window.addEventListener('hashchange', stop);
  window.addEventListener('pagehide', stop);
  window.WorkspaceProduction = {configure: value => { bridge = value; }, render, stop, sourcePage, reviewInbox, contentStudio};
}());

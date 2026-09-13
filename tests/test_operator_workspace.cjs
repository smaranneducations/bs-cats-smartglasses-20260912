const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');

const source = fs.readFileSync(path.join(__dirname, '../apps/operator/operator-v1.js'), 'utf8');
const settle = () => new Promise(resolve => setImmediate(resolve));

function fixture() {
  let workspace = null;
  const inserted = [], observers = [], calls = [], pending = new Map(), listeners = new Map(), nodes = new Map();
  const node = selector => {
    if (!nodes.has(selector)) nodes.set(selector, {innerHTML: '', textContent: '', addEventListener() {}, classList: {toggle() {}}});
    return nodes.get(selector);
  };
  const root = node('#stageDetail');
  let markup = '';
  Object.defineProperty(root, 'innerHTML', {get: () => markup, set: value => {markup = value; workspace = null;}});
  const card = {
    classList: {toggle() {}},
    querySelector: selector => selector === '#stageDataWorkspace' ? workspace : null,
    insertAdjacentHTML(position, value) {
      inserted.push(value);
      if (value.includes('id="stageDataWorkspace"')) workspace = {remove() {workspace = null;}};
    }
  };
  const document = {
    querySelector(selector) {
      if (selector === '#stageDetail .stage-card') return card;
      if (selector === '#stageDataWorkspace') return workspace;
      return node(selector);
    },
    querySelectorAll: () => [],
    addEventListener() {}
  };
  const location = {hash: '#domain'};
  const context = vm.createContext({document, location, Headers, console, crypto: webcrypto,
    setTimeout: () => 1, requestAnimationFrame: callback => callback(),
    window: {addEventListener(type, callback) {if (!listeners.has(type)) listeners.set(type, []); listeners.get(type).push(callback);}},
    MutationObserver: class {constructor(callback) {observers.push(callback);} observe() {}},
    fetch(url, options) {
      calls.push({url, options});
      return new Promise(resolve => {if (!pending.has(url)) pending.set(url, []); pending.get(url).push(resolve);});
    }
  });
  vm.runInContext(source, context);
  return {context, inserted, calls, nodes, location,
    notify() {observers.forEach(callback => callback());},
    changeHash(hash) {location.hash = hash; (listeners.get('hashchange') || []).forEach(callback => callback());},
    respond(url, data, status = 200) {
      const response = {ok: status >= 200 && status < 300, status, json: async () => data};
      (pending.get(url) || []).splice(0).forEach(resolve => resolve(response));
    }
  };
}

test('loading workspace is mounted once, even after repeated observer notifications', () => {
  const f = fixture();
  for (let index = 0; index < 100; index++) f.notify();
  assert.equal(f.inserted.length, 1);
  assert.match(f.inserted[0], /Loading governed records/);
});

test('failed catalogue replaces loading once without an observer loop', async () => {
  const f = fixture();
  f.respond('/v1/objects', {detail: 'Catalogue unavailable'}, 503);
  await settle();
  for (let index = 0; index < 100; index++) f.notify();
  assert.equal(f.inserted.length, 2);
  assert.match(f.inserted[1], /Catalogue unavailable/);
});

test('loaded catalogue replaces its placeholder once and remains stable', async () => {
  const f = fixture();
  f.respond('/v1/objects', {items: []});
  f.respond('/v1/schema', {object_types: {}});
  f.respond('/v1/semantic/ontology', {items: [], concepts: [], definitions: []});
  await settle();
  for (let index = 0; index < 100; index++) f.notify();
  assert.equal(f.inserted.length, 2);
  assert.match(f.inserted[1], /What this stage reads and writes/);
});

test('JSON writes carry the workspace guard and preserve idempotency headers', async () => {
  const f = fixture();
  const response = vm.runInContext("request('/v1/fixture',{method:'POST',body:'{}',headers:{'Idempotency-Key':'fixture-operation'}})", f.context);
  const call = f.calls.at(-1);
  assert.equal(call.options.headers.get('Content-Type'), 'application/json');
  assert.equal(call.options.headers.get('X-Workspace-Action'), '1');
  assert.equal(call.options.headers.get('Idempotency-Key'), 'fixture-operation');
  f.respond('/v1/fixture', {accepted: true});
  assert.equal((await response).accepted, true);
});

test('request respects an explicitly supplied content type', async () => {
  const f = fixture();
  const response = vm.runInContext("request('/v1/fixture',{method:'POST',body:'text',headers:{'Content-Type':'text/plain'}})", f.context);
  assert.equal(f.calls.at(-1).options.headers.get('Content-Type'), 'text/plain');
  f.respond('/v1/fixture', {});
  await response;
});

test('API rejection remains an error rather than a success acknowledgement', async () => {
  const f = fixture();
  const response = vm.runInContext("request('/v1/fixture')", f.context);
  f.respond('/v1/fixture', {detail: 'Version conflict'}, 409);
  await assert.rejects(response, /Version conflict/);
});

test('hash navigation rerenders the matching stage instead of leaving the previous page', () => {
  const f = fixture();
  const workflow = {stages: [{id: 'domain', number: 1, label: 'Domain'}, {id: 'ontology', number: 2, label: 'Ontology'}],
    domain: {label: 'Fixture', version: 1}, ontology: [], exceptions: [], agent_roster: {agents: [], locked_boundaries: []}};
  vm.runInContext('state=' + JSON.stringify(workflow), f.context);
  f.changeHash('#ontology');
  assert.equal(vm.runInContext('selected', f.context), 'ontology');
  assert.match(f.nodes.get('#stageDetail').innerHTML, /<h2>Ontology<\/h2>/);
  f.changeHash('#domain');
  assert.equal(vm.runInContext('selected', f.context), 'domain');
});

test('navigation before workflow data arrives does not throw or fabricate stages', () => {
  const f = fixture();
  assert.doesNotThrow(() => f.changeHash('#ontology'));
  assert.equal(vm.runInContext('selected', f.context), 'domain');
});

test('operator writes never claim a hardcoded founder identity', () => {
  assert.doesNotMatch(source, /(?:reviewer_id|actor_id)\s*:\s*['"]founder['"]/);
});

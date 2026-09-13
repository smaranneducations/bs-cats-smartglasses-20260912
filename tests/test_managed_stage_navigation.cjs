const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../apps/operator/stage-admin.js'), 'utf8');

async function fixture() {
  let workspace = null;
  const inserted = [], listeners = new Map();
  const product = {dataset: {managedType: 'product'}, onclick: null};
  const root = {};
  const card = {
    querySelector(selector) {return ['.managed-workspace', '#stageDataWorkspace'].includes(selector) ? workspace : null;},
    insertAdjacentHTML(position, text) {inserted.push(text); workspace = {remove() {workspace = null;}};}
  };
  const location = {hash: '#dataset'};
  const context = vm.createContext({location,
    document: {
      querySelector(selector) {
        if (selector === '#stageDetail .stage-card') return card;
        if (selector === '#stageDetail') return root;
        if (selector === '#stageDataWorkspace') return workspace;
        return null;
      },
      querySelectorAll(selector) {return selector === '[data-managed-type]' ? [product] : [];}
    },
    window: {addEventListener(type, callback) {listeners.set(type, callback);}},
    MutationObserver: class {observe() {}},
    fetch: async url => ({ok: true, json: async () => url === '/v1/objects' ? {items: []} : url === '/v1/schema' ? {object_types: {}} : {}})
  });
  vm.runInContext(source, context);
  await new Promise(resolve => setImmediate(resolve));
  return {context, product, inserted,
    view: () => JSON.parse(vm.runInContext('JSON.stringify(adminState.view)', context)),
    hash(hash, replaceCard = false) {if (replaceCard) workspace = null; location.hash = hash; listeners.get('hashchange')();},
    run: code => vm.runInContext(code, context)
  };
}

test('managed stage establishes its view before reusing an existing mount', async () => {
  const f = await fixture();
  f.run('adminState.view=null; mount();');
  assert.deepEqual(f.view(), {stage: 'dataset', type: null});
  assert.equal(f.inserted.length, 1);
});

test('dataset branch remains clickable after the hash-change handler runs', async () => {
  const f = await fixture();
  f.hash('#dataset');
  assert.doesNotThrow(() => f.product.onclick());
  assert.deepEqual(f.view(), {stage: 'dataset', type: 'product'});
  assert.match(f.inserted.at(-1), /Create new/);
});

test('branch selection recovers even if an earlier handler cleared view state', async () => {
  const f = await fixture();
  f.run('adminState.view=null;');
  f.product.onclick();
  assert.equal(f.view().type, 'product');
});

test('unknown branch types do not enter the stage renderer', async () => {
  const f = await fixture();
  f.run("selectManagedType('unknown_type')");
  assert.deepEqual(f.view(), {stage: 'dataset', type: null});
  assert.equal(f.inserted.length, 1);
});

test('creative stage exposes its own primitive branch after navigation', async () => {
  const f = await fixture();
  f.hash('#direction', true);
  f.run("selectManagedType('__primitives')");
  assert.deepEqual(f.view(), {stage: 'direction', type: '__primitives'});
  assert.match(f.inserted.at(-1), /Scene primitives/);
});

test('rerender preserves the selected branch until a navigation reset', async () => {
  const f = await fixture();
  f.product.onclick();
  f.run('rerender();');
  assert.equal(f.view().type, 'product');
  f.hash('#learn', true);
  assert.deepEqual(f.view(), {stage: 'learn', type: null});
  assert.match(f.inserted.at(-1), /Learning and improvement library/);
});

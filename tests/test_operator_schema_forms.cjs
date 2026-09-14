const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const schemas = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures/operator-payload-schemas.json'), 'utf8'));
const source = fs.readFileSync(path.join(__dirname, '../apps/operator/stage-admin.js'), 'utf8');
let sequence = 0;
const sandbox = {structuredClone, crypto: {randomUUID: () => String(++sequence)}};
vm.createContext(sandbox);
vm.runInContext(source.replace(/start\(\);\s*$/, '') + '\nglobalThis.forms = {adminState, resolveFieldSchema, initialPayload, control, inputValue, collectPayload, stableWriteKey, recordForm};', sandbox);
const f = sandbox.forms;
f.adminState.schema = {object_types: schemas};
const field = (type, name) => f.resolveFieldSchema(schemas[type].properties[name], schemas[type]);
const input = (name, value, kind = 'text', empty = 'omit') => ({name, value, dataset: {kind, empty}});
const plain = value => JSON.parse(JSON.stringify(value));

test('feedback choices come from the registered schema instead of free text', () => {
  for (const name of ['authority', 'system_area', 'classification']) {
    const definition = field('feedback', name);
    const markup = f.control(name, definition.default, definition, schemas.feedback.required.includes(name));
    assert.match(markup, /<select /);
    assert.doesNotMatch(markup, /<input /);
    for (const option of definition.enum) assert.ok(markup.includes('&quot;' + option + '&quot;'));
  }
});

test('creation uses schema defaults without copying another record', () => {
  f.adminState.objects = [{object_type: 'feedback', payload: {summary: 'Another person', authority: 'verified_evidence'}}];
  const values = f.initialPayload('feedback', null);
  assert.equal(values.authority, 'observation');
  assert.equal(values.system_area, 'governance');
  assert.equal(values.classification, undefined);
  assert.equal(values.summary, undefined);
});

test('editing preserves false, zero, null, timestamps and unknown existing fields', () => {
  const existing = {authority: 'operating_directive', extra_false: false, extra_zero: 0, extra_null: null, observed_at: '2026-09-14T08:00:00+02:00'};
  const values = f.initialPayload('feedback', {payload: existing});
  for (const [key, value] of Object.entries(existing)) assert.equal(values[key], value);
});

test('mutable schema defaults are cloned per form', () => {
  f.adminState.schema.object_types.fixture = {properties: {items: {type: 'array', default: []}}};
  const one = f.initialPayload('fixture', null);
  one.items.push('changed');
  assert.deepEqual(plain(f.initialPayload('fixture', null).items), []);
  delete f.adminState.schema.object_types.fixture;
});

test('local references and nullable unions retain canonical constraints', () => {
  const root = {$defs: {Permission: {type: 'boolean', description: 'Documented permission'}}};
  const resolved = f.resolveFieldSchema({title: 'Allowed', anyOf: [{$ref: '#/$defs/Permission'}, {type: 'null'}]}, root);
  assert.equal(resolved.type, 'boolean');
  assert.equal(resolved.nullable, true);
  assert.equal(resolved.title, 'Allowed');
  assert.equal(resolved.description, 'Documented permission');
  const markup = f.control('allowed', null, resolved);
  assert.match(markup, /value="null" selected/);
  assert.match(markup, /value="false"/);
  assert.match(markup, /Documented permission/);
});

test('nullable enum keeps an explicit unknown and serializes choices correctly', () => {
  const resolved = f.resolveFieldSchema({anyOf: [{type: 'string', enum: ['yes', 'no']}, {type: 'null'}]}, {});
  const markup = f.control('answer', null, resolved);
  assert.match(markup, /value="null" selected/);
  assert.match(markup, /value="&quot;yes&quot;"/);
  assert.equal(f.inputValue(input('answer', 'null', 'enum', 'null')), null);
});

test('constants cannot be edited into a new policy permission', () => {
  const markup = f.control('publication_allowed', false, {type: 'boolean', const: false}, true);
  assert.match(markup, /readonly/);
  assert.match(markup, /value="false"/);
  assert.equal(f.inputValue(input('publication_allowed', 'false', 'json')), false);
});

test('numeric controls preserve zero and expose integer bounds', () => {
  const markup = f.control('count', 0, {type: 'integer', minimum: 0, maximum: 90}, true);
  assert.match(markup, /type="number"/);
  assert.match(markup, /step="1"/);
  assert.match(markup, /value="0"/);
  assert.match(markup, /min="0" max="90"/);
  assert.equal(f.inputValue(input('count', '0', 'integer')), 0);
  for (const value of ['NaN', 'Infinity', '1.5']) assert.throws(() => f.inputValue(input('count', value, 'integer')), /valid integer/);
});

test('missing optional values are omitted, not invented as false or empty', () => {
  const inputs = [input('omitted', ''), input('unknown', '', 'number', 'null'), input('zero', '0', 'number'), input('negative', 'false', 'boolean'), input('empty_text', '', 'text', 'text')];
  const payload = f.collectPayload({querySelectorAll: () => inputs});
  assert.deepEqual(plain(payload), {unknown: null, zero: 0, negative: false, empty_text: ''});
  assert.throws(() => f.inputValue(input('required_choice', '', 'enum', 'error')), /Required Choice is required/);
});

test('JSON fields support arrays and fail with the field name', () => {
  assert.deepEqual(plain(f.inputValue(input('target_ids', '["object_1"]', 'json'))), ['object_1']);
  assert.throws(() => f.inputValue(input('target_ids', '[broken', 'json')), /Target Ids must contain valid JSON/);
  assert.equal(f.resolveFieldSchema({anyOf: [{type: 'string'}, {type: 'integer'}]}, {}).type, 'json');
});

test('text constraints and date-time offsets survive rendering without HTML injection', () => {
  const markup = f.control('observed_at', '2026-09-14T08:00:00+02:00', {type: 'string', format: 'date-time', minLength: 1, maxLength: 80, title: '<unsafe>'}, true);
  assert.match(markup, /2026-09-14T08:00:00\+02:00/);
  assert.match(markup, /minlength="1" maxlength="80"/);
  assert.match(markup, /&lt;unsafe&gt;/);
  assert.doesNotMatch(markup, /datetime-local|<unsafe>/);
});

test('same failed write reuses its key; changed payload or endpoint gets a new key', () => {
  const state = {};
  const key = f.stableWriteKey(state, '/v1/objects', {payload: {summary: 'First'}});
  assert.equal(f.stableWriteKey(state, '/v1/objects', {payload: {summary: 'First'}}), key);
  const edited = f.stableWriteKey(state, '/v1/objects', {payload: {summary: 'Revised'}});
  assert.notEqual(edited, key);
  assert.notEqual(f.stableWriteKey(state, '/v1/objects/id/curate', {payload: {summary: 'Revised'}}), edited);
});

test('form submission prevents a second in-flight write', async () => {
  let handler;
  let requests = 0;
  let finish;
  const submit = {disabled: false};
  const status = {textContent: ''};
  const form = {
    elements: {__title: {value: 'Directive'}, __purpose: {value: 'Retain direction'}, __reason: {value: 'UAT'}},
    querySelectorAll: () => [input('summary', 'One request')],
    querySelector: selector => selector === '.form-status' ? status : submit,
    set onsubmit(value) { handler = value; }
  };
  sandbox.document = {querySelector: () => null};
  sandbox.location = {reload() {}};
  sandbox.fetch = () => { requests += 1; return new Promise(resolve => {finish = () => resolve({ok: true, json: async () => ({})});}); };
  sandbox.testDialog = {querySelector: selector => selector === 'form' ? form : {innerHTML: ''}, showModal() {}};
  vm.runInContext('dialog = () => testDialog;', sandbox);
  f.recordForm('feedback');
  const event = {preventDefault() {}, currentTarget: form};
  const pending = handler(event);
  assert.equal(submit.disabled, true);
  await handler(event);
  assert.equal(requests, 1);
  finish();
  await pending;
  assert.equal(submit.disabled, false);
});

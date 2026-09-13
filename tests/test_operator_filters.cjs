const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../apps/operator/stage-admin.js'), 'utf8');
const css = fs.readFileSync(path.join(__dirname, '../apps/operator/operator-v1.css'), 'utf8');

function fixture(query = '', status = 'all') {
  const rows = [
    {dataset: {search: 'viture luma', status: 'active'}},
    {dataset: {search: 'xreal one', status: 'captured'}},
    {dataset: {search: 'xreal air', status: 'captured'}}
  ];
  const controls = {'#recordSearch': {value: query}, '#recordStatus': {value: status}, '#recordCount': {textContent: ''}, '#recordNoResults': {hidden: true}};
  const context = vm.createContext({
    document: {querySelector: selector => controls[selector] || null, querySelectorAll: selector => selector === '.managed-record' ? rows : []},
    fetch: () => new Promise(() => {})
  });
  vm.runInContext(source, context);
  vm.runInContext('filterRecords()', context);
  return {rows, controls};
}

test('search is case-insensitive and reports the visible count', () => {
  const {rows, controls} = fixture('VITURE');
  assert.deepEqual(rows.map(row => row.hidden), [false, true, true]);
  assert.equal(controls['#recordCount'].textContent, '1 of 3 records');
  assert.equal(controls['#recordNoResults'].hidden, true);
});

test('status and search filters are combined', () => {
  const {rows} = fixture('xreal', 'captured');
  assert.deepEqual(rows.map(row => row.hidden), [true, false, false]);
});

test('a no-match filter has an explicit empty state', () => {
  const {rows, controls} = fixture('not-present');
  assert.equal(rows.every(row => row.hidden), true);
  assert.equal(controls['#recordCount'].textContent, '0 of 3 records');
  assert.equal(controls['#recordNoResults'].hidden, false);
});

test('hidden records override the author-level grid display rule', () => {
  assert.match(css, /\.managed-record\[hidden\][^{]*\{[^}]*display:\s*none\s*!important/);
});

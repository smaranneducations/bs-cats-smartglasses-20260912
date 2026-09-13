const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../apps/web/app.js'), 'utf8');
const context = vm.createContext({
  document: {querySelector: () => ({}), addEventListener() {}},
  // These tests exercise evidence parsing, not the separate production UI adapter.
  window: {addEventListener() {}, WorkspaceProduction: {configure() {}}}, URL, FormData,
});
vm.runInContext(source.replace(/\nstart\(\);\s*$/, '') +
  '\nglobalThis.buildForTest = buildEvidenceFields;', context);
const fields = [{key:'weight_g',label:'Weight',value_type:'number',category:'all'}];
const original = {
  weight_g:{value:75.5,source_ids:['source_a','source_b'],evidence_kind:'independent_test',
    observed_at:'2026-09-01T10:30:00Z',conditions:'Fixture conditions',confidence:0},
};
function form() {
  const data = new FormData();
  data.set('category','display');
  data.set('weight_g','75.5');
  data.append('weight_g_source','source_a');
  data.append('weight_g_source','source_b');
  data.set('weight_g_kind','independent_test');
  data.set('weight_g_observed_at',original.weight_g.observed_at);
  data.set('weight_g_conditions','Fixture conditions');
  data.set('weight_g_confidence','0');
  return data;
}
function build(data, definitions=fields, previous=original, hasSource=false) {
  return JSON.parse(JSON.stringify(context.buildForTest(data,definitions,previous,'source_c',hasSource)));
}
test('unchanged fields preserve dates, zero confidence, evidence type and multiple sources',()=>{
  assert.deepEqual(build(form()),original);
});
test('adding a source does not silently claim a fresh observation',()=>{
  const data=form();data.append('weight_g_source','new');
  const result=build(data,fields,original,true);
  assert.deepEqual(result.weight_g.source_ids,['source_a','source_b','source_c']);
  assert.equal(result.weight_g.observed_at,original.weight_g.observed_at);
});
test('a changed value retains the original date unless a new date is entered',()=>{
  const data=form();data.set('weight_g','76.25');
  const result=build(data);
  assert.equal(result.weight_g.value,76.25);
  assert.equal(result.weight_g.observed_at,original.weight_g.observed_at);
});
test('unassessed confidence stays null rather than receiving a fabricated score',()=>{
  const data=form();data.set('weight_g_confidence','');
  assert.equal(build(data).weight_g.confidence,null);
});
test('unknown optional fields are not populated with fresh timestamps',()=>{
  const definitions=[...fields,{key:'fov_deg',label:'FOV',value_type:'number',category:'display'}];
  assert.deepEqual(Object.keys(build(form(),definitions)),['weight_g']);
});
test('a selected new source requires its URL',()=>{
  const data=form();data.append('weight_g_source','new');
  assert.throws(()=>build(data),/additional source URL/);
});
test('invalid observation dates and nonfinite values are rejected',()=>{
  const data=form();data.set('weight_g_observed_at','2026-09-01T10:30:00');
  assert.throws(()=>build(data),/timezone/);
  data.set('weight_g_observed_at',original.weight_g.observed_at);
  data.set('weight_g','Infinity');
  assert.throws(()=>build(data),/finite number/);
});
test('boolean false and numeric zero remain known values',()=>{
  const data=form();data.set('weight_g','0');
  data.set('recording_indicator','false');
  data.append('recording_indicator_source','source_a');
  data.set('recording_indicator_observed_at',original.weight_g.observed_at);
  const definitions=[...fields,{key:'recording_indicator',label:'Indicator',value_type:'boolean',category:'all'}];
  const result=build(data,definitions);
  assert.equal(result.weight_g.value,0);
  assert.equal(result.recording_indicator.value,false);
});

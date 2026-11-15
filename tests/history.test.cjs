const { test } = require('node:test');
const assert = require('node:assert/strict');
const history = require('../static/history.js');
function report(url='https://example.com/a') {
  return { url, title:'Sample', note:'note', excerpt:'text', score:50, bots:[], checks:[
    { id:'title', label:'タイトル', weight:10, passed:false, evidence:'なし', action:'追加' },
    { id:'schema', label:'構造化データ', weight:15, passed:true, evidence:'あり', action:'確認' }
  ] };
}
const entry = r => ({ at:'2026-11-15T00:00:00.000Z', report:r });
test('reads bounded history and ignores corrupt or partial records', () => {
  assert.deepEqual(history.read('not json'), []);
  assert.deepEqual(history.read('{}'), []);
  assert.deepEqual(history.read('[null, {"at":"bad"}]'), []);
  assert.equal(history.read(JSON.stringify(Array.from({length:20}, () => entry(report())))).length,10);
  const invalid=report(); invalid.checks[0].passed='false';
  assert.deepEqual(history.read(JSON.stringify([entry(invalid)])),[]);
  for (const url of ['https://', 'javascript:alert(1)', 'file:///etc/passwd']) {
    assert.equal(history.validReport(report(url)),false);
  }
});
test('compares the latest identical URL, ignores fragments, preserves query', () => {
  const rows=[entry(report('https://example.com/a?q=2')), entry(report('https://example.com/a?q=1#old'))];
  assert.equal(history.previous(rows,report('https://example.com/a?q=1#new')),rows[1]);
  assert.equal(history.previous(rows,report('https://example.com/b')),undefined);
});
test('reports improvements and regressions even with equal score', () => {
  const old=report(); const current=report();
  current.checks[0].passed=true; current.checks[1].passed=false;
  const diff=history.compare(current,entry(old));
  assert.equal(diff.delta,0);
  assert.deepEqual(diff.improved,['タイトル']);
  assert.deepEqual(diff.regressed,['構造化データ']);
});
test('handles score increase, score decrease, and unchanged results', () => {
  const old=report(); const current=report(); current.score=70;
  assert.equal(history.compare(current,entry(old)).delta,20);
  assert.equal(history.compare(old,entry(current)).delta,-20);
  assert.deepEqual(history.compare(old,entry(old)).improved,[]);
  assert.equal(history.compare(old,undefined),null);
});
test('does not compare different checks or scoring weights', () => {
  const old=report(); const current=report(); current.checks[0].weight=20;
  assert.deepEqual(history.compare(current,entry(old)), {compatible:false});
  current.checks.pop();
  assert.deepEqual(history.compare(current,entry(old)), {compatible:false});
});
test('matches checks by ID regardless of ordering', () => {
  const old=report(); const current=report(); current.checks.reverse();
  assert.equal(history.compare(current,entry(old)).compatible,true);
});
test('preserves legacy records but refuses comparison across analysis versions', () => {
  const old=report(); const current=report(); current.analysis_version='2';
  assert.equal(history.read(JSON.stringify([entry(old)])).length,1);
  assert.deepEqual(history.compare(current,entry(old)),{compatible:false});
  old.analysis_version='2';
  assert.equal(history.compare(current,entry(old)).compatible,true);
});
test('ignores corrupt structured-data details in saved records', () => {
  const r=report(); r.schema_details=[{block:1,passed:false,types:'bad',issues:[]}];
  assert.equal(history.read(JSON.stringify([entry(r)])).length,0);
});
test('backup round trip preserves complete records and legacy versions', () => {
  const rows=[entry(report())];
  const data=history.backup(rows);
  assert.equal(data.format,'aeo-check-history');
  assert.deepEqual(history.parseBackup(JSON.stringify(data)),rows);
});
test('rejects invalid backups as a whole without silently dropping records', () => {
  for (const value of ['broken','[]',JSON.stringify({format:'aeo-check-history',version:2,entries:[]}),JSON.stringify(history.backup([entry(report()),{at:'bad',report:report()}])),JSON.stringify(history.backup(Array.from({length:11},()=>entry(report()))))]) {
    assert.throws(()=>history.parseBackup(value));
  }
});
test('merges newest ten while retaining existing duplicate records', () => {
  const current=entry(report());
  const duplicate={...entry(report()),at:'2026-11-15T00:00:00+00:00'};
  duplicate.report.title='do not replace';
  assert.deepEqual(history.merge([current],[duplicate]),[current]);
  const rows=Array.from({length:10},(_,i)=>({at:`2026-11-${String(i+1).padStart(2,'0')}T00:00:00Z`,report:report()}));
  const merged=history.merge(rows,[current]);
  assert.equal(merged.length,10);
  assert.equal(merged[0],current);
  assert.equal(merged.at(-1).at,'2026-11-02T00:00:00Z');
});

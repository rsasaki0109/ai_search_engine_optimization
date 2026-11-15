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

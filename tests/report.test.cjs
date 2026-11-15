const { test } = require('node:test');
const assert = require('node:assert/strict');
const { markdown } = require('../static/report.js');
function report() { return { title:'Sample', url:'https://example.com/a', score:50, note:'技術診断です', excerpt:'PRIVATE EXCERPT', bots:[{name:'GPTBot',allowed:false,purpose:'学習用'}], checks:[
  {id:'schema',label:'構造化データ',passed:false,weight:15,evidence:'なし',action:'追加',repair:{location:'HTML / <head>',note:'内容を確認',code:'<script type="application/ld+json">{}</script>'}},
  {id:'title',label:'タイトル',passed:true,weight:10,evidence:'Sample',action:'確認'}
] }; }
const options = {at:'2026-11-15T01:00:00Z',generatedAt:'2026-11-16T01:00:00Z'};
test('exports complete audit, repairs, timestamps and bot purpose without excerpt', () => {
  const md=markdown(report(),options);
  for (const phrase of ['# AEO Check','50 / 100','2026\\-11\\-15T01:00:00Z','2026\\-11\\-16T01:00:00Z','優先度 高','```html','学習用','制限']) assert.ok(md.includes(phrase),phrase);
  assert.ok(!md.includes('PRIVATE EXCERPT'));
  assert.ok(!md.includes('## 前回との比較'));
});
test('includes comparison using original diagnosis, with both kinds of changes', () => {
  const old=report(); old.checks[0].passed=true; old.checks[1].passed=false;
  const md=markdown(report(),{...options,prior:{at:'2026-11-14T00:00:00Z',report:old}});
  assert.ok(md.includes('改善: タイトル'));
  assert.ok(md.includes('要対応に変化: 構造化データ'));
  assert.ok(md.includes('**0 点**'));
});
test('reports incompatible scoring without a misleading score delta', () => {
  const old=report(); old.checks[0].weight=5;
  const md=markdown(report(),{...options,prior:{at:'old',report:old}});
  assert.ok(md.includes('比較できません'));
  assert.ok(!md.includes('スコア差'));
});
test('escapes untrusted HTML, headings, table separators and links', () => {
  const r=report(); r.title='<img src=x> [click](https://evil.test)';
  r.checks[0].evidence='cell|bad\n# Heading';
  const md=markdown(r,options);
  assert.ok(md.includes('&lt;img src=x&gt;'));
  assert.ok(md.includes('\\[click\\]\\('));
  assert.ok(md.includes('cell\\|bad \\# Heading'));
  assert.ok(!md.includes('<img src=x>'));
});
test('uses a longer code fence when sample contains backticks', () => {
  const r=report();r.checks[0].repair.code='```\n# pretend heading\n````';
  const md=markdown(r,options);
  assert.ok(md.includes('`````html\n```\n# pretend heading\n````\n`````'));
});
test('handles passed audits and unknown robots without fake allow status', () => {
  const r=report();r.checks.forEach(c=>{c.passed=true;});r.bots=[];r.robots_error='robots取得失敗';
  const md=markdown(r,options);
  assert.ok(md.includes('すべて通過'));
  assert.ok(md.includes('robots取得失敗'));
  assert.ok(md.includes('アクセス設定は不明'));
  assert.ok(!md.includes('```html'));
});
test('exports structured-data findings and analysis version', () => {
  const r=report();r.analysis_version='2';
  r.schema_details=[{block:1,passed:false,types:['Article'],issues:['@contextを確認']}];
  const md=markdown(r,options);
  assert.ok(md.includes('判定基準バージョン: 2'));
  assert.ok(md.includes('## 構造化データの詳細'));
  assert.ok(md.includes('検出した型: Article'));
  assert.ok(md.includes('@contextを確認'));
});
test('exports crawler group and matched rule with line number', () => {
  const r=report();Object.assign(r.bots[0],{group:'*',matched_rule:'Disallow: /private/*$',matched_line:3,reason:'最長一致'});
  const md=markdown(r,options);
  assert.ok(md.includes('適用グループ'));
  assert.ok(md.includes('Disallow: /private/\\*$（3行目）'));
});

const {test}=require('node:test');
const assert=require('node:assert/strict');
const {validateHtml,origin}=require('../pages/file-input.js');
test('accepts saved HTML and supported snippets',()=>{
  for(const html of ['<!doctype html><html></html>','<h1>Title</h1>','\ufeff<html lang="ja"><p>本文</p></html>'])assert.doesNotThrow(()=>validateHtml('page.html','text/html',html));
});
test('rejects report JSON even when renamed or containing repair code',()=>{
  const report=JSON.stringify({title:'test',repair:'<script type="application/ld+json">{}</script>'});
  assert.throws(()=>validateHtml('report.json','application/json',report));
  assert.throws(()=>validateHtml('report.html','text/html',report));
});
test('rejects empty or plain-text files without changing input',()=>{
  for(const html of ['', 'not a page'])assert.throws(()=>validateHtml('page.html','text/html',html));
});
test('distinguishes origins while preserving same-site path edits',()=>{
  assert.equal(origin('https://example.com/a'),origin('https://example.com/b'));
  assert.notEqual(origin('https://example.com/a'),origin('https://other.test/a'));
  assert.equal(origin('bad'),null);
});

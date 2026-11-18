(function(root) {
  function validateHtml(name, type, html) {
    if (!/\.html?$/i.test(name) && type !== 'text/html') throw new Error('HTMLファイル（.html / .htm）を選択してください。診断JSONではなく、対象ページのHTMLを選び直してください。');
    const source=html.trimStart();
    if (/^[{\[]/.test(source) || !/<(?:!doctype\s+html|html|head|body|title|meta|main|article|h[1-6]|p|div|section|script)(?:\s|>)/i.test(source)) {
      throw new Error('HTMLとして読み取れませんでした。対象ページを「HTMLのみ」で保存し、選び直してください。');
    }
  }
  function origin(value) { try { return new URL(value).origin; } catch { return null; } }
  const api={validateHtml,origin};
  if (typeof module!=='undefined' && module.exports) module.exports=api;
  else root.AEOFileInput=api;
})(typeof window==='undefined'?globalThis:window);

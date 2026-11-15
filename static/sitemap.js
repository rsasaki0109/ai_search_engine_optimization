function refreshSitemapSelection() {
  const checked = document.querySelectorAll('#sitemap-candidates input:checked').length;
  document.querySelectorAll('#sitemap-candidates input').forEach(input => { input.disabled = busy || (!input.checked && checked >= 5); });
  $('sitemap-apply').disabled = busy || !checked || checked > 5;
  $('sitemap-apply').textContent = `選んだ${checked}件を一括診断欄へ`;
}
$('sitemap-form').addEventListener('submit', async event => {
  event.preventDefault();
  setBusy(true);
  $('sitemap-candidates').replaceChildren();
  $('sitemap-apply').hidden = true;
  $('sitemap-status').textContent = 'サイトマップを読み込んでいます…';
  try {
    const response = await fetch('/api/sitemap', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url:$('sitemap-url').value.trim()}), signal:AbortSignal.timeout(40000) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '読み込みに失敗しました。');
    $('sitemap-status').textContent = `${data.urls.length}件の${data.kind === 'index' ? '子サイトマップ' : 'ページ候補'}を表示。${data.skipped}件を形式不正・別ホストなどで除外。${data.truncated ? '上限100件まで表示しています。' : ''}`;
    data.urls.forEach(url => {
      if (data.kind === 'index') {
        const button = el('button', url, 'sitemap-child'); button.type = 'button';
        button.addEventListener('click', () => { $('sitemap-url').value = url; $('sitemap-form').requestSubmit(); });
        $('sitemap-candidates').append(button);
      } else {
        const label = el('label', '', 'sitemap-choice');
        const input = document.createElement('input'); input.type = 'checkbox'; input.value = url;
        input.addEventListener('change', refreshSitemapSelection);
        label.append(input, el('span', url)); $('sitemap-candidates').append(label);
      }
    });
    $('sitemap-apply').hidden = data.kind !== 'pages' || !data.urls.length;
  } catch (error) {
    $('sitemap-status').textContent = error.name === 'TimeoutError' ? '読み込みがタイムアウトしました。再試行してください。' : error.message;
  } finally { setBusy(false); }
});
$('sitemap-apply').addEventListener('click', () => {
  const selected = [...document.querySelectorAll('#sitemap-candidates input:checked')].map(input => input.value);
  if (busy || !selected.length || selected.length > 5) return;
  if ($('batch-form').hidden) $('batch-toggle').click();
  $('batch-urls').value = selected.join('\n');
  $('batch-status').textContent = `${selected.length}件を入力しました。「まとめて診断する」で開始できます。`;
  $('batch-urls').focus();
});

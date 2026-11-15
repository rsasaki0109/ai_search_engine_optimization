let batchReport;
$('batch-toggle').addEventListener('click', () => {
  const expanded = $('batch-form').hidden;
  $('batch-form').hidden = !expanded;
  $('audit-form').hidden = expanded;
  $('batch-toggle').setAttribute('aria-expanded', String(expanded));
  $('batch-toggle').textContent = expanded ? '1ページずつ診断に戻る ↗' : '複数ページをまとめて診断 ↗';
  if (expanded) $('batch-urls').focus();
});
$('batch-form').addEventListener('submit', async event => {
  event.preventDefault();
  const urls = [...new Set($('batch-urls').value.split(/\r?\n/).map(s => s.trim()).filter(Boolean))];
  $('batch-status').className = '';
  try {
    if (!urls.length || urls.length > 5) throw new Error('URLは1件から5件まで、1行に1件で入力してください。');
    urls.forEach(value => {
      let url;
      try { url = new URL(value); } catch { throw new Error(`URLの形式を確認してください：${value}`); }
      if (!['https:', 'http:'].includes(url.protocol)) throw new Error('http:// または https:// から始まるURLを入力してください。');
    });
  } catch (error) {
    $('batch-status').className = 'error';
    $('batch-status').textContent = error.message;
    return;
  }
  setBusy(true);
  batchReport = undefined;
  $('batch-results').hidden = true;
  $('results').hidden = true;
  $('batch-status').textContent = `${urls.length}件のURLを診断しています…（最大3件ずつ処理）`;
  try {
    const response = await fetch('/api/audit/batch', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ urls }), signal:AbortSignal.timeout(90000) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '一括診断に失敗しました。');
    batchReport = data;
    $('batch-list').replaceChildren();
    const priors = new Map();
    data.results.filter(row => row.report).sort((a,b) => Date.parse(a.at) - Date.parse(b.at)).forEach(row => {
      priors.set(row, rememberAudit(row.report, row.at));
    });
    data.results.forEach(row => {
      const card = el('article', '', 'batch-row');
      const content = el('div', '', 'batch-info');
      content.append(el('h3', row.report ? (row.report.title || 'タイトル未設定') : '取得できませんでした'), el('p', row.url));
      if (row.report) {
        const prior = priors.get(row);
        if (row.report.url !== row.url) content.append(el('p', `転送先：${row.report.url}`));
        const stats = el('div', '', 'batch-stats');
        stats.append(el('strong', `${row.report.score} / 100`), el('span', `要改善 ${row.report.checks.filter(c => !c.passed).length}項目`));
        const open = el('button', '詳細を見る', 'secondary'); open.type = 'button';
        open.addEventListener('click', () => { renderReport(row.report, history.includes(prior) ? prior : undefined, row.at); });
        stats.append(open); card.append(content, stats);
      } else {
        content.append(el('p', row.error, 'batch-error')); card.append(content);
      }
      $('batch-list').append(card);
    });
    const s = data.summary;
    $('batch-summary').textContent = `${s.total}件中 ${s.succeeded}件成功・${s.failed}件取得失敗${s.average_score === null ? '' : ` · 成功したページの平均 ${s.average_score} / 100`}`;
    $('batch-results').hidden = false;
    $('features').hidden = true;
    $('batch-status').textContent = '一括診断が完了しました。';
    $('batch-results').scrollIntoView({ behavior:'smooth', block:'start' });
  } catch (error) {
    $('batch-status').className = 'error';
    $('batch-status').textContent = error.name === 'TimeoutError' ? '一括診断がタイムアウトしました。件数を減らして再試行してください。' : error.message;
  } finally { setBusy(false); }
});
$('batch-download').addEventListener('click', () => {
  if (batchReport) downloadFile(JSON.stringify(batchReport,null,2),'application/json','aeo-batch-report.json');
});

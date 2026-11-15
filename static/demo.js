let demoReports;
let demoAt;
function showDemo(stage) {
  if (busy || !demoReports) return;
  const prior = stage === 'after' ? { at: demoAt, report: demoReports.before } : undefined;
  renderReport(demoReports[stage], prior, demoAt);
  $('batch-results').hidden = true;
  $('demo-before').setAttribute('aria-pressed', String(stage === 'before'));
  $('demo-after').setAttribute('aria-pressed', String(stage === 'after'));
  $('demo-source').href = `/demo/${stage}`;
  $('demo-stage').textContent = stage === 'before' ? '① 修正前：要改善の項目と修正例を確認し、「② 修正後と比較する」へ進んでください。' : '② 修正後：本文・見出し・メタ情報・構造化データを整えたサンプルです。前回比較欄で変化を確認できます。';
}
$('demo-start').addEventListener('click', async () => {
  if (busy) return;
  setBusy(true);
  $('demo-status').textContent = 'サンプルを診断しています…';
  try {
    const response = await fetch('/api/demo', { signal: AbortSignal.timeout(10000) });
    if (!response.ok) throw new Error('サンプルを読み込めませんでした。再試行してください。');
    demoReports = await response.json();
    demoAt = new Date().toISOString();
    setBusy(false);
    showDemo('before');
    $('demo-status').textContent = 'サンプルを表示しています。診断履歴は変更しません。';
  } catch (error) {
    $('demo-status').textContent = error.name === 'TimeoutError' ? '読み込みがタイムアウトしました。再試行してください。' : error.message;
  } finally { setBusy(false); }
});
$('demo-before').addEventListener('click', () => showDemo('before'));
$('demo-after').addEventListener('click', () => showDemo('after'));

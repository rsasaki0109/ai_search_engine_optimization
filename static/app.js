const $ = id => document.getElementById(id);
let report;
let reportAt;
let reportPrior;
function el(tag, text, cls) { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; }
function repairPanel(repair) {
  const panel = el('details', '', 'repair');
  panel.append(el('summary', '修正例と適用方法を見る'));
  const top = el('div', '', 'repair-top');
  top.append(el('span', repair.location));
  panel.append(top, el('p', repair.note, 'repair-note'));
  if (repair.code) {
    const code = el('code', repair.code);
    const pre = el('pre', ''); pre.append(code); panel.append(pre);
    const copy = el('button', 'コードをコピー', 'secondary');
    copy.type = 'button';
    copy.setAttribute('aria-label', `${repair.location}の修正例をコピー`);
    const status = el('span', '', 'copy-status');
    status.setAttribute('role', 'status');
    copy.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(repair.code);
        status.textContent = 'コピーしました';
      } catch {
        const range = document.createRange(); range.selectNodeContents(code);
        const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
        status.textContent = '自動コピーできませんでした。選択したコードを手動でコピーしてください。';
      }
    });
    const controls = el('div', '', 'copy-controls'); controls.append(copy, status); panel.append(controls);
  }
  return panel;
}
$('audit-form').addEventListener('submit', async event => {
  event.preventDefault();
  setBusy(true);
  $('status').className = '';
  $('status').textContent = 'ページとrobots.txtを確認しています…';
  $('results').hidden = true;
  $('batch-results').hidden = true;
  try {
    const response = await fetch('/api/audit', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: $('url').value.trim() }), signal: AbortSignal.timeout(40000) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '診断に失敗しました。');
    const at = new Date().toISOString();
    const prior = rememberAudit(data, at);
    renderReport(data, prior, at);
    $('status').textContent = '診断が完了しました。';
  } catch (error) {
    $('status').className = 'error';
    $('status').textContent = error.name === 'TimeoutError' ? '診断がタイムアウトしました。時間をおいて再試行してください。' : error.message;
  } finally { setBusy(false); }
});
function downloadFile(content, mime, filename) {
  const url = URL.createObjectURL(new Blob([content], { type: mime }));
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$('download').addEventListener('click', () => {
  if (report) downloadFile(JSON.stringify(report, null, 2), 'application/json', 'aeo-report.json');
});
$('download-markdown').addEventListener('click', () => {
  if (report) downloadFile(AEOReport.markdown(report, { at: reportAt, prior: reportPrior }), 'text/markdown;charset=utf-8', 'aeo-report.md');
});
$('print-report').addEventListener('click', () => { if (report) window.print(); });
let printDetails = [];
window.addEventListener('beforeprint', () => {
  printDetails = [...document.querySelectorAll('#results .repair')].filter(detail => !detail.open);
  printDetails.forEach(detail => { detail.open = true; });
});
window.addEventListener('afterprint', () => {
  printDetails.forEach(detail => { detail.open = false; });
  printDetails = [];
});

function renderReport(data, prior, at) {
  report = data;
  reportAt = at;
  reportPrior = prior;
  document.body.classList.add('has-report');
  $('report-date').textContent = `診断日時：${new Date(at).toLocaleString('ja-JP')} · AEO Check 診断レポート`;
  $('page-title').textContent = data.title || 'タイトル未設定';
  $('page-url').textContent = data.url;
  $('score').textContent = data.score;
  $('disclaimer').textContent = data.note;
  $('check-count').textContent = `${data.checks.filter(c => c.passed).length} / ${data.checks.length} 項目を通過`;
  $('recommendations').replaceChildren();
  const failed = data.checks.filter(c => !c.passed).sort((a,b) => b.weight - a.weight);
  if (!failed.length) $('recommendations').append(el('p', '今回の技術チェックはすべて通過しました。次は情報の正確さ、独自性、出典を確認しましょう。', 'notice'));
  failed.forEach((c,i) => {
    const row = el('article', '', 'recommendation');
    row.append(el('span', `${String(i+1).padStart(2,'0')} · ${c.weight >= 15 ? '優先度 高' : '優先度 中'}`, 'priority'));
    const body = el('div', '', 'recommendation-body'); body.append(el('h3', c.label), el('p', c.action));
    if (c.repair) body.append(repairPanel(c.repair));
    row.append(body); $('recommendations').append(row);
  });
  $('checks').replaceChildren();
  data.checks.forEach(c => {
    const card = el('article', '', `check ${c.passed ? '' : 'fail'}`);
    card.append(el('span', c.passed ? '✓ 確認済み' : '要確認', 'state'), el('h3', c.label), el('p', c.evidence)); $('checks').append(card);
  });
  renderSchemaDetails(data);
  $('bots').replaceChildren();
  data.bots.forEach(bot => {
    const card = el('article', '', 'bot');
    card.append(el('b', bot.name), el('span', bot.allowed ? '✓ ルール上は許可' : '× ルール上は制限'), el('small', bot.purpose));
    if (bot.reason) {
      card.append(el('p', `適用グループ：${bot.group}`, 'bot-group'));
      if (bot.matched_rule) card.append(el('code', `${bot.matched_rule}（${bot.matched_line}行目）`, 'bot-rule'));
      card.append(el('p', bot.reason, 'bot-reason'));
    }
    $('bots').append(card);
  });
  $('robots-note').hidden = !data.robots_error;
  $('robots-note').textContent = data.robots_error || '';
  $('excerpt').textContent = data.excerpt || '本文テキストなし';
  $('results').hidden = false;
  $('features').hidden = true;
  renderComparison(data, prior);
  $('results').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

let history = [];
let busy = false;
let storageNote = '';
try { history = AEOHistory.read(localStorage.getItem(AEOHistory.KEY)); }
catch { storageNote = 'ブラウザの保存を利用できません。履歴はこのタブを開いている間だけ保持します。'; }
function saveHistory() {
  try {
    localStorage.setItem(AEOHistory.KEY, JSON.stringify(history));
    storageNote = '';
  } catch {
    storageNote = '履歴を保存できませんでした。今回の履歴はこのタブ内だけに保持します。';
  }
}
function setBusy(value) {
  busy = value;
  $('submit').disabled = value;
  $('clear-history').disabled = value || !history.length;
  document.querySelectorAll('#history-list button, #batch-form button, #batch-toggle, #batch-results button, #sitemap-form button, #sitemap-candidates button, #sitemap-apply').forEach(button => { button.disabled = value; });
  if (typeof refreshSitemapSelection === 'function') refreshSitemapSelection();
}
function renderComparison(data, prior) {
  const container = $('comparison'); container.replaceChildren();
  const diff = AEOHistory.compare(data, prior);
  container.hidden = !diff;
  if (!diff) return;
  container.append(el('h2', '前回との比較'), el('p', `${new Date(prior.at).toLocaleString('ja-JP')} の診断から`, 'hint'));
  if (!diff.compatible) {
    container.append(el('p', '判定基準・診断項目・配点のいずれかが異なるため、スコアを比較できません。'));
    return;
  }
  container.append(el('strong', `${diff.delta > 0 ? '+' : ''}${diff.delta} 点`, diff.delta < 0 ? 'score-delta negative' : 'score-delta'));
  if (diff.improved.length) container.append(el('p', `改善：${diff.improved.join('、')}`));
  if (diff.regressed.length) container.append(el('p', `要対応に変化：${diff.regressed.join('、')}`));
  if (!diff.improved.length && !diff.regressed.length) container.append(el('p', '技術チェックの通過状況に変化はありません。'));
  container.append(el('p', '同じ取得後URLの直前の保存結果と比較しています。AI検索での評価の変化を示すものではありません。', 'hint'));
}
function renderHistory() {
  $('history').hidden = !history.length && !storageNote;
  $('history-status').textContent = storageNote;
  $('clear-history').disabled = busy || !history.length;
  $('history-list').replaceChildren();
  history.forEach((entry, index) => {
    const row = el('article', '', 'history-row');
    const content = el('div', '', 'history-info');
    content.append(el('h3', entry.report.title || 'タイトル未設定'), el('p', entry.report.url), el('small', `${new Date(entry.at).toLocaleString('ja-JP')} · ${entry.report.score} / 100`));
    const actions = el('div', '', 'history-actions');
    const open = el('button', '結果を見る', 'secondary'); open.type = 'button'; open.disabled = busy;
    open.addEventListener('click', () => {
      $('url').value = entry.report.url;
      renderReport(entry.report, AEOHistory.previous(history.slice(index + 1), entry.report), entry.at);
      $('status').textContent = `${new Date(entry.at).toLocaleString('ja-JP')} の保存結果を表示しています。再診断ではありません。`;
      $('status').className = '';
    });
    const retry = el('button', '再診断', 'secondary'); retry.type = 'button'; retry.disabled = busy;
    retry.addEventListener('click', () => { $('url').value = entry.report.url; $('audit-form').requestSubmit(); });
    actions.append(open, retry); row.append(content, actions); $('history-list').append(row);
  });
}
$('clear-history').addEventListener('click', () => {
  try {
    localStorage.removeItem(AEOHistory.KEY);
    storageNote = '';
  } catch {
    storageNote = 'このタブの履歴を削除しました。保存領域へのアクセスが拒否されたため、ブラウザのサイトデータも確認してください。';
  }
  history = [];
  $('comparison').hidden = true;
  reportPrior = undefined;
  renderHistory();
  $('status').textContent = storageNote || '診断履歴を削除しました。';
});
renderHistory();

function renderSchemaDetails(data) {
  const list = $('schema-details'); list.replaceChildren();
  $('schema-section').hidden = !Array.isArray(data.schema_details);
  if (!Array.isArray(data.schema_details)) return;
  if (!data.schema_details.length) {
    list.append(el('p', 'JSON-LDを検出できませんでした。HTMLに含まれる構造化データだけを対象にしています。', 'notice'));
  }
  data.schema_details.forEach(item => {
    const card = el('article', '', 'schema-card');
    card.append(el('h3', `JSON-LD #${item.block} · ${item.passed ? '基本確認を通過' : '要確認'}`));
    card.append(el('p', `検出した型：${item.types.join('、') || 'なし'}`));
    if (item.issues.length) {
      const issues = el('ul', ''); item.issues.forEach(issue => issues.append(el('li', issue))); card.append(issues);
    }
    list.append(card);
  });
}

function rememberAudit(data, at) {
  const prior = AEOHistory.previous(history, data);
  history = [{ at, report: data }, ...history].sort((a,b) => Date.parse(b.at) - Date.parse(a.at)).slice(0, AEOHistory.LIMIT);
  saveHistory();
  renderHistory();
  return prior;
}

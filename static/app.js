const $ = id => document.getElementById(id);
let report;
function el(tag, text, cls) { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; }
$('audit-form').addEventListener('submit', async event => {
  event.preventDefault();
  $('submit').disabled = true;
  $('status').className = '';
  $('status').textContent = 'ページとrobots.txtを確認しています…';
  $('results').hidden = true;
  try {
    const response = await fetch('/api/audit', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: $('url').value.trim() }), signal: AbortSignal.timeout(40000) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '診断に失敗しました。');
    report = data;
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
      const body = el('div', ''); body.append(el('h3', c.label), el('p', c.action)); row.append(body); $('recommendations').append(row);
    });
    $('checks').replaceChildren();
    data.checks.forEach(c => {
      const card = el('article', '', `check ${c.passed ? '' : 'fail'}`);
      card.append(el('span', c.passed ? '✓ 確認済み' : '要確認', 'state'), el('h3', c.label), el('p', c.evidence)); $('checks').append(card);
    });
    $('bots').replaceChildren();
    data.bots.forEach(bot => { const card = el('article', '', 'bot'); card.append(el('b', bot.name), el('span', bot.allowed ? '✓ ルール上は許可' : '× ルール上は制限'), el('small', bot.purpose)); $('bots').append(card); });
    $('robots-note').hidden = !data.robots_error;
    $('robots-note').textContent = data.robots_error || '';
    $('excerpt').textContent = data.excerpt || '本文テキストなし';
    $('results').hidden = false;
    $('features').hidden = true;
    $('status').textContent = '診断が完了しました。';
    $('results').scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    $('status').className = 'error';
    $('status').textContent = error.name === 'TimeoutError' ? '診断がタイムアウトしました。時間をおいて再試行してください。' : error.message;
  } finally { $('submit').disabled = false; }
});
$('download').addEventListener('click', () => {
  if (!report) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }));
  const a = document.createElement('a'); a.href = url; a.download = 'aeo-report.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});

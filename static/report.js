/* Portable text export. Page-provided values are data, never Markdown markup. */
(function (root) {
  const history = typeof module !== 'undefined' && module.exports ? require('./history.js') : root.AEOHistory;
  function text(value) {
    return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/[\\`*_{}\[\]()#+.!|~-]/g, '\\$&').replace(/[\r\n]+/g, ' ');
  }
  function fence(code) {
    const runs = String(code).match(/`+/g) || [];
    const delimiter = '`'.repeat(Math.max(3, ...runs.map(s => s.length + 1)));
    return `${delimiter}html\n${code}\n${delimiter}`;
  }
  function markdown(report, { at, prior, generatedAt = new Date().toISOString() } = {}) {
    const lines = ['# AEO Check 診断レポート', '', `**${text(report.title || 'タイトル未設定')}**`, '',
      `- URL: ${text(report.url)}`, `- 診断日時: ${text(at || '不明')}`, `- レポート出力日時: ${text(generatedAt)}`,
      `- 技術チェックスコア: **${report.score} / 100**`, `- 判定基準バージョン: ${text(report.analysis_version || '1')}`, '', text(report.note), ''];
    if (report.source_mode==='html-file') {
      lines.push('## 診断に使用したファイル', '', '保存HTMLのみの診断です。HTTPヘッダー・実際の取得可否は未確認です。', '');
      for (const [label,file] of [['HTML',report.source_files?.html],['robots.txt',report.source_files?.robots]]) {
        if (file) lines.push(`- ${label}: ${text(file.name)} / ${file.size} bytes / SHA256: ${text(file.sha256)}`);
        else lines.push(`- ${label}: ${label==='HTML' ? 'ファイル情報なし（以前の履歴）' : '未提供・判定不明'}`);
      }
      lines.push('');
    }
    const diff = history.compare(report, prior);
    if (diff) {
      lines.push('## 前回との比較', '', `比較対象: ${text(prior.at)}`, '');
      if (!diff.compatible) lines.push('判定基準・診断項目・配点のいずれかが異なるため、比較できません。', '');
      else {
        lines.push(`スコア差: **${diff.delta > 0 ? '+' : ''}${diff.delta} 点**`, '');
        if (diff.improved.length) lines.push(`- 改善: ${diff.improved.map(text).join('、')}`);
        if (diff.regressed.length) lines.push(`- 要対応に変化: ${diff.regressed.map(text).join('、')}`);
        if (!diff.improved.length && !diff.regressed.length) lines.push('技術チェックの通過状況に変化はありません。');
        lines.push('', '同じ取得後URLの直前の保存結果との比較です。AI検索の評価の変化を示すものではありません。', '');
      }
    }
    lines.push('## 優先して取り組む改善', '');
    const failed = report.checks.filter(c => !c.passed).sort((a,b) => b.weight - a.weight);
    if (!failed.length) lines.push('今回の技術チェックはすべて通過しました。', '');
    failed.forEach((c,i) => {
      lines.push(`### ${i + 1}. ${text(c.label)}（優先度 ${c.weight >= 15 ? '高' : '中'}）`, '', text(c.action), '', `検出内容: ${text(c.evidence)}`, '');
      if (c.repair) {
        lines.push(`適用場所: ${text(c.repair.location)}`, '', text(c.repair.note), '');
        if (c.repair.code) lines.push(fence(c.repair.code), '');
      }
    });
    lines.push('## 技術チェック', '', '| 項目 | 結果 | 検出内容 |', '| --- | --- | --- |');
    report.checks.forEach(c => lines.push(`| ${text(c.label)} | ${c.passed ? '通過' : '要確認'} | ${text(c.evidence)} |`));
    if (Array.isArray(report.schema_details)) {
      lines.push('', '## 構造化データの詳細', '', 'JSON-LDの基本確認です。型の実在・必須項目・リッチリザルト適合は未検証です。外部contextは展開しません。', '');
      if (!report.schema_details.length) lines.push('JSON-LDを検出できませんでした。', '');
      report.schema_details.forEach(item => {
        lines.push(`### JSON-LD #${item.block} · ${item.passed ? '基本確認を通過' : '要確認'}`, '', `検出した型: ${item.types.map(text).join('、') || 'なし'}`, '');
        item.issues.forEach(issue => lines.push(`- ${text(issue)}`));
        lines.push('');
      });
    }
    lines.push('', '## クローラーのアクセス設定' , '', 'robots.txtによる指定URLへのアクセス設定です。実際の取得成功や引用を保証しません。GPTBotは学習用で、スコアには含めません。', '');
    if (report.robots_error) lines.push(text(report.robots_error), '');
    if (report.bots.length) {
      lines.push('| ボット | ルール上の判定 | 用途 | 適用グループ | 一致ルール |', '| --- | --- | --- | --- | --- |');
      report.bots.forEach(b => lines.push(`| ${text(b.name)} | ${b.allowed ? '許可' : '制限'} | ${text(b.purpose)} | ${text(b.group ?? '記録なし')} | ${text(b.matched_rule ? `${b.matched_rule}（${b.matched_line}行目）` : (b.reason || '記録なし'))} |`));
    } else lines.push('アクセス設定は不明です。');
    lines.push('', '---', '', 'AEO Check · 公開HTMLに基づく技術診断。本文の抜粋・他のURLの履歴はこのレポートに含みません。', '');
    return lines.join('\n');
  }
  const api = { markdown };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AEOReport = api;
})(typeof window === 'undefined' ? globalThis : window);

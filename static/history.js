/* Browser-local audit records; pure helpers are also tested with node:test. */
(function (root) {
  const KEY = 'aeo-check.history.v1';
  const LIMIT = 10;
  function urlKey(value) {
    const url = new URL(value); url.hash = ''; return url.href;
  }
  function validReport(r) {
    try {
      const url = new URL(r.url);
      if (!['http:', 'https:'].includes(url.protocol) || !url.hostname) return false;
    } catch { return false; }
    return r && typeof r.url === 'string' && /^https?:\/\//.test(r.url) &&
      (r.analysis_version === undefined || typeof r.analysis_version === 'string') &&
      (r.schema_details === undefined || (Array.isArray(r.schema_details) && r.schema_details.every(item =>
        item && Number.isInteger(item.block) && typeof item.passed === 'boolean' &&
        Array.isArray(item.types) && item.types.every(t => typeof t === 'string') &&
        Array.isArray(item.issues) && item.issues.every(issue => typeof issue === 'string')))) &&
      Number.isFinite(r.score) && r.score >= 0 && r.score <= 100 &&
      ['title', 'note', 'excerpt'].every(k => typeof r[k] === 'string') &&
      Array.isArray(r.checks) && r.checks.length > 0 && r.checks.every(c =>
        c && ['id','label','evidence','action'].every(k => typeof c[k] === 'string') &&
        typeof c.passed === 'boolean' && Number.isFinite(c.weight) &&
        (!c.repair || (typeof c.repair.location === 'string' && typeof c.repair.note === 'string' && (c.repair.code === null || typeof c.repair.code === 'string')))) &&
      Array.isArray(r.bots) && r.bots.every(b => b && typeof b.name === 'string' && typeof b.allowed === 'boolean' && typeof b.purpose === 'string' &&
        (b.reason === undefined || (typeof b.reason === 'string' && typeof b.group === 'string' &&
          (b.matched_rule === null || typeof b.matched_rule === 'string') && (b.matched_line === null || Number.isInteger(b.matched_line)))));
  }
  function read(raw) {
    try {
      const rows = JSON.parse(raw || '[]');
      if (!Array.isArray(rows)) return [];
      return rows.filter(row => row && typeof row.at === 'string' && Number.isFinite(Date.parse(row.at)) && validReport(row.report)).slice(0, LIMIT);
    } catch { return []; }
  }
  function previous(rows, report) {
    return rows.find(row => urlKey(row.report.url) === urlKey(report.url));
  }
  function backup(rows) {
    return { format: 'aeo-check-history', version: 1, exported_at: new Date().toISOString(), entries: rows };
  }
  function parseBackup(raw) {
    let data;
    try { data = JSON.parse(raw); } catch { throw new Error('JSONファイルを解析できませんでした。'); }
    if (!data || data.format !== 'aeo-check-history' || data.version !== 1 || !Array.isArray(data.entries) || data.entries.length > LIMIT) {
      throw new Error('AEO Checkの履歴バックアップ（形式バージョン1、最大10件）を選択してください。');
    }
    const rows = read(JSON.stringify(data.entries));
    if (rows.length !== data.entries.length) throw new Error('日時や診断データが不正なため、履歴を読み込めませんでした。');
    return rows;
  }
  function merge(current, incoming) {
    const seen = new Set();
    return [...current, ...incoming].filter(row => {
      const key = JSON.stringify([new Date(row.at).toISOString(), urlKey(row.report.url)]);
      if (seen.has(key)) return false;
      seen.add(key); return true;
    }).sort((a,b) => Date.parse(b.at) - Date.parse(a.at)).slice(0, LIMIT);
  }
  function compare(current, prior) {
    if (!prior) return null;
    const old = prior.report;
    const signature = r => r.checks.map(c => `${c.id}:${c.weight}`).sort().join('|');
    if ((current.analysis_version || '1') !== (old.analysis_version || '1') || signature(current) !== signature(old)) return { compatible: false };
    const byId = new Map(old.checks.map(c => [c.id, c]));
    return { compatible: true, delta: current.score - old.score,
      improved: current.checks.filter(c => c.passed && !byId.get(c.id).passed).map(c => c.label),
      regressed: current.checks.filter(c => !c.passed && byId.get(c.id).passed).map(c => c.label) };
  }
  const api = { KEY, LIMIT, read, validReport, previous, compare, backup, parseBackup, merge };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AEOHistory = api;
})(typeof window === 'undefined' ? globalThis : window);

let runtime;
async function initialize() {
  importScripts('https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js');
  const py = await loadPyodide({indexURL:'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/'});
  for (const file of ['robots.py','analysis.py']) {
    const response=await fetch(`./${file}`);
    if (!response.ok) throw new Error('解析プログラムを読み込めませんでした。');
    py.FS.writeFile(file,await response.text());
  }
  await py.runPythonAsync('from analysis import analyze, validate_url\nimport json');
  return py;
}
self.onmessage=async ({data}) => {
  try {
    runtime ||= initialize().catch(error=>{runtime=undefined;throw error;});
    const py=await runtime;
    py.globals.set('input_json',JSON.stringify(data));
    const output=await py.runPythonAsync(`payload=json.loads(input_json)
validate_url(payload['url'])
result=analyze({'url':payload['url'],'body':payload['html'],'robots_header':''}, payload.get('robots'), 'robots.txtは未提供のため不明です。' if payload.get('robots') is None else None)
result['source_mode']='html-file'
result['analysis_version']+='-html-file'
result['note']='保存HTMLを端末内で診断しています。URLからの取得・HTTPヘッダー・実際のアクセス可否は未確認です。'+result['note']
for check in result['checks']:
 if check['id']=='index': check['evidence']+='（HTML内のみ。HTTPヘッダー未確認）'
json.dumps(result,ensure_ascii=False)`);
    self.postMessage({result:JSON.parse(output)});
  } catch(error) { self.postMessage({error:String(error.message || error)}); }
};

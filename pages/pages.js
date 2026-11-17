// Adapt local demo requests without adding a hosted API or transmitting HTML.
const pagesFetch=window.fetch.bind(window);
window.fetch=(input,options)=> {
  if (typeof input==='string' && input==='/api/demo') return pagesFetch('./demo.json',options);
  if (typeof input==='string' && input.startsWith('/api/')) return Promise.resolve(new Response(JSON.stringify({error:'GitHub Pages版は保存HTMLを診断します。HTMLファイルを選択してください。'}),{status:400,headers:{'Content-Type':'application/json'}}));
  return pagesFetch(input,options);
};
let analysisWorker;
function analyzeFile(data) {
  analysisWorker ||= new Worker(new URL('./analysis-worker.js',document.baseURI));
  return new Promise((resolve,reject)=> {
    const timer=setTimeout(()=>{analysisWorker.terminate();analysisWorker=undefined;reject(new Error('初回準備または解析がタイムアウトしました。通信環境を確認して再試行してください。'));},120000);
    analysisWorker.onmessage=({data})=>{clearTimeout(timer);if(data.error)reject(new Error(data.error));else resolve(data.result);};
    analysisWorker.onerror=()=>{clearTimeout(timer);analysisWorker.terminate();analysisWorker=undefined;reject(new Error('解析環境を読み込めませんでした。CDNへの通信を確認してください。'));};
    analysisWorker.postMessage(data);
  });
}
$('pages-form').addEventListener('submit',async event=> {
  event.preventDefault();if(busy)return;
  const html=$('pages-html').files[0],robots=$('pages-robots').files[0];
  if(!html)return;
  setBusy(true);$('pages-submit').disabled=true;
  $('pages-status').textContent='端末内の解析環境を準備しています…初回は時間がかかります。';
  try {
    if(html.size>2000000)throw new Error('HTMLの上限（2MB）を超えています。');
    if(robots && robots.size>512000)throw new Error('robots.txtの上限（500KiB）を超えています。');
    const report=await analyzeFile({url:$('pages-url').value.trim(),html:await html.text(),robots:robots?await robots.text():null});
    const at=new Date().toISOString();const prior=rememberAudit(report,at);
    renderReport(report,prior,at);$('pages-status').textContent='端末内の診断が完了しました。ファイルは送信していません。';
  } catch(error){$('pages-status').textContent=error.message;}
  finally{setBusy(false);$('pages-submit').disabled=false;}
});

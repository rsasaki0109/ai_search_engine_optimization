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
let robotsOrigin=null;
function syncRobotsOrigin() {
  const current=AEOFileInput.origin($('pages-url').value);
  if ($('pages-robots').files.length && current !== robotsOrigin) {
    $('pages-robots').value='';
    $('pages-input-note').textContent='サイトが変わったため、前のrobots.txtを解除しました。必要ならこのサイトのファイルを選び直してください。';
    robotsOrigin=null;
  }
}
$('pages-url').addEventListener('input',syncRobotsOrigin);
$('pages-robots').addEventListener('change',()=>{
  robotsOrigin=AEOFileInput.origin($('pages-url').value);
  $('pages-input-note').textContent='';
});
async function fileIdentity(file) {
  const digest=await crypto.subtle.digest('SHA-256',await file.arrayBuffer());
  return {name:file.name,size:file.size,sha256:[...new Uint8Array(digest)].map(b=>b.toString(16).padStart(2,'0')).join('')};
}
$('pages-form').addEventListener('submit',async event=> {
  event.preventDefault();if(busy)return;
  syncRobotsOrigin();
  const html=$('pages-html').files[0],robots=$('pages-robots').files[0];
  if(!html)return;
  setBusy(true);$('pages-submit').disabled=true;
  $('pages-status').textContent='端末内の解析環境を準備しています…初回は時間がかかります。';
  try {
    if(html.size>2000000)throw new Error('HTMLの上限（2MB）を超えています。');
    if(robots && robots.size>512000)throw new Error('robots.txtの上限（500KiB）を超えています。');
    const body=await html.text();
    AEOFileInput.validateHtml(html.name,html.type,body);
    const report=await analyzeFile({url:$('pages-url').value.trim(),html:body,robots:robots?await robots.text():null});
    report.source_files={html:await fileIdentity(html),robots:robots?await fileIdentity(robots):null};
    const at=new Date().toISOString();const prior=rememberAudit(report,at);
    renderReport(report,prior,at);$('pages-status').textContent='端末内の診断が完了しました。ファイルは送信していません。';
  } catch(error){$('pages-status').textContent=error.message;}
  finally{setBusy(false);$('pages-submit').disabled=false;}
});

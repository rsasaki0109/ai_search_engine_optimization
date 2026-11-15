"""Render README demo: pip install playwright pillow; Chromium required.
Uses the real UI and analyzer with an explicitly labeled HTML fixture.
Run from repository root: python3 tools/create_hero.py
"""
import io
import json
from pathlib import Path
import sys
import threading
from http.server import ThreadingHTTPServer

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import Handler, analyze

SAMPLE = '''<html lang="ja"><head><title>AI検索に伝わるコンテンツの作り方</title>
<meta name="description" content="AI検索に向けたコンテンツ設計の基本を解説します。">
</head><body><h1>AI検索に伝わるコンテンツの作り方</h1><h2>まず、読者の問いに答える</h2>
<p>ページの冒頭で結論を述べ、見出しごとに具体的な根拠と説明を示しましょう。</p>
<p>''' + '情報の出典と更新日を示し、読者が確かめられる具体的な説明を心がけましょう。' * 8 + '</p></body></html>'
REPORT = analyze(dict(body=SAMPLE, url='https://example.com/guide', robots_header=''),
    'User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nDisallow: /')

STAGE = '''<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0;background:#102c25;color:#f4f8ee;font-family:Arial,'Noto Sans CJK JP',sans-serif;width:1280px;height:940px;overflow:hidden}
body:before{content:'';position:absolute;width:650px;height:650px;right:-200px;top:-250px;background:radial-gradient(circle,#6cba7530,transparent 70%)}
.top{position:relative;padding:38px 64px 25px;display:flex;align-items:end;justify-content:space-between}.tag{font-size:12px;letter-spacing:3px;color:#9cc6a5;margin-bottom:12px}.title{font-size:36px;font-weight:700;letter-spacing:-1px}.right{font-size:12px;color:#a6c4b3;line-height:1.9;text-align:right}.pill{border:1px solid #50715f;border-radius:30px;padding:7px 12px;color:#c8e6c9;font-size:11px;display:inline-block;margin-top:8px}
.browser{margin:0 48px;background:#f6f8f3;border-radius:12px;overflow:hidden;box-shadow:0 26px 65px #0005;border:1px solid #6f947659}.bar{height:43px;background:#e7ede4;display:flex;align-items:center;gap:7px;padding:0 18px}.dot{height:8px;width:8px;background:#9fb1a1;border-radius:50%}.address{margin-left:18px;background:#f6f8f3;border-radius:5px;padding:6px 18px;color:#66806e;font-size:10px;width:74%;letter-spacing:.4px}.demo{font-size:10px;color:#58745f;letter-spacing:1px;margin-left:auto}iframe{width:1182px;height:690px;border:0;display:block}.bottom{margin:25px 64px;display:flex;justify-content:space-between;color:#97b6a4;font-size:11px;letter-spacing:1px}.steps{display:flex;gap:25px}.step{color:#719380}.active{color:#ddf3c0}.mark{color:#d7edc3}
</style></head><body><div class="top"><div><div class="tag">AEO CHECK / AI SEARCH READINESS</div><div class="title">AI検索への準備を、見える化。</div></div><div class="right">URLひとつで、次の改善がわかる。<br><span class="pill">APIキー不要 &nbsp; / &nbsp; Pythonだけで起動</span></div></div>
<div class="browser"><div class="bar"><i class="dot"></i><i class="dot"></i><i class="dot"></i><div class="address">◈ &nbsp; AEO Check / localhost</div><span class="demo">SAMPLE DEMO</span></div><iframe src="APP_URL"></iframe></div>
<div class="bottom"><div class="steps"><span class="step active" id="s1">01 URLを入力</span><span class="step" id="s2">02 技術設定を診断</span><span class="step" id="s3">03 改善案を確認</span></div><span>サンプルHTMLによるデモ · AI検索での引用率は測定しません</span></div></body></html>'''


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    frames, durations = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
            page = browser.new_page(viewport={'width':1280, 'height':940}, device_scale_factor=1)
            page.route('https://fonts.googleapis.com/**', lambda route: route.abort())
            def respond(route):
                page.wait_for_timeout(700)
                route.fulfill(status=200, content_type='application/json', body=json.dumps(REPORT))
            page.route('**/api/audit', respond)
            page.set_content(STAGE.replace('APP_URL', f'http://127.0.0.1:{server.server_port}'))
            ui = page.frames[1]
            ui.wait_for_selector('#url')
            ui.add_style_tag(content='header{height:72px}.intro{padding:30px 0 25px}h1{font-size:46px;line-height:1.35}.lead{margin-bottom:22px}form{padding:20px}.eyebrow{margin-bottom:15px}.features{padding-top:24px}.features h2{margin-top:8px}*{scroll-behavior:auto!important}')
            def snap(ms=250):
                image = Image.open(io.BytesIO(page.screenshot())).convert('RGB').resize((1080,793), Image.Resampling.LANCZOS)
                frames.append(image)
                durations.append(ms)
            def step(n):
                page.evaluate('(n)=>document.querySelectorAll(".step").forEach((e,i)=>e.classList.toggle("active",i===n-1))', n)
            snap(1400)
            target = ui.locator('#url')
            target.focus()
            for chunk in ['https://', 'example.', 'com/', 'guide']:
                target.press_sequentially(chunk, delay=30)
                snap(170)
            snap(600)
            step(2)
            ui.locator('#submit').click(no_wait_after=True)
            snap(700)
            ui.locator('#results').wait_for(state='visible')
            ui.evaluate('window.scrollTo(0,document.querySelector("#results").offsetTop-24)')
            step(3)
            snap(2400)
            start = ui.evaluate('window.scrollY')
            for delta in range(30,361,30):
                ui.evaluate('(y)=>window.scrollTo(0,y)', start + delta)
                snap(65)
            snap(2200)
            for delta in range(330,-1,-30):
                ui.evaluate('(y)=>window.scrollTo(0,y)', start + delta)
                snap(65)
            snap(1500)
            browser.close()
    finally:
        server.shutdown()
    # One shared palette keeps UI colors stable across frames.
    palette = frames[0].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    out = ROOT / 'docs' / 'hero.gif'
    indexed[0].save(out, save_all=True, append_images=indexed[1:], duration=durations, loop=0, optimize=True, disposal=1)
    frames[0].save('/tmp/aeo-hero-first.png')
    frames[7].save('/tmp/aeo-hero-results.png')
    print(f'{out}: {out.stat().st_size:,} bytes, {len(frames)} frames')

if __name__ == '__main__': main()

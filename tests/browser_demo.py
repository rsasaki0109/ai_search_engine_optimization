"""Sample demo QA: playwright and Chromium; no external audit requests."""
from pathlib import Path
import json
import os
import sys
import threading
from unittest.mock import patch
from playwright.sync_api import sync_playwright, expect
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app

def main():
    server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with patch('app.fetch',side_effect=AssertionError('external fetch in demo')),sync_playwright() as p:
            browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE','/usr/bin/chromium') or None,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1280,'height':900},accept_downloads=True)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.route('https://fonts.googleapis.com/**',lambda r:r.abort())
            base=f'http://127.0.0.1:{server.server_port}'
            page.goto(base)
            real=app.analyze(dict(body='<title>Saved real page</title>',url='https://example.com/real',robots_header=''))
            saved=[dict(at='2026-11-15T00:00:00Z',report=real)]
            page.evaluate('(rows)=>localStorage.setItem(AEOHistory.KEY,JSON.stringify(rows))',saved)
            page.reload()
            original=page.evaluate('localStorage.getItem(AEOHistory.KEY)')
            page.locator('#demo-start').click()
            expect(page.locator('#score')).to_have_text('30')
            expect(page.locator('#demo-controls')).to_be_visible()
            expect(page.locator('#comparison')).to_be_hidden()
            expect(page.locator('.repair')).to_have_count(6)
            page.locator('#demo-after').click()
            expect(page.locator('#score')).to_have_text('100')
            expect(page.locator('#comparison')).to_contain_text('+70 点')
            expect(page.locator('#comparison')).to_contain_text('改善：')
            expect(page.locator('#demo-source')).to_have_attribute('href','/demo/after')
            with page.expect_download() as capture:page.locator('#download-markdown').click()
            text=Path(capture.value.path()).read_text()
            assert '検証用サンプル' in text and '**+70 点**' in text
            with page.expect_download() as capture:page.locator('#download').click()
            assert json.loads(Path(capture.value.path()).read_text())['is_demo']
            assert page.context.request.get(base+'/demo/after').status==200
            page.locator('#demo-before').click()
            expect(page.locator('#score')).to_have_text('30')
            expect(page.locator('#comparison')).to_be_hidden()
            assert page.evaluate('localStorage.getItem(AEOHistory.KEY)')==original
            expect(page.locator('.history-row')).to_have_count(1)
            for width in [375,320]:
                page.set_viewport_size({'width':width,'height':850})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.locator('.history-row').get_by_role('button',name='結果を見る',exact=True).click()
            expect(page.locator('#demo-controls')).to_be_hidden()
            expect(page.locator('#page-title')).to_have_text('Saved real page')
            assert not errors,errors
            browser.close()
            print('Demo browser checks passed: network-free analysis, before/after comparison, sample labels in exports, unchanged history, source page, mobile widths, return to real result')
    finally:server.shutdown()

if __name__=='__main__':main()

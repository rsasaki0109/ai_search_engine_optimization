"""Optional browser checks: Python playwright + /usr/bin/chromium required.
Run: python3 tests/browser_history.py
All audit data comes from fixtures; no external page is fetched.
"""
from pathlib import Path
import os
import sys
import threading
from unittest.mock import patch
from playwright.sync_api import sync_playwright, expect
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app

state = {'body': '<html lang="ja"><h1>Sample</h1></html>', 'failed': False}

def fixture(url, deadline=None):
    if state['failed']: raise ValueError('テスト用の取得失敗')
    return dict(url=url, status=200, type='text/plain' if url.endswith('/robots.txt') else 'text/html', body='User-agent: *\nAllow: /' if url.endswith('/robots.txt') else state['body'], robots_header='')


def main():
    server = app.ThreadingHTTPServer(('127.0.0.1',0), app.Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with patch('app.fetch', side_effect=fixture), sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE', '/usr/bin/chromium') or None, args=['--no-sandbox'])
            context = browser.new_context(viewport={'width':1280,'height':900})
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.route('https://fonts.googleapis.com/**', lambda r:r.abort())
            base = f'http://127.0.0.1:{server.server_port}'
            page.goto(base)
            expect(page.locator('#history')).to_be_hidden()
            def run(url='https://example.com/guide'):
                page.locator('#url').fill(url)
                page.locator('#submit').click()
                expect(page.locator('#status')).to_have_text('診断が完了しました。')
            run()
            expect(page.locator('.history-row')).to_have_count(1)
            expect(page.locator('#comparison')).to_be_hidden()
            state['body'] = '<html lang="ja"><title>改善したページ</title><h1>Sample</h1></html>'
            page.locator('.history-row').first.get_by_role('button',name='再診断',exact=True).click()
            expect(page.locator('.history-row')).to_have_count(2)
            expect(page.locator('#comparison')).to_contain_text('+10 点')
            expect(page.locator('#comparison')).to_contain_text('改善：ページタイトル')
            page.reload()
            expect(page.locator('.history-row')).to_have_count(2)
            requests = []
            page.on('request', lambda r: requests.append(r.url) if '/api/audit' in r.url else None)
            page.locator('.history-row').first.get_by_role('button',name='結果を見る',exact=True).click()
            expect(page.locator('#score')).to_have_text('40')
            expect(page.locator('#status')).to_contain_text('保存結果')
            assert not requests
            page.locator('.history-row').nth(1).get_by_role('button',name='結果を見る',exact=True).click()
            expect(page.locator('#score')).to_have_text('30')
            expect(page.locator('#comparison')).to_be_hidden()
            run('https://example.com/other?q=1')
            expect(page.locator('#comparison')).to_be_hidden()
            expect(page.locator('.history-row')).to_have_count(3)
            state['failed'] = True
            page.locator('#submit').click()
            expect(page.locator('#status')).to_contain_text('テスト用の取得失敗')
            expect(page.locator('.history-row')).to_have_count(3)
            state['failed'] = False
            # Fill past retention limit through UI, then ensure reload keeps only ten.
            for n in range(9): run(f'https://example.com/page/{n}')
            expect(page.locator('.history-row')).to_have_count(10)
            page.reload()
            expect(page.locator('.history-row')).to_have_count(10)
            for width in [375,320]:
                page.set_viewport_size({'width':width,'height':850})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.locator('#clear-history').click()
            expect(page.locator('#history')).to_be_hidden()
            assert page.evaluate('localStorage.getItem(AEOHistory.KEY)') is None
            page.reload()
            expect(page.locator('#history')).to_be_hidden()
            page.evaluate("localStorage.setItem(AEOHistory.KEY, '{broken')")
            page.reload()
            expect(page.locator('#history')).to_be_hidden()
            # Storage denial must not turn a successful audit into an error.
            page.evaluate("() => { Storage.prototype.setItem = () => { throw new Error('denied'); }; }")
            run()
            expect(page.locator('.history-row')).to_have_count(1)
            expect(page.locator('#history-status')).to_contain_text('保存できませんでした')
            assert not errors, errors
            browser.close()
            print('Browser history checks passed: comparison, persistence, restore without fetch, failure, 10-record retention, deletion, corrupt storage, denied storage, 375px/320px layouts')
    finally: server.shutdown()

if __name__ == '__main__': main()

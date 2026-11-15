"""Optional report QA: playwright, Chromium and pdftotext required.
Run: python3 tests/browser_report.py. Uses local fixtures only.
"""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import threading
from unittest.mock import patch
from playwright.sync_api import sync_playwright, expect
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


def main():
    server = app.ThreadingHTTPServer(('127.0.0.1',0), app.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    sample = dict(url='https://example.com/guide', body='<html lang="ja"><title>Report Demo</title><h1>Report Demo</h1><p>PRIVATE_EXCERPT_MARKER</p><script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"Article"},{"@type":"Organization"}]}</script><script type="application/ld+json">broken</script></html>', robots_header='')
    report = app.analyze(sample, 'User-agent: *\nDisallow: /\nAllow: /guide$\n\nUser-agent: GPTBot\nDisallow: /')
    old = json.loads(json.dumps(report)); old['score'] -= 10
    next(c for c in old['checks'] if c['id']=='title')['passed'] = False
    unrelated = json.loads(json.dumps(report)); unrelated['url']='https://example.com/PRIVATE_OTHER_HISTORY'
    saved = [dict(at='2026-11-15T02:00:00Z',report=report), dict(at='2026-11-14T02:00:00Z',report=old), dict(at='2026-11-13T02:00:00Z',report=unrelated)]
    try:
        with tempfile.TemporaryDirectory() as temp, sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1280,'height':900}, accept_downloads=True)
            errors=[];page.on('pageerror', lambda e:errors.append(str(e)))
            page.route('https://fonts.googleapis.com/**',lambda r:r.abort())
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.evaluate('(records)=>localStorage.setItem(AEOHistory.KEY, JSON.stringify(records))',saved)
            page.reload()
            page.locator('.history-row').first.get_by_role('button',name='結果を見る',exact=True).click()
            expect(page.locator('#comparison')).to_contain_text('+10 点')
            expect(page.locator('.schema-card')).to_have_count(2)
            expect(page.locator('.bot').first).to_contain_text('Allow: /guide$（3行目）')
            expect(page.locator('.bot').last).to_contain_text('適用グループ：GPTBot')
            expect(page.locator('.bot').last).to_contain_text('制限')
            expect(page.locator('.schema-card').first).to_contain_text('Article、Organization')
            expect(page.locator('.schema-card').nth(1)).to_contain_text('JSONの構文を解析できません')
            with page.expect_download() as capture: page.locator('#download-markdown').click()
            downloaded=capture.value
            assert downloaded.suggested_filename=='aeo-report.md'
            text=Path(downloaded.path()).read_text()
            assert '2026\\-11\\-15T02:00:00Z' in text
            assert '**+10 点**' in text and '```html' in text
            assert '## 構造化データの詳細' in text and 'Article' in text
            assert 'Allow: /guide$（3行目）' in text
            assert 'PRIVATE_EXCERPT_MARKER' not in text and 'PRIVATE_OTHER_HISTORY' not in text
            with page.expect_download() as capture: page.locator('#download').click()
            assert json.loads(Path(capture.value.path()).read_text())==report
            # Open just one detail: print expands all, then restores original state.
            page.locator('.repair summary').first.click()
            before=page.locator('.repair').evaluate_all('(nodes)=>nodes.map(n=>n.open)')
            page.pdf(path=f'{temp}/report.pdf',format='A4',print_background=True)
            assert page.locator('.repair').evaluate_all('(nodes)=>nodes.map(n=>n.open)')==before
            pdftext=subprocess.check_output(['pdftotext',f'{temp}/report.pdf','-']).decode()
            assert 'Report Demo' in pdftext and 'application/ld+json' in pdftext
            assert '2026/11/15' in pdftext
            assert 'Article' in pdftext and 'Organization' in pdftext
            assert 'Allow: /guide$' in pdftext
            assert 'PRIVATE_EXCERPT_MARKER' not in pdftext and 'PRIVATE_OTHER_HISTORY' not in pdftext
            page.evaluate('() => { window.print = () => { window.printCalled = true; }; }')
            page.locator('#print-report').click()
            assert page.evaluate('window.printCalled')
            for width in [375,320]:
                page.set_viewport_size({'width':width,'height':850})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            # Legacy records remain viewable but cannot be compared to new criteria.
            legacy=json.loads(json.dumps(old));legacy.pop('analysis_version');legacy.pop('schema_details')
            page.evaluate('(rows)=>localStorage.setItem(AEOHistory.KEY,JSON.stringify(rows))', [saved[0],dict(at=saved[1]['at'],report=legacy)])
            page.reload()
            page.locator('.history-row').first.get_by_role('button',name='結果を見る',exact=True).click()
            expect(page.locator('#comparison')).to_contain_text('判定基準')
            expect(page.locator('#comparison')).not_to_contain_text('+10 点')
            page.locator('.history-row').nth(1).get_by_role('button',name='結果を見る',exact=True).click()
            expect(page.locator('#schema-section')).to_be_hidden()
            # Deleting history must clear comparison from both screen and export.
            page.locator('#clear-history').click()
            with page.expect_download() as capture: page.locator('#download-markdown').click()
            assert '## 前回との比較' not in Path(capture.value.path()).read_text()
            assert not errors, errors
            browser.close()
            print('Browser report checks passed: Markdown/JSON downloads, original timestamp, comparison, PDF content and privacy, detail restoration, print action, 320px/375px layout, history deletion')
    finally: server.shutdown()

if __name__ == '__main__': main()

"""Optional batch QA: playwright + /usr/bin/chromium required. Local fixtures only."""
from pathlib import Path
import json
import os
import sys
import threading
from unittest.mock import patch
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app

release=threading.Event()

def fixture(url, deadline=None):
    path=urlsplit(url).path
    if path in ('/sitemap.xml','/pages.xml'):
        body='<sitemapindex><sitemap><loc>https://example.com/pages.xml</loc></sitemap></sitemapindex>' if path=='/sitemap.xml' else '<urlset>'+''.join(f'<url><loc>https://example.com/{n}</loc></url>' for n in range(6))+'</urlset>'
        return dict(url=url,status=200,type='application/xml',body=body)
    if path=='/slow': release.wait(timeout=5)
    if path=='/robots.txt':return dict(url=url,status=200,type='text/plain',body='User-agent: *\nAllow: /')
    return dict(url=url,status=404 if path.startswith('/broken') else 200,type='text/html',body=f'<html lang="ja"><title>Page {path}</title><h1>Sample</h1></html>',robots_header='')


def main():
    server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with patch('app.fetch',side_effect=fixture),sync_playwright() as p:
            browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE', '/usr/bin/chromium') or None,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1280,'height':900},accept_downloads=True)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            calls=[];page.on('request',lambda r:calls.append(r.url) if '/api/audit' in r.url else None)
            page.route('https://fonts.googleapis.com/**',lambda r:r.abort())
            base=f'http://127.0.0.1:{server.server_port}'
            page.goto(base)
            page.locator('#sitemap-picker summary').click()
            page.locator('#sitemap-url').fill('https://example.com/sitemap.xml')
            page.locator('#sitemap-load').click()
            expect(page.locator('.sitemap-child')).to_have_count(1)
            page.locator('.sitemap-child').click()
            expect(page.locator('.sitemap-choice')).to_have_count(6)
            for n in range(5):page.locator('.sitemap-choice input').nth(n).check()
            expect(page.locator('.sitemap-choice input').nth(5)).to_be_disabled()
            page.locator('#sitemap-apply').click()
            expect(page.locator('#batch-urls')).to_have_value('\n'.join(f'https://example.com/{n}' for n in range(5)))
            assert not calls # Loading candidates never starts audits.

            expect(page.locator('#audit-form')).to_be_hidden()
            expect(page.locator('#batch-toggle')).to_have_attribute('aria-expanded','true')
            page.locator('#batch-urls').fill('\n'.join(f'https://example.com/{n}' for n in range(6)))
            page.locator('#batch-submit').click()
            expect(page.locator('#batch-status')).to_contain_text('5件まで')
            assert not calls
            page.locator('#batch-urls').fill('https://example.com/guide#one\nhttps://example.com/guide#two\nhttps://example.com/about\nhttps://example.com/broken')
            page.locator('#batch-submit').click()
            expect(page.locator('#batch-status')).to_have_text('一括診断が完了しました。')
            expect(page.locator('.batch-row')).to_have_count(3)
            expect(page.locator('#batch-summary')).to_contain_text('3件中 2件成功・1件取得失敗')
            expect(page.locator('.history-row')).to_have_count(2)
            expect(page.locator('.batch-row').nth(2)).to_contain_text('HTTP 404')
            with page.expect_download() as capture:page.locator('#batch-download').click()
            assert capture.value.suggested_filename=='aeo-batch-report.json'
            data=json.loads(Path(capture.value.path()).read_text())
            assert data['summary']['total']==3 and data['summary']['succeeded']==2
            assert data['results'][0]['url']=='https://example.com/guide'
            before=len(calls)
            page.locator('.batch-row').first.get_by_role('button',name='詳細を見る').click()
            expect(page.locator('#page-title')).to_have_text('Page /guide')
            assert len(calls)==before
            expect(page.locator('.repair')).not_to_have_count(0)
            for width in [375,320]:
                page.set_viewport_size({'width':width,'height':850})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.locator('#batch-urls').fill('https://example.com/broken\nhttps://example.com/broken-two')
            page.locator('#batch-submit').click()
            expect(page.locator('#batch-summary')).to_contain_text('2件中 0件成功・2件取得失敗')
            expect(page.locator('#batch-summary')).not_to_contain_text('平均')
            expect(page.locator('.history-row')).to_have_count(2)
            expect(page.locator('#batch-list button')).to_have_count(0)
            page.locator('#batch-urls').fill('https://example.com/slow')
            page.locator('#batch-submit').click()
            expect(page.locator('#batch-toggle')).to_be_disabled()
            expect(page.locator('#submit')).to_be_disabled()
            release.set()
            expect(page.locator('#batch-status')).to_have_text('一括診断が完了しました。')
            expect(page.locator('#batch-toggle')).to_be_enabled()
            page.locator('#batch-toggle').click()
            page.locator('#url').fill('https://example.com/single')
            page.locator('#submit').click()
            expect(page.locator('#status')).to_have_text('診断が完了しました。')
            expect(page.locator('#batch-results')).to_be_hidden()
            expect(page.locator('.history-row')).to_have_count(4)
            page.reload()
            expect(page.locator('.history-row')).to_have_count(4)
            response=page.request.post(base+'/api/audit/batch',data={'urls':[]})
            assert response.status==400
            assert not errors,errors
            browser.close()
            print('Browser batch checks passed: limits, partial failure, deduplication, details, JSON download, all-failure, concurrency UI, single-mode regression, persistence, mobile widths, API validation')
    finally:
        release.set();server.shutdown()

if __name__=='__main__':main()

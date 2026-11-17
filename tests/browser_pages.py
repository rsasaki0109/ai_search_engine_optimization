"""Verify the built Pages site at a project subpath; loads pinned Pyodide CDN."""
from pathlib import Path
import functools
import json
import os
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]

def main():
    with tempfile.TemporaryDirectory() as folder:
        (Path(folder)/'project').symlink_to(ROOT/'dist-pages',target_is_directory=True)
        server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(SimpleHTTPRequestHandler,directory=folder))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE','/usr/bin/chromium') or None,args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1280,'height':900},accept_downloads=True)
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                requests=[];page.on('request',lambda r:requests.append((r.method,r.url)))
                page.route('https://fonts.googleapis.com/**',lambda r:r.abort())
                page.goto(f'http://127.0.0.1:{server.server_port}/project/')
                page.locator('#demo-start').click()
                expect(page.locator('#score')).to_have_text('30')
                page.locator('#demo-after').click()
                expect(page.locator('#comparison')).to_contain_text('+70 点')
                expect(page.locator('#demo-source')).to_have_attribute('href','./demo/after.html')
                page.locator('#pages-url').fill('https://demo.example/guide')
                page.locator('#pages-html').set_input_files(str(ROOT/'static/demo/after.html'))
                page.locator('#pages-submit').click()
                expect(page.locator('#pages-status')).to_contain_text('端末内の診断が完了',timeout=120000)
                expect(page.locator('#score')).to_have_text('100')
                expect(page.locator('#robots-note')).to_contain_text('未提供')
                expect(page.locator('#demo-controls')).to_be_hidden()
                expect(page.locator('.history-row')).to_have_count(1)
                with page.expect_download() as captured:page.locator('#download').click()
                report=json.loads(Path(captured.value.path()).read_text())
                assert report['source_mode']=='html-file'
                page.locator('#pages-html').set_input_files(str(ROOT/'static/demo/before.html'))
                page.locator('#pages-robots').set_input_files({'name':'robots.txt','mimeType':'text/plain','buffer':b'User-agent: *\nDisallow: /'})
                page.locator('#pages-submit').click()
                expect(page.locator('#comparison')).to_contain_text('-70 点',timeout=30000)
                expect(page.locator('.bot').first).to_contain_text('制限')
                page.reload()
                expect(page.locator('.history-row')).to_have_count(2)
                page.locator('.history-row').first.get_by_role('button',name='結果を見る',exact=True).click()
                expect(page.locator('#score')).to_have_text('30')
                for width in [375,320]:
                    page.set_viewport_size({'width':width,'height':850})
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                assert all(method=='GET' for method,url in requests),requests
                assert not any('/api/' in url for method,url in requests),requests
                assert not errors,errors
                browser.close()
                print('Pages checks passed: subpath assets, demo comparison, real in-browser Python, HTML and robots diagnosis, history, export, mobile, no upload/API requests')
        finally:server.shutdown()
if __name__=='__main__':main()

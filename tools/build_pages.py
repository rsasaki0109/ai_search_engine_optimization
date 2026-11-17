"""Build a static GitHub Pages site using the same pure Python analyzer."""
import ast
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import app


def build():
    out=ROOT/'dist-pages'
    if out.exists():shutil.rmtree(out)
    shutil.copytree(ROOT/'static',out)
    for path in (ROOT/'pages').iterdir():shutil.copy2(path,out/path.name)
    tree=ast.parse((ROOT/'app.py').read_text())
    names={'reject_json_constant','validate_url','Page','inspect_schemas','repair_example','analyze'}
    nodes=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in names]
    source='import json, re\nfrom html import escape\nfrom html.parser import HTMLParser\nfrom urllib.parse import urlsplit, urlunsplit\nfrom robots import RobotsRules\n'
    source+=f'BOTS = {app.BOTS!r}\nANALYSIS_VERSION = {app.ANALYSIS_VERSION!r}\n'
    source+='\n\n'.join(ast.unparse(node) for node in nodes)
    (out/'analysis.py').write_text(source)
    shutil.copy2(ROOT/'robots.py',out/'robots.py')
    (out/'demo.json').write_text(json.dumps(app.demo_audits(),ensure_ascii=False))
    html=(out/'index.html').read_text().replace('href="/','href="./').replace('src="/','src="./')
    html=html.replace('<head>','<head><script src="./pages-mode.js"></script>')
    html=html.replace('</head>','<script src="./pages.js" defer></script></head>')
    html=html.replace('PUBLIC BETA / v0.2','GITHUB PAGES EDITION')
    html=html.replace('URLから技術設定を確認し、次に取り組む改善を見つけましょう。','保存したHTMLを端末内で診断し、次に取り組む改善を見つけましょう。')
    html=html.replace('<form id="audit-form">','''<section id="pages-local"><p class="notice">GitHub Pages版：URLの自動取得は行いません。ブラウザでページのHTMLを保存して選択してください。HTMLはサーバーへ送信せず、スクリプトも実行しません。HTTPヘッダーは検証できません。</p><form id="pages-form"><label for="pages-url">保存したページの元のURL</label><input id="pages-url" type="url" required placeholder="https://example.com/guide"><label for="pages-html">HTMLファイル（UTF-8、2MBまで）</label><input id="pages-html" type="file" accept=".html,.htm,text/html" required><label for="pages-robots">robots.txt（任意、500KiBまで）</label><input id="pages-robots" type="file" accept=".txt,text/plain"><button id="pages-submit" type="submit">HTMLを端末内で診断する</button><p class="hint">初回診断はPython実行環境をCDNから読み込むため時間がかかります。読み込んだファイルは端末内で処理します。</p><p id="pages-status" role="status" aria-live="polite"></p></form></section><form id="audit-form" hidden>''')
    html=html.replace('</body>','<style>#audit-form,#batch-toggle,#batch-form,#sitemap-picker{display:none!important}#pages-local label{margin-top:18px}#pages-local input{width:100%;margin-bottom:10px}#pages-submit{margin-top:15px}#pages-status{font-size:12px;line-height:1.9}@media print{#pages-local{display:none}}</style></body>')
    (out/'index.html').write_text(html)
    (out/'demo.js').write_text((out/'demo.js').read_text().replace('`/demo/${stage}`','`./demo/${stage}.html`'))
    (out/'.nojekyll').touch()
    print(out)

if __name__=='__main__':build()

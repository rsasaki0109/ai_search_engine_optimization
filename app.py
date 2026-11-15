"""Dependency-free, single-page technical AEO audit. Python 3.12+."""
import argparse
import http.client
import ipaddress
import json
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, urljoin
from robots import RobotsRules
from sitemap import parse_sitemap

ROOT = Path(__file__).parent
LIMIT = 2_000_000
BOTS = ['OAI-SearchBot', 'ChatGPT-User', 'PerplexityBot', 'Googlebot', 'GPTBot']
ANALYSIS_VERSION = '2'


def reject_json_constant(value):
    raise ValueError(f'{value} is not valid JSON')


def validate_url(url):
    if not isinstance(url, str) or len(url) > 2048 or any(ord(c) < 33 for c in url):
        raise ValueError('有効なURLを入力してください。')
    p = urlsplit(url)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise ValueError('http:// または https:// で始まる公開URLを入力してください。')
    if p.port not in (None, 80, 443):
        raise ValueError('標準のHTTP/HTTPSポートのみ対応しています。')
    return p


def fetch(url, deadline=None):
    deadline = deadline or time.monotonic() + 25
    for _ in range(6):
        p = validate_url(url)
        host = p.hostname.encode('idna').decode('ascii')
        port = p.port or (443 if p.scheme == 'https' else 80)
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError('公開インターネット上のURLのみ診断できます。')
        timeout = min(8, deadline - time.monotonic())
        if timeout <= 0:
            raise TimeoutError('取得がタイムアウトしました。')
        cls = http.client.HTTPSConnection if p.scheme == 'https' else http.client.HTTPConnection
        conn = cls(host, port, timeout=timeout)
        # Pin the validated address; HTTPS still validates the original hostname.
        address = addresses[0][4][0]
        conn._create_connection = lambda addr, timeout, source_address=None: socket.create_connection((address, port), timeout, source_address)
        try:
            conn.request('GET', urlunsplit(('', '', p.path or '/', p.query, '')), headers={'User-Agent': 'AEO-Check/0.1', 'Accept-Encoding': 'identity'})
            r = conn.getresponse()
            if r.status in (301, 302, 303, 307, 308):
                location = r.getheader('Location')
                if not location:
                    raise ValueError('転送先が指定されていません。')
                url = urljoin(url, location)
                continue
            data = r.read(LIMIT + 1)
            if len(data) > LIMIT:
                raise ValueError('取得サイズの上限（2MB）を超えています。')
            charset = r.headers.get_content_charset() or 'utf-8'
            try:
                body = data.decode(charset, errors='replace')
            except LookupError:
                body = data.decode('utf-8', errors='replace')
            return {'url': url, 'status': r.status, 'body': body, 'type': r.getheader('Content-Type', ''), 'robots_header': r.getheader('X-Robots-Tag', '')}
        finally:
            conn.close()
    raise ValueError('リダイレクト回数の上限を超えました。')


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ''
        self.headings = []
        self.meta = {}
        self.canonical = ''
        self.lang = ''
        self.schemas = []
        self.schema_errors = {}
        self.text = []
        self.images = 0
        self.alt = 0
        self.skip = 0
        self.in_title = False
        self.heading = None
        self.json_data = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style', 'noscript', 'template'):
            self.skip += 1
        if tag == 'script' and a.get('type', '').lower() == 'application/ld+json':
            self.json_data = ''
        if tag == 'title': self.in_title = True
        if tag in ('h1', 'h2', 'h3'): self.heading = [tag, '']
        if tag == 'html': self.lang = a.get('lang', '')
        if tag == 'meta': self.meta[a.get('name', '').lower()] = a.get('content', '')
        if tag == 'link' and 'canonical' in a.get('rel', '').lower().split(): self.canonical = a.get('href', '')
        if tag == 'img':
            self.images += 1
            self.alt += bool(a.get('alt', '').strip())

    def handle_endtag(self, tag):
        if tag == 'script' and self.json_data is not None:
            try:
                self.schemas.append(json.loads(self.json_data, parse_constant=reject_json_constant))
            except (ValueError, TypeError, RecursionError):
                self.schema_errors[len(self.schemas)] = 'JSONの構文を解析できません。深すぎるJSONも対象です。'
                self.schemas.append(None)
            self.json_data = None
        if tag in ('script', 'style', 'noscript', 'template'): self.skip = max(0, self.skip - 1)
        if tag == 'title': self.in_title = False
        if self.heading and tag == self.heading[0]:
            self.headings.append(self.heading)
            self.heading = None

    def handle_data(self, data):
        if self.json_data is not None: self.json_data += data
        if self.in_title: self.title += data
        if self.heading and not self.skip: self.heading[1] += data
        if not self.skip and not self.in_title: self.text.append(data)


def inspect_schemas(parser):
    """Bounded structural inspection, not JSON-LD expansion or vocabulary validation."""
    details = []
    context_budget = [0]
    schema_contexts = {'http://schema.org', 'https://schema.org', 'http://schema.org/', 'https://schema.org/'}
    def context(value, vocab, prefixes, depth=0):
        context_budget[0] += 1
        if depth > 60 or context_budget[0] > 2000:
            raise ValueError('@contextが解析上限を超えました。手動で検証してください。')
        prefixes = dict(prefixes)
        if isinstance(value, list):
            for part in value:
                vocab, prefixes = context(part, vocab, prefixes, depth + 1)
        elif value is None:
            vocab, prefixes = False, {}
        elif isinstance(value, str):
            # Other remote contexts are deliberately not fetched or expanded.
            if value not in schema_contexts:
                raise ValueError('独自・外部@contextは展開できません。手動で検証してください。')
            vocab = True
        elif isinstance(value, dict):
            if '@vocab' in value:
                vocab = value['@vocab'] in schema_contexts if isinstance(value['@vocab'], str) else False
            for key, target in value.items():
                if key.startswith('@'): continue
                if isinstance(target, dict) and target.get('@prefix') is False:
                    prefixes.pop(key, None)
                    continue
                target = target.get('@id') if isinstance(target, dict) else target
                if isinstance(target, str) and target in schema_contexts:
                    prefixes[key] = True
                else:
                    prefixes.pop(key, None)
        else:
            raise ValueError('@contextは文字列・オブジェクト・配列・nullのいずれかにしてください。')
        return vocab, prefixes

    for index, document in enumerate(parser.schemas):
        context_budget[0] = 0
        types, issues = set(), []
        if index in parser.schema_errors:
            issues.append(parser.schema_errors[index])
        elif not isinstance(document, (dict, list)) or not document:
            issues.append('ルートには空でないオブジェクトまたは配列が必要です。')
        else:
            stack = [(document, False, {}, 0, True)]
            visited = 0
            while stack:
                node, vocab, prefixes, depth, root = stack.pop()
                visited += 1
                if depth > 60 or visited > 2000:
                    issues.append('解析上限（深さ60・要素2000）に達しました。手動で検証してください。')
                    break
                if isinstance(node, list):
                    stack.extend((child, vocab, prefixes, depth + 1, root) for child in node)
                    continue
                if not isinstance(node, dict):
                    if root: issues.append('ルートや@graph内の要素はオブジェクトである必要があります。')
                    continue
                if '@context' in node:
                    try:
                        vocab, prefixes = context(node['@context'], vocab, prefixes)
                    except ValueError as error:
                        issues.append(str(error))
                        vocab, prefixes = False, {}
                if '@type' in node:
                    declared = node['@type'] if isinstance(node['@type'], list) else [node['@type']]
                    if not declared or any(not isinstance(t, str) or not t.strip() for t in declared):
                        issues.append('@typeは空でない文字列または文字列配列にしてください。')
                    for item in declared:
                        if not isinstance(item, str): continue
                        name = None
                        for base in schema_contexts:
                            if base.endswith('/') and item.startswith(base): name = item[len(base):]
                        if ':' in item and not item.startswith(('http:', 'https:')):
                            prefix, local = item.split(':', 1)
                            if prefixes.get(prefix): name = local
                        elif ':' not in item and vocab:
                            name = item
                        if name and re.fullmatch(r'[A-Za-z][A-Za-z0-9]*', name):
                            types.add(name)
                        else:
                            issues.append('@typeをSchema.orgとして解釈できません。@contextや型の指定を手動で確認してください。')
                for key, child in node.items():
                    if key == '@context': continue
                    if key == '@graph' and not isinstance(child, (dict, list)):
                        issues.append('@graphはオブジェクトまたは配列にしてください。')
                    if isinstance(child, (dict, list)):
                        stack.append((child, vocab, prefixes, depth + 1, key == '@graph'))
            if not types:
                issues.append('Schema.orgの@typeを検出できませんでした。独自・外部contextの展開は行いません。')
        details.append(dict(block=index + 1, types=sorted(types), issues=list(dict.fromkeys(issues)), passed=bool(types) and not issues))
    return details


def repair_example(key, parser, page):
    """Templates stay explicit about editorial choices and deployment scope."""
    title = parser.title.strip() or '【ページの主題が伝わるタイトルに置換】'
    url = urlunsplit(urlsplit(page['url'])._replace(fragment=''))
    schema = json.dumps({'@context': 'https://schema.org', '@type': 'WebPage',
                         'name': title, 'url': url}, ensure_ascii=False, indent=2)
    # JSON embedded in a script element must not terminate the element.
    schema = schema.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    examples = {
        'title': ('HTML / <head>', '<title>【ページの主題】｜【サイト名】</title>', '【】内を実際の内容に置き換えてください。'),
        'description': ('HTML / <head>', '<meta name="description" content="【このページで答える問いと、読者が得られる情報を簡潔に記入】">', 'ページに書かれている内容を要約してください。'),
        'h1': ('HTML / <body>', f'<h1>{escape(title)}</h1>', '既存のH1が複数ある場合は見出し階層を整理し、ページの主題を1つにまとめてください。'),
        'headings': ('HTML / 本文', '<h2>【読者の問い・節の主題】</h2>\n<p>【問いへの答えを最初に記入】</p>', '実際の内容に置き換え、既存の見出し階層に合わせてください。'),
        'content': ('HTML / 本文', '<main>\n  <h1>【ページの主題】</h1>\n  <p>【主な説明と具体的な根拠】</p>\n</main>', '既存のmainやH1に統合してください。JavaScriptでのみ表示している本文はSSRや静的生成でHTMLに含めてください。'),
        'schema': ('HTML / <head>', '<script type="application/ld+json">\n' + schema + '\n</script>', '汎用WebPageのひな形です。name・urlを確認し、既存データが壊れている場合は修正してください。内容に応じた型・項目を追加し、Schema Markup Validatorで検証してください。'),
        'canonical': ('HTML / <head>', f'<link rel="canonical" href="{escape(url, quote=True)}">', '取得後のURLを候補として表示しています。クエリを含め、実際に正規化したい公開URLへ修正してください。'),
        'language': ('HTML / 開始タグ', '<html lang="ja">', '既存のhtmlタグに統合してください。jaは日本語の例です。本文の言語に合わせて変更してください。'),
        'index': ('公開設定 / 手動確認', None, '公開する意図を確認してから、meta robotsとHTTPレスポンスのX-Robots-Tagのnoindex / noneを見直してください。HTTPヘッダーはHTMLの変更だけでは解除できません。'),
    }
    location, code, note = examples[key]
    return dict(location=location, code=code, note=note)


def analyze(page, robots=None, robots_error=None):
    parser = Page()
    parser.feed(page['body'])
    content = re.sub(r'\s+', ' ', ' '.join(parser.text)).strip()
    checks = []
    def add(key, label, passed, evidence, action, weight=10):
        checks.append(dict(id=key, label=label, passed=passed, evidence=evidence, action=action, weight=weight))
    add('title', 'ページタイトル', bool(parser.title.strip()), parser.title.strip() or '未設定', 'ページの主題と対象読者が伝わるtitleを設定する。')
    desc = parser.meta.get('description', '').strip()
    add('description', '概要の明示', bool(desc), desc or 'meta descriptionなし', 'ページの答えを簡潔に要約したdescriptionを設定する。')
    h1 = [h[1].strip() for h in parser.headings if h[0] == 'h1']
    add('h1', '主題を示す見出し', len(h1) == 1 and bool(h1[0]), f'H1: {len(h1)}件', '主題を明確に示すH1を1つ設ける。')
    add('headings', '本文の構造', any(h[0] == 'h2' and h[1].strip() for h in parser.headings), f'H2: {sum(h[0] == "h2" for h in parser.headings)}件', '内容をH2で整理し、各節の冒頭に端的な答えを書く。')
    add('content', '取得可能な本文', len(content) >= 200, f'本文テキスト: {len(content)}文字', '主な説明をサーバーから返すHTMLに含める。短いページでは内容に応じて判断する。', 15)
    schema_details = inspect_schemas(parser)
    types = sorted({t for item in schema_details for t in item['types']})
    schema_passed = bool(schema_details) and all(item['passed'] for item in schema_details)
    evidence = f'JSON-LD: {len(schema_details)}件、要確認: {sum(not item["passed"] for item in schema_details)}件。型: {", ".join(types) or "未検出"}'
    add('schema', '構造化データ', schema_passed, evidence, '詳細の問題点を確認し、既存JSON-LDの@context・@type・構文を修正する。未設定なら内容に合うJSON-LDを追加する。', 15)
    add('canonical', '正規URL', bool(parser.canonical), parser.canonical or '未設定', '重複ページの扱いを明確にするcanonical URLを設定する。')
    add('language', 'ページ言語', bool(parser.lang.strip()), parser.lang or 'lang属性なし', 'html要素のlang属性を設定する（日本語ならja）。', 5)
    directives = parser.meta.get('robots', '') + ',' + page.get('robots_header', '')
    blocked = bool(re.search(r'\b(noindex|none)\b', directives, re.I))
    add('index', 'インデックス設定', not blocked, directives.strip(', ') or 'noindex指定は検出されませんでした', '検索に公開するページならnoindexを解除する。非公開の意図がある場合は維持する。', 15)
    bots = []
    if robots is not None:
        try:
            rules = RobotsRules(robots)
            for bot in BOTS:
                bots.append({'name': bot, **rules.decision(bot, page['url']), 'purpose': '学習用' if bot == 'GPTBot' else '検索・ユーザー取得'})
        except ValueError as error:
            robots_error = str(error)
    score = round(sum(c['weight'] for c in checks if c['passed']) / sum(c['weight'] for c in checks) * 100)
    for check in checks:
        if not check['passed']:
            check['repair'] = repair_example(check['id'], parser, page)
    return dict(analysis_version=ANALYSIS_VERSION, schema_details=schema_details, url=page['url'], title=parser.title.strip(), score=score, checks=checks, bots=bots, robots_error=robots_error, headings=parser.headings[:30], excerpt=content[:500], note='独自の技術チェック指標です。AI検索での引用率や掲載を測定・保証するものではありません。JSON-LDは構文とSchema.orgのcontext・型指定を基本確認します。型の実在・必須項目・リッチリザルト適合は未検証です。外部contextは展開しません。')


def audit(url):
    deadline = time.monotonic() + 25
    page = fetch(url, deadline)
    if page['status'] != 200: raise ValueError(f'ページ取得に失敗しました（HTTP {page["status"]}）。')
    if not any(t in page['type'].lower() for t in ('text/html', 'application/xhtml+xml')):
        raise ValueError('HTMLページのURLを入力してください。')
    p = urlsplit(page['url'])
    robots_url = urlunsplit((p.scheme, p.netloc, '/robots.txt', '', ''))
    robots, error = None, None
    try:
        result = fetch(robots_url, deadline)
        if result['status'] in (404, 410):
            robots = ''
            error = 'robots.txtなし（HTTP 404/410）。ルールによる制限なしとして表示。'
        elif result['status'] == 200 and 'text/html' not in result['type'].lower(): robots = result['body']
        else: error = f'robots.txtを確認できませんでした（HTTP {result["status"]}）。'
    except (ValueError, OSError, http.client.HTTPException): error = 'robots.txtの取得に失敗しました。アクセス可否は不明です。'
    return analyze(page, robots, error)


def demo_audits():
    reports = {}
    for stage in ('before', 'after'):
        body = (ROOT / 'static' / 'demo' / f'{stage}.html').read_text()
        report = analyze(dict(url='https://demo.example/guide', body=body, robots_header=''), 'User-agent: *\nAllow: /')
        report.update(is_demo=True, demo_stage=stage)
        report['note'] = '検証用サンプルHTMLの診断です。実サイトの評価やAI検索での効果を示すものではありません。' + report['note']
        reports[stage] = report
    return reports


def load_sitemap(url):
    result = fetch(url)
    if result['status'] != 200:
        raise ValueError(f'サイトマップを取得できませんでした（HTTP {result["status"]}）。')
    return parse_sitemap(result['body'], result['url'], validate_url)


def error_message(error):
    return str(error) if isinstance(error, ValueError) else 'ページを取得できませんでした。URLやサイトのアクセス制限を確認してください。'


def audit_batch(urls):
    if not isinstance(urls, list) or not 1 <= len(urls) <= 5:
        raise ValueError('URLは1件から5件までの配列で指定してください。')
    unique = []
    for url in urls:
        p = validate_url(url)
        normalized = urlunsplit(p._replace(fragment=''))
        if normalized not in unique: unique.append(normalized)

    def run(url):
        result = dict(url=url)
        try:
            result['report'] = audit(url)
        except (ValueError, OSError, http.client.HTTPException) as error:
            result['error'] = error_message(error)
        result['at'] = datetime.now(timezone.utc).isoformat()
        return result

    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(run, unique))
    successful = [row['report'] for row in rows if 'report' in row]
    return dict(results=rows, summary=dict(total=len(rows), succeeded=len(successful),
        failed=len(rows) - len(successful),
        average_score=round(sum(r['score'] for r in successful) / len(successful), 1) if successful else None))


class Handler(BaseHTTPRequestHandler):
    def send(self, status, data, mime='application/json; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/api/demo':
            return self.send(200, json.dumps(demo_audits(), ensure_ascii=False).encode())
        assets = {'/demo/before': ('demo/before.html', 'text/html; charset=utf-8'), '/demo/after': ('demo/after.html', 'text/html; charset=utf-8'), '/demo.js': ('demo.js', 'text/javascript; charset=utf-8'), '/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/history.js': ('history.js', 'text/javascript; charset=utf-8'), '/report.js': ('report.js', 'text/javascript; charset=utf-8'), '/batch.js': ('batch.js', 'text/javascript; charset=utf-8'), '/sitemap.js': ('sitemap.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if self.path not in assets: return self.send(404, b'{}')
        name, mime = assets[self.path]
        self.send(200, (ROOT / 'static' / name).read_bytes(), mime)

    def do_POST(self):
        if self.path not in ('/api/audit', '/api/audit/batch', '/api/sitemap'): return self.send(404, b'{}')
        try:
            size = int(self.headers.get('Content-Length', '0'))
            limit = 16384 if self.path == '/api/audit/batch' else 4096
            if not 0 < size <= limit: raise ValueError('リクエストのサイズが不正です。')
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict): raise ValueError('JSONオブジェクトが必要です。')
            if self.path == '/api/sitemap': result = load_sitemap(payload.get('url'))
            else: result = audit_batch(payload.get('urls')) if self.path == '/api/audit/batch' else audit(payload.get('url'))
            self.send(200, json.dumps(result, ensure_ascii=False).encode())
        except (ValueError, OSError, http.client.HTTPException) as e:
            message = error_message(e)
            self.send(400, json.dumps({'error': message}, ensure_ascii=False).encode())


if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument('--host', default='127.0.0.1')
    args.add_argument('--port', type=int, default=8000)
    opts = args.parse_args()
    print(f'AEO Check: http://{opts.host}:{opts.port}', flush=True)
    ThreadingHTTPServer((opts.host, opts.port), Handler).serve_forever()

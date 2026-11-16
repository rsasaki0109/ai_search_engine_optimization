import json
import unittest
from unittest.mock import patch
import app

HTML = '''<html lang="ja"><head><title>診断サンプル</title><meta name="description" content="概要"><link rel="canonical" href="https://example.com/a"><script type="application/ld+json">{"@context":"https://schema.org","@type":"Article"}</script></head><body><h1>主題</h1><h2>回答</h2><p>''' + '正確な説明と出典。' * 40 + '</p></body></html>'

class AuditTests(unittest.TestCase):
    def page(self, body=HTML):
        return dict(body=body, url='https://example.com/a', robots_header='')

    def test_complete_page(self):
        result = app.analyze(self.page(), 'User-agent: *\nAllow: /')
        self.assertEqual(result['score'], 100)
        self.assertEqual(len(result['checks']), 9)
        self.assertTrue(all(b['allowed'] for b in result['bots']))
        self.assertNotIn('@type', result['excerpt'])

    def test_noindex_header_and_meta(self):
        for page in [dict(self.page(), robots_header='noindex'), self.page(HTML.replace('</head>', '<meta name="robots" content="none"></head>'))]:
            self.assertFalse(next(c for c in app.analyze(page)['checks'] if c['id'] == 'index')['passed'])

    def test_bots_are_separate_from_score(self):
        result = app.analyze(self.page(), 'User-agent: OAI-SearchBot\nDisallow: /\n\nUser-agent: *\nAllow: /')
        self.assertFalse(result['bots'][0]['allowed'])
        self.assertTrue(result['bots'][1]['allowed'])
        self.assertEqual(result['score'], 100)

    def test_invalid_jsonld_and_missing_content(self):
        result = app.analyze(self.page('<script type="application/ld+json">broken</script>'))
        self.assertFalse(next(c for c in result['checks'] if c['id'] == 'schema')['passed'])
        self.assertEqual(result['excerpt'], '')

    def test_failed_checks_have_actionable_templates(self):
        result = app.analyze(self.page('<meta name="robots" content="noindex">'))
        self.assertEqual(len(result['checks']), 9)
        for check in result['checks']:
            self.assertFalse(check['passed'])
            self.assertTrue(check['repair']['location'])
            self.assertTrue(check['repair']['note'])
        index = next(c for c in result['checks'] if c['id'] == 'index')
        self.assertIsNone(index['repair']['code'])
        self.assertIn('X-Robots-Tag', index['repair']['note'])

    def test_schema_template_escapes_script_end_and_preserves_title(self):
        title = '&lt;/script&gt;&lt;img src=x onerror=alert(1)&gt;'
        result = app.analyze(self.page(f'<title>{title}</title>'))
        code = next(c for c in result['checks'] if c['id'] == 'schema')['repair']['code']
        self.assertEqual(code.count('</script>'), 1)
        schema = json.loads(code.split('>\n', 1)[1].rsplit('\n</script>', 1)[0])
        self.assertEqual(schema['name'], '</script><img src=x onerror=alert(1)>')
        self.assertEqual(schema['@type'], 'WebPage')

    def test_canonical_template_quotes_url_and_removes_fragment(self):
        page = dict(self.page('<html></html>'), url='https://example.com/a?q="x"&page=2#section')
        checks = app.analyze(page)['checks']
        code = next(c for c in checks if c['id'] == 'canonical')['repair']['code']
        self.assertIn('q=&quot;x&quot;&amp;page=2', code)
        self.assertNotIn('#section', code)

    def test_passed_checks_do_not_recommend_edits(self):
        self.assertTrue(all('repair' not in c for c in app.analyze(self.page())['checks']))

    def test_valueless_html_attributes_do_not_crash(self):
        result=app.analyze(self.page('<html lang><meta name="description" content><link rel><script type></script><img alt><h1>主題</h1></html>'))
        self.assertEqual(len(result['checks']),9)
        self.assertFalse(next(c for c in result['checks'] if c['id']=='language')['passed'])

    def test_invalid_urls(self):
        for url in [None, 'file:///etc/passwd', 'https://user:pass@example.com', 'http://example.com:8080', 'https://example.com/\nfoo']:
            with self.subTest(url=url), self.assertRaises(ValueError): app.validate_url(url)

    @patch('app.socket.getaddrinfo')
    def test_private_destinations_blocked(self, dns):
        for ip in ['127.0.0.1', '10.0.0.1', '169.254.169.254', '::1', '::ffff:127.0.0.1']:
            dns.return_value = [(2, 1, 6, '', (ip, 80))]
            with self.subTest(ip=ip), self.assertRaises(ValueError): app.fetch('http://example.com')

    @patch('app.fetch')
    def test_missing_robots_and_failed_robots(self, fetch):
        page = dict(self.page(), status=200, type='text/html')
        fetch.side_effect = [page, {'status': 404}]
        self.assertEqual(len(app.audit('https://example.com')['bots']), 5)
        fetch.side_effect = [page, OSError('timeout')]
        result = app.audit('https://example.com')
        self.assertEqual(result['bots'], [])
        self.assertIsNotNone(result['robots_error'])

    @patch('app.fetch')
    def test_http_rejections_are_not_successful_audits_or_bot_allows(self, fetch):
        for status in [403,429,500]:
            fetch.return_value={'status':status}
            with self.subTest(status=status),self.assertRaises(ValueError):app.audit('https://example.com')
            fetch.side_effect=[dict(self.page(),status=200,type='text/html'),{'status':status}]
            result=app.audit('https://example.com')
            self.assertEqual(result['bots'],[])
            self.assertIn(str(status),result['robots_error'])
            fetch.side_effect=None

    @patch('app.socket.getaddrinfo')
    @patch('app.http.client.HTTPConnection')
    def test_redirect_to_private_destination(self, connection, dns):
        dns.side_effect = [[(2,1,6,'',('93.184.216.34',80))], [(2,1,6,'',('127.0.0.1',80))]]
        response = connection.return_value.getresponse.return_value
        response.status = 302
        response.getheader.return_value = 'http://127.0.0.1/'
        with self.assertRaises(ValueError): app.fetch('http://example.com')
        self.assertEqual(connection.call_count, 1)

if __name__ == '__main__': unittest.main()

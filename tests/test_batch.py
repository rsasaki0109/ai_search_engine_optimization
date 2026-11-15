import threading
import unittest
from unittest.mock import patch
import app


class BatchTests(unittest.TestCase):
    @patch('app.audit')
    def test_partial_failure_preserves_input_order_and_summary(self, audit):
        def run(url):
            if url.endswith('/bad'): raise ValueError('HTTP 404')
            return {'url':url,'score':80 if url.endswith('/a') else 60}
        audit.side_effect=run
        result=app.audit_batch(['https://example.com/a','https://example.com/bad','https://example.com/b'])
        self.assertEqual([r['url'].rsplit('/',1)[1] for r in result['results']], ['a','bad','b'])
        self.assertEqual(result['summary'],dict(total=3,succeeded=2,failed=1,average_score=70.0))
        self.assertEqual(result['results'][1]['error'],'HTTP 404')
        self.assertTrue(all('at' in r for r in result['results']))

    @patch('app.audit')
    def test_validates_whole_request_before_fetching(self, audit):
        for value in [None,'https://example.com',[],['https://example.com']*6,[None],['file:///etc/passwd'],['https://example.com','broken']]:
            with self.subTest(value=value),self.assertRaises(ValueError):app.audit_batch(value)
        audit.assert_not_called()

    @patch('app.audit',return_value={'score':50})
    def test_deduplicates_urls_and_fragments(self,audit):
        result=app.audit_batch(['https://example.com/a#one','https://example.com/a#two','https://example.com/a'])
        audit.assert_called_once_with('https://example.com/a')
        self.assertEqual(result['summary']['total'],1)

    @patch('app.audit',side_effect=OSError('private connection detail'))
    def test_all_failures_have_no_average_and_no_internal_error_leak(self,audit):
        result=app.audit_batch(['https://example.com/a'])
        self.assertIsNone(result['summary']['average_score'])
        self.assertEqual(result['summary']['failed'],1)
        self.assertNotIn('private connection detail',result['results'][0]['error'])

    @patch('app.audit')
    def test_at_most_three_jobs_run_concurrently(self,audit):
        barrier=threading.Barrier(3)
        lock=threading.Lock()
        active=0
        maximum=0
        def run(url):
            nonlocal active,maximum
            with lock:
                active+=1
                maximum=max(maximum,active)
            if int(url.rsplit('/',1)[1])<3:barrier.wait(timeout=3)
            with lock:active-=1
            return {'score':50}
        audit.side_effect=run
        result=app.audit_batch([f'https://example.com/{n}' for n in range(5)])
        self.assertEqual(maximum,3)
        self.assertEqual(result['summary']['succeeded'],5)

    def test_private_url_failure_does_not_prevent_other_results(self):
        with patch('app.socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',80))]):
            result=app.audit_batch(['http://127.0.0.1','http://localhost'])
        self.assertEqual(result['summary']['failed'],2)
        self.assertTrue(all('公開インターネット' in r['error'] for r in result['results']))

if __name__=='__main__':unittest.main()

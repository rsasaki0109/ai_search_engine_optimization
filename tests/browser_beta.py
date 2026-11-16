"""HTTP integration for public beta limits. No browser dependency or external fetches."""
import json
from pathlib import Path
import sys
import threading
import urllib.request
import urllib.error
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
from limits import RuntimeLimits


def main():
    limits=RuntimeLimits(jobs=1,per_minute=2)
    server=app.BetaServer(('127.0.0.1',0),app.Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    client=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def request(origin=None,body=b'{"url":"https://example.com"}'):
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        req=urllib.request.Request(base+'/api/audit',data=body,headers=headers)
        try:r=client.open(req)
        except urllib.error.HTTPError as e:r=e
        return r.status,dict(r.headers),r.read()
    try:
        with patch('app.RUNTIME',limits),patch('app.fetch') as fetch:
            def page(url,deadline=None):
                return dict(url=url,status=200,type='text/plain' if url.endswith('robots.txt') else 'text/html',body='User-agent: *\nAllow: /' if url.endswith('robots.txt') else '<title>Test</title>',robots_header='')
            fetch.side_effect=page
            assert client.open(base+'/healthz').status==200
            assert request('https://evil.test')[0]==403
            assert request(body=b'x'*4097)[0]==400
            assert request(base)[0]==200
            with limits.job():assert request(base)[0]==503
            status,headers,body=request(base)
            assert status==429 and headers['Retry-After']=='60'
            assert '利用上限' in json.loads(body)['error']
            assert client.open(base+'/api/demo').status==200
        # Inbound sockets are independently bounded.
        for _ in range(16):assert server.connections.acquire(timeout=2)
        try:
            try:client.open(base+'/healthz');raise AssertionError('capacity not enforced')
            except urllib.error.HTTPError as e:assert e.code==503
        finally:
            for _ in range(16):server.connections.release()
        print('Beta HTTP checks passed: origin, body limit, rate budget, job capacity, connection cap, health, demo availability')
    finally:server.shutdown();server.server_close()

if __name__=='__main__':main()

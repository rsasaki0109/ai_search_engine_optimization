"""Validated-IP connections, optionally through an environment HTTP proxy."""
import base64
import http.client
import socket
import ssl
from urllib.parse import unquote, urlsplit
from urllib.request import getproxies, proxy_bypass


class TLSTunnel(http.client.HTTPConnection):
    def __init__(self, *args, target_hostname, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_hostname = target_hostname

    def connect(self):
        super().connect()
        # CONNECT targets a pinned IP; SNI and certificate checks use the URL host.
        self.sock = ssl.create_default_context().wrap_socket(self.sock, server_hostname=self.target_hostname)


def connection(host, port, address, scheme, timeout):
    proxies = getproxies()
    proxy_url = proxies.get(scheme) or proxies.get('all')
    if proxy_url and not proxy_bypass(host):
        proxy = urlsplit(proxy_url)
        if proxy.scheme != 'http' or not proxy.hostname:
            raise ValueError('プロキシ接続はhttp://形式のHTTP CONNECTプロキシに対応しています。')
        cls = TLSTunnel if scheme == 'https' else http.client.HTTPConnection
        kwargs = {'target_hostname': host} if scheme == 'https' else {}
        conn = cls(proxy.hostname, proxy.port or 80, timeout=timeout, **kwargs)
        headers = {}
        if proxy.username is not None:
            auth = unquote(proxy.username) + ':' + unquote(proxy.password or '')
            headers['Proxy-Authorization'] = 'Basic ' + base64.b64encode(auth.encode()).decode('ascii')
        conn.set_tunnel(address, port, headers=headers)
        return conn
    cls = http.client.HTTPSConnection if scheme == 'https' else http.client.HTTPConnection
    conn = cls(host, port, timeout=timeout)
    conn._create_connection = lambda addr, timeout, source_address=None: socket.create_connection((address, port), timeout, source_address)
    return conn

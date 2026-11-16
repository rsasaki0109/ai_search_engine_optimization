import unittest
from unittest.mock import patch, Mock
import network

class NetworkTests(unittest.TestCase):
    @patch('network.socket.create_connection')
    @patch('network.getproxies',return_value={})
    def test_direct_connection_is_pinned(self,proxies,socket):
        conn=network.connection('example.com',443,'93.184.216.34','https',8)
        conn._create_connection(('example.com',443),8)
        socket.assert_called_once_with(('93.184.216.34',443),8,None)

    @patch('network.proxy_bypass',return_value=False)
    @patch('network.getproxies',return_value={'https':'http://proxy.test:8080'})
    def test_proxy_connect_targets_validated_ip(self,proxies,bypass):
        conn=network.connection('example.com',443,'93.184.216.34','https',8)
        self.assertEqual(conn.host,'proxy.test')
        self.assertEqual(conn._tunnel_host,'93.184.216.34')
        self.assertEqual(conn.target_hostname,'example.com')
        self.assertEqual(conn._tunnel_port,443)

    @patch('network.ssl.create_default_context')
    @patch('network.http.client.HTTPConnection.connect')
    def test_tls_uses_original_hostname_and_default_trust(self,connect,context):
        conn=network.TLSTunnel('proxy.test',8080,target_hostname='example.com')
        sock=Mock();conn.sock=sock
        conn.connect()
        context.return_value.wrap_socket.assert_called_once_with(sock,server_hostname='example.com')
        connect.assert_called_once()

    @patch('network.proxy_bypass',return_value=True)
    @patch('network.getproxies',return_value={'https':'http://proxy.test:8080'})
    def test_no_proxy_bypasses_proxy(self,proxies,bypass):
        conn=network.connection('example.com',443,'93.184.216.34','https',8)
        self.assertEqual(conn.host,'example.com')
        self.assertIsNone(conn._tunnel_host)

    @patch('network.proxy_bypass',return_value=False)
    @patch('network.getproxies',return_value={'http':'http://user:pass@proxy.test:8080'})
    def test_proxy_auth_is_tunnel_only(self,proxies,bypass):
        conn=network.connection('example.com',80,'93.184.216.34','http',8)
        self.assertEqual(conn._tunnel_host,'93.184.216.34')
        self.assertIn('Proxy-Authorization',conn._tunnel_headers)
        self.assertNotIn('Authorization',conn._tunnel_headers)

    @patch('network.proxy_bypass',return_value=False)
    @patch('network.getproxies',return_value={'https':'socks5://proxy.test:1080'})
    def test_unsupported_proxy_has_no_direct_fallback(self,proxies,bypass):
        with self.assertRaises(ValueError):network.connection('example.com',443,'93.184.216.34','https',8)

if __name__=='__main__':unittest.main()

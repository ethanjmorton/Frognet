import http.server
import socketserver
import urllib.request
import urllib.parse
import urllib.error
import traceback
import socket
import ssl
import select
import random

class AdvancedProxyHandler(http.server.BaseHTTPRequestHandler):
    timeout = 5

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    ]

    ALLOWED_DOMAINS = []  # Empty means all domains are allowed

    def do_CONNECT(self):
        try:
            dest_host, dest_port = self.path.split(":")
            dest_port = int(dest_port)

            with socket.create_connection((dest_host, dest_port)) as conn:
                self.send_response(200, "Connection Established")
                self.end_headers()

                # Use a fresh socket for the SSL/TLS connection
                with socket.create_connection((dest_host, dest_port)) as tls_conn:
                    with ssl.wrap_socket(tls_conn, server_side=False) as secure_conn:
                        self._forward_data(secure_conn, conn)
        except Exception as e:
            self._handle_error(f"CONNECT error: {e}")

    def do_GET(self):
        self._proxy_request()

    def do_POST(self):
        self._proxy_request()

    def _proxy_request(self):
        try:
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            target_url = query_params.get('url', [None])[0]

            if not target_url:
                self.send_error(400, "Bad Request: Missing 'url' parameter.")
                return

            if not target_url.startswith(('http://', 'https://')):
                self.send_error(400, "Bad Request: Invalid URL format.")
                return

            if self.ALLOWED_DOMAINS:
                domain = urllib.parse.urlparse(target_url).netloc
                if domain not in self.ALLOWED_DOMAINS:
                    self.send_error(403, "Forbidden: Domain not allowed.")
                    return

            req_headers = self._get_headers()
            req_headers['User-Agent'] = random.choice(self.USER_AGENTS)

            req = urllib.request.Request(target_url, headers=req_headers)

            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    self.send_response(response.status)
                    self._send_headers(response.getheaders())
                    self._stream_response(response)
            except urllib.error.HTTPError as e:
                self.send_response(e.code)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
            except urllib.error.URLError as e:
                self.send_error(502, f"Bad Gateway: {e.reason}")
        except Exception as e:
            self._handle_error(f"Proxy error: {e}")

    def _get_headers(self):
        headers = {}
        for key in self.headers:
            headers[key] = self.headers[key]

        headers['X-Forwarded-For'] = self.client_address[0]
        headers['Via'] = '1.1 proxy'

        return headers

    def _send_headers(self, response_headers):
        headers_to_remove = ['X-Frame-Options', 'Content-Security-Policy']
        for header, value in response_headers:
            if header not in headers_to_remove:
                self.send_header(header, value)
        self.end_headers()

    def _stream_response(self, response):
        try:
            while True:
                data = response.read(4096)
                if not data:
                    break
                self.wfile.write(data)
        except Exception as e:
            self._handle_error(f"Error streaming response: {e}")

    def _forward_data(self, source, destination):
        try:
            while True:
                rlist, _, _ = select.select([source, destination], [], [])
                if source in rlist:
                    data = source.recv(4096)
                    if not data:
                        break
                    destination.sendall(data)
                if destination in rlist:
                    data = destination.recv(4096)
                    if not data:
                        break
                    source.sendall(data)
        except Exception as e:
            self._handle_error(f"Error forwarding data: {e}")

    def _handle_error(self, message):
        traceback.print_exc()
        self.send_error(500, message)

PORT = 8000

with socketserver.TCPServer(("0.0.0.0", PORT), AdvancedProxyHandler) as httpd:
    print(f"Serving at port {PORT}")
    httpd.serve_forever()

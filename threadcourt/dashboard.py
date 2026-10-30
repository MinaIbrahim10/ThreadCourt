"""Read-only loopback dashboard; no execution/upload endpoints."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files


def serve(report, port=8765):
    page = files('threadcourt').joinpath('dashboard.html').read_bytes()
    data = json.dumps(report).encode()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ('/', '/report.json'):
                self.send_error(404)
                return
            body = data if self.path == '/report.json' else page
            self.send_response(200)
            self.send_header('Content-Type', 'application/json' if self.path == '/report.json' else 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'ThreadCourt dashboard: http://127.0.0.1:{port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

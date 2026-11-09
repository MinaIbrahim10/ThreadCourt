"""Read-only loopback dashboard; no execution/upload endpoints."""
import json
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files


def render_embedded(report):
    """Self-contained evidence viewer, without a server or network requests."""
    page = files('threadcourt').joinpath('dashboard.html').read_text(encoding='utf-8')
    data = json.dumps(report, ensure_ascii=True).replace('<', '\\u003c')
    embedded = '<script id="threadcourt-report" type="application/json">' + data + '</script>\n'
    return page.replace('<script>', embedded + '<script>', 1)


def render_notebook(report, height=1100):
    """Isolate the viewer from notebook CSS; no port proxy is required."""
    if type(height) is not int or not 300 <= height <= 3000:
        raise ValueError('Viewer height must be between 300 and 3000 pixels')
    page = html.escape(render_embedded(report), quote=True)
    return ('<iframe title="ThreadCourt evidence" sandbox="allow-scripts allow-downloads" '
            f'srcdoc="{page}" style="width:100%;height:{height}px;border:0"></iframe>')


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

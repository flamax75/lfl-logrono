"""Servidor local con lista cerrada de archivos publicos. Nunca sirve .env."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = {'/index.html', '/css/style.css', '/js/data.js', '/js/app.js', '/data/league.json', '/manifest.webmanifest', '/service-worker.js', '/assets/images/logo-lfl.png', '/assets/images/logo-papeo2.png'}


class PublicHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_head(self):
        path = unquote(urlsplit(self.path).path)
        if path == '/':
            self.path = '/index.html'
        elif path not in PUBLIC:
            self.send_error(404)
            return None
        if not (ROOT / path.lstrip('/')).resolve().is_relative_to(ROOT):
            self.send_error(404)
            return None
        return super().send_head()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    print('LFL local: http://127.0.0.1:8000 — Ctrl+C para detener.')
    try:
        ThreadingHTTPServer(('127.0.0.1', 8000), PublicHandler).serve_forever()
    except KeyboardInterrupt:
        pass

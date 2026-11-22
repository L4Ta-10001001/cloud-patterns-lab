#!/usr/bin/env python3
"""Aplicación heredada simulada para demostrar rehosting sin modificar código."""
import json
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self._json(200, {'status': 'ok'})
        elif self.path == '/':
            self._json(200, {
                'app': 'legacy-demo',
                'version': '1.0',
                'message': 'Aplicacion heredada funcionando',
                'hostname': socket.gethostname(),
            })
        else:
            self._json(404, {'error': 'not_found'})

    def _json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(host='0.0.0.0', port=8080):
    return ThreadingHTTPServer((host, port), AppHandler)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8080'))
    print(f'legacy-demo listening on :{port}', flush=True)
    create_server(port=port).serve_forever()

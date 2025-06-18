import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

EVENTS = []

class SaaSHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/events':
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get('Content-Length', 0))
        try:
            data = json.loads(self.rfile.read(length).decode('utf-8'))
        except Exception:
            self.send_response(400)
            self.end_headers()
            return
        EVENTS.append(data)
        self.send_response(201)
        self.end_headers()

    def do_GET(self):
        if self.path != '/events':
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(EVENTS).encode('utf-8'))

    def log_message(self, *a, **kw):
        pass

class SaaSServer:
    def __init__(self, host='0.0.0.0', port=8000):
        self.httpd = HTTPServer((host, port), SaaSHandler)
        self.thread = Thread(target=self.httpd.serve_forever)
        self.thread.daemon = True

    @property
    def server_address(self):
        return self.httpd.server_address

    def start(self):
        self.thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join()


def main():
    parser = argparse.ArgumentParser(description='Hume SaaS server')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    server = SaaSServer(args.host, args.port)
    print(f'Serving on {server.server_address[0]}:{server.server_address[1]}')
    server.start()
    try:
        while True:
            server.thread.join(1)
    except KeyboardInterrupt:
        pass
    server.stop()

if __name__ == '__main__':
    main()

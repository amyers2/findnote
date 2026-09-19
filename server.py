#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from config import load_config
from search import search_notes


class RequestHandler(BaseHTTPRequestHandler):
    config = None

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
            return

        if parsed.path == "/search":
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]

            print(f"Search query: {query}")

            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(query.encode())
            return

        self.send_response(404)
        self.end_headers()


def main():
    config = load_config()
    RequestHandler.config = config

    print(f"Loaded {len(config.get('collections', {}))} collections")

    server = HTTPServer(("0.0.0.0", 8000), RequestHandler)

    print("Server listening on port 8000")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

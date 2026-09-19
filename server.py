#!/usr/bin/env python3

import json

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from config import load_config
from search import (
    get_search_paths,
    notes_to_dicts,
    search_notes
)


class RequestHandler(BaseHTTPRequestHandler):
    config = None


    def handle_health(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")


    def send_json(self, data):
        response = json.dumps(data)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response.encode())))
        self.end_headers()

        self.wfile.write(response.encode())


    def handle_search(self, query):
        if not query:
            self.send_json([])
            return

        results = search_notes(
            get_search_paths(self.config),
            all_words=[query],
        )

        data = notes_to_dicts(results)
        
        self.send_json(data)


    def get_query(self, parsed):
        params = parse_qs(parsed.query)
        return params.get("q", [""])[0]


    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self.handle_health()
            return

        if parsed.path == "/search":
            query = self.get_query(parsed)
            self.handle_search(query)
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

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


#
# RequestHandler class definition
#
class RequestHandler(BaseHTTPRequestHandler):
    config = None

    def handle_collections(self):
        collections = [
            {
                "name": name,
            }
            for name in self.config.get("collections", {})
        ]

        self.send_json(collections)

    def handle_health(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def send_json(self, data, status=200):
        response = json.dumps(data, ensure_ascii=False)

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response.encode())))
        self.end_headers()

        self.wfile.write(response.encode())

    def handle_search(
            self, query, all_words=None, any_words=None,
            not_words=None, regex=None, collections=None,
            match_case=False, whole_word=False):

        if all_words is None:
            all_words = []

        if query:
            all_words = [query] + all_words

        results = search_notes(
            get_search_paths(self.config, collections),
            all_words=all_words,
            any_words=any_words,
            not_words=not_words,
            regex=regex,
            match_case=match_case,
            whole_word=whole_word
        )

        data = notes_to_dicts(results, self.config)

        self.send_json(data)

    def get_query(self, parsed):
        return parse_qs(parsed.query)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self.handle_health()
            return

        if parsed.path == "/collections":
            self.handle_collections()
            return

        if parsed.path == "/search":
            params = self.get_query(parsed)
            query = params.get("q", [""])[0]
            all_words = params.get("all", [])
            any_words = params.get("any", [])
            not_words = params.get("not", [])
            regex = params.get("re", [None])[0]
            match_case = params.get(
                "match_case",
                ["false"])[0].lower() == "true"
            whole_word = params.get(
                "whole_word",
                ["false"])[0].lower() == "true"

            collections = params.get("collection")
            try:
                self.handle_search(
                    query,
                    all_words,
                    any_words,
                    not_words,
                    regex,
                    collections,
                    match_case,
                    whole_word)
            except ValueError as e:
                self.send_json({"error": str(e)}, status=400)
            return

        self.send_response(404)
        self.end_headers()

# ==============================================================================


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

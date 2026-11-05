#!/usr/bin/env python3
"""Quiet, loopback-only permanent redirects for an existing tunnel."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("target", help="Destination HTTP(S) origin, without a path or query")
p.add_argument("--port", type=int, default=8094)
p.add_argument("--check", action="store_true")
a = p.parse_args()
target = urlsplit(a.target)
if (target.scheme not in {"http", "https"} or not target.netloc
        or target.username is not None or target.password is not None
        or target.path not in {"", "/"} or target.query or target.fragment
        or any(ord(c) < 32 for c in a.target) or not 1 <= a.port <= 65535):
    p.error("Expected an HTTP(S) origin and a valid port")
origin = f"{target.scheme}://{target.netloc}"


class Redirect(BaseHTTPRequestHandler):
    def redirect(self):
        path = self.path if self.path.startswith("/") else "/" + self.path
        self.send_response(308)
        self.send_header("Location", origin + path)
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = redirect

    def log_message(self, *_):
        pass  # Requested URLs can be private; never write access logs.


if not a.check:
    ThreadingHTTPServer(("127.0.0.1", a.port), Redirect).serve_forever()

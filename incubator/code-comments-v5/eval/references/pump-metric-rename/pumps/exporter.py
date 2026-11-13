"""Serve the station metrics over HTTP for Prometheus to scrape."""

import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from pumps.metrics import StationMetrics
from pumps.telemetry import apply_feed

PORT = 9410
METRICS = StationMetrics()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_error(404)
            return
        body = METRICS.render().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.end_headers()
        self.wfile.write(body)


def main():
    """Apply controller events from stdin in the background and serve /metrics on PORT."""
    threading.Thread(target=apply_feed, args=(METRICS, sys.stdin), daemon=True).start()
    HTTPServer(("", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()

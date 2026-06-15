"""Vercel handler — auth + dispatch."""
import os
import sys
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import run_job, JOBS

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        job   = (params.get("job")   or [""])[0]
        token = (params.get("token") or [""])[0]

        if not WEBHOOK_SECRET or token != WEBHOOK_SECRET:
            self._respond(401, {"ok": False, "error": "unauthorized"})
            return

        if job not in JOBS:
            self._respond(400, {"ok": False, "error": f"invalid job (use: {'|'.join(JOBS)})"})
            return

        try:
            run_job(job)
            self._respond(200, {"ok": True, "job": job})
        except Exception as e:
            self._respond(500, {"ok": False, "error": str(e)[:300]})

    def _respond(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

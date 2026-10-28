#!/usr/bin/env python3
"""Reverse proxy: gated player on /, MCP on /mcp, admin cookie export."""
import http.client
import re
import socket
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def target_for(path):
    if path.startswith("/mcp"):
        return ("127.0.0.1", 18012)
    return ("127.0.0.1", 9090)


def parse_cookies(header):
    cookies = {}
    for part in (header or "").split(";"):
        if "=" in part:
            key, value = part.strip().split("=", 1)
            cookies[key] = value
    return cookies


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        line = fmt % args
        line = re.sub(r"([?&](?:token|key|auth|code)=)[^&\s]+", r"\1***", line)
        sys.stderr.write("%s - %s\n" % (self.address_string(), line))

    def _send_text(self, status, text):
        data = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)

    def _admin_cookie(self):
        expected = os.environ.get("ADMIN_SECRET", "")
        if not expected or self.headers.get("X-Admin-Secret", "") != expected:
            self._send_text(403, "forbidden")
            return
        path = "/app/server/data/.netease_cred"
        if not os.path.exists(path):
            self._send_text(404, "cookie-not-set")
            return
        raw = open(path, encoding="utf-8").read().strip()
        if raw.startswith("MUSIC_U="):
            raw = raw.split("=", 1)[1]
        self._send_text(200, raw)

    def _player_allowed(self, parsed):
        expected = os.environ.get("MUSIC_WEB_TOKEN", "")
        if not expected:
            return True
        return parse_cookies(self.headers.get("Cookie", "")).get("music_web") == expected

    def _forward(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/health":
            for host, port in (("127.0.0.1", 9090), ("127.0.0.1", 18012)):
                try:
                    sock = socket.create_connection((host, port), timeout=2)
                    sock.close()
                except OSError:
                    self._send_text(503, "upstream unavailable")
                    return
            self._send_text(200, "ok")
            return
        if parsed.path == "/admin/cookie":
            self._admin_cookie()
            return
        if parsed.path == "/login-qr.png":
            token = urllib.parse.parse_qs(parsed.query).get("token", [""])[0]
            if token != os.environ.get("MUSIC_WEB_TOKEN", ""):
                self._send_text(403, "forbidden")
                return
            qr_path = "/app/server/data/login-qr.png"
            if not os.path.exists(qr_path):
                self._send_text(404, "qr not ready")
                return
            data = open(qr_path, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(data)
            return

        if parsed.path.startswith("/mcp"):
            required = os.environ.get("MCP_TOKEN", "")
            if not required:
                self._send_text(503, "MCP_TOKEN is not configured")
                return
            if self.headers.get("Authorization", "") != "Bearer " + required:
                self._send_text(401, "missing MCP bearer token")
                return
        else:
            expected = os.environ.get("MUSIC_WEB_TOKEN", "")
            if expected and not self._player_allowed(parsed):
                query = urllib.parse.parse_qs(parsed.query)
                if parsed.path == "/" and query.get("token", [""])[0] == expected:
                    self.send_response(302)
                    self.send_header("Location", "/#login")
                    self.send_header("Set-Cookie", "music_web=%s; Path=/; HttpOnly; Secure; SameSite=Lax" % expected)
                    self.send_header("Content-Length", "0")
                    self.send_header("Connection", "close")
                    self.end_headers()
                    return
                self._send_text(401, "open this player with its access link")
                return

        host, port = target_for(parsed.path)
        length = int(self.headers.get("Content-Length") or "0")
        body = self.rfile.read(length) if length else None
        headers = {}
        for key, value in self.headers.items():
            if key.lower() in ("host", "connection", "content-length", "transfer-encoding"):
                continue
            headers[key] = value
        if not parsed.path.startswith("/mcp"):
            # Never trust a client-supplied gateway header (case-insensitive in HTTP).
            headers = {k: v for k, v in headers.items() if k.lower() != "x-music-gateway"}
            headers["X-Music-Gateway"] = os.environ.get("MUSIC_GATEWAY_TOKEN", "music-gateway")

        conn = http.client.HTTPConnection(host, port, timeout=120)
        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            resp = conn.getresponse()
            self.send_response(resp.status)
            for key, value in resp.getheaders():
                if key.lower() in ("connection", "transfer-encoding", "content-length", "keep-alive"):
                    continue
                self.send_header(key, value)
            self.send_header("Connection", "close")
            self.end_headers()
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except Exception as error:
            sys.stderr.write("proxy error: %s\n" % error)
            try:
                self._send_text(502, "bad gateway")
            except Exception:
                pass
        finally:
            conn.close()

    do_GET = _forward
    do_POST = _forward
    do_PUT = _forward
    do_PATCH = _forward
    do_DELETE = _forward
    do_HEAD = _forward
    do_OPTIONS = _forward


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()

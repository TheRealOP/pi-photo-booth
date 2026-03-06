from __future__ import annotations

import mimetypes
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


WEB_DIR = Path(__file__).resolve().parent / "web"
LATEST_IMAGE = Path(__file__).resolve().parent / "sessions" / "latest.jpg"


class KioskHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/latest.jpg"):
            self._send_latest_image()
            return

        super().do_GET()

    def end_headers(self):
        if self.path.startswith("/latest.jpg"):
            self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def _send_latest_image(self):
        if not LATEST_IMAGE.exists():
            self.send_error(404, "No photo captured yet")
            return

        self.send_response(200)
        content_type = mimetypes.guess_type(str(LATEST_IMAGE))[0] or "image/jpeg"
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(LATEST_IMAGE.stat().st_size))
        self.end_headers()

        with LATEST_IMAGE.open("rb") as handle:
            self.wfile.write(handle.read())


def main():
    if not WEB_DIR.exists():
        raise SystemExit("Missing web/ directory. Run from repo root.")

    handler = partial(KioskHandler, directory=str(WEB_DIR))
    server = ThreadingHTTPServer(("0.0.0.0", 3000), handler)
    print("Kiosk server running at http://localhost:3000")
    server.serve_forever()


if __name__ == "__main__":
    main()

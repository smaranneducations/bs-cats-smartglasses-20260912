#!/usr/bin/env python3
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_DIRECTORY = PROJECT_ROOT / ".local" / "demo"


class DemoHandler(SimpleHTTPRequestHandler):
    def list_directory(self, path: str):  # type: ignore[no-untyped-def]
        self.send_error(404, "Directory listing is disabled")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the packaged demo on localhost only.")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    handler = partial(DemoHandler, directory=str(DEMO_DIRECTORY))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Serving packaged demo at http://127.0.0.1:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()

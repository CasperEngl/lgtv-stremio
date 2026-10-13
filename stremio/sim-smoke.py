#!/usr/bin/env python3
"""PROTOTYPE (issue #31): launch the Stremio desktop simulator against a throwaway loopback server.

Passes when the simulator opened a window, stremio-core's catalogue request arrived at this
machine through upstream's network client, the answer was parsed and drawn, and the process exited
0. The server here is not the stand-in server of docs/adr/0002: it answers every GET with one
invented catalogue and nothing else.

    python3 stremio/sim-smoke.py --binary <stremio-sim> --assets pkg --runtime <dir> --output <png>
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import threading
import time
import zlib

# Invented titles: nothing recorded from a real add-on.
CATALOGUE = {
    "metas": [
        {"id": f"tt000000{n}", "type": "movie", "name": name, "poster": None}
        for n, name in enumerate(["The Loopback Affair", "Stand-In", "Port Zero"], start=1)
    ]
}


class Handler(http.server.BaseHTTPRequestHandler):
    seen: list[tuple[str, str]] = []

    def do_GET(self) -> None:
        Handler.seen.append((self.path, self.headers.get("User-Agent", "")))
        body = json.dumps(CATALOGUE).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_: object) -> None:
        pass


def read_ppm(path: Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    magic, size, depth, pixels = data.split(b"\n", 3)
    if magic != b"P6" or depth != b"255":
        raise ValueError("the shot is not a binary PPM")
    width, height = (int(part) for part in size.split())
    if len(pixels) != width * height * 3:
        raise ValueError("the shot is truncated")
    return width, height, pixels


def write_png(path: Path, width: int, height: int, rgb: bytes) -> None:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))

    rows = b"".join(b"\x00" + rgb[y * width * 3 : (y + 1) * width * 3] for y in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()

    runtime = args.runtime.resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    shot = runtime / "shot.ppm"
    shot.unlink(missing_ok=True)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    stand_in = f"http://127.0.0.1:{server.server_address[1]}"

    env = os.environ.copy()
    env.update(
        PLXNATIVE_RUNTIME_DIR=str(runtime),
        PLXNATIVE_APP_DIR=str(args.assets.resolve(strict=True)),
        PLXNATIVE_WIN="1280x720",
        STREMIO_TV_STAND_IN=stand_in,
        STREMIO_TV_SIM_SHOT=str(shot),
    )
    events = runtime / "plxnative-events.log"
    started = time.monotonic()
    try:
        result = subprocess.run(
            [str(args.binary.resolve(strict=True))],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=args.timeout, check=False,
        )
    except subprocess.TimeoutExpired as error:
        print(error.stdout or "", file=sys.stderr)
        print(f"the simulator did not exit within {args.timeout}s", file=sys.stderr)
        return 1
    elapsed = time.monotonic() - started
    log = events.read_text(errors="replace") if events.is_file() else "(no event log)"

    failures = []
    if result.returncode != 0:
        failures.append(f"the simulator exited with {result.returncode}")
    if not Handler.seen:
        failures.append("no request reached the loopback server")
    elif not any(path.startswith("/v3-cinemeta.strem.io/catalog/") for path, _ in Handler.seen):
        failures.append(f"no Cinemeta catalogue request among {Handler.seen}")
    elif not all(agent.startswith("stremio-tv-prototype/") for _, agent in Handler.seen):
        failures.append(f"a request did not come from upstream's network client: {Handler.seen}")
    if f"Catalogue: {len(CATALOGUE['metas'])} titles; First: {CATALOGUE['metas'][0]['name']}" not in log:
        failures.append("the event log does not show the invented catalogue as loaded")
    if not failures:
        try:
            width, height, rgb = read_ppm(shot)
            if len(set(rgb[i : i + 3] for i in range(0, len(rgb), 3))) < 8:
                failures.append("the shot is nearly one colour: nothing was drawn")
            else:
                write_png(output, width, height, rgb)
        except (OSError, ValueError) as error:
            failures.append(f"no usable shot: {error}")
    if failures:
        print(result.stdout, file=sys.stderr)
        print(f"--- {events} ---\n{log}\n--- end ---", file=sys.stderr)
        for failure in failures:
            print(f"FAILED: {failure}", file=sys.stderr)
        return 1

    for line in log.splitlines():
        if "video driver" in line or "GL:" in line or "stremio-" in line:
            print(line)
    for path, agent in Handler.seen:
        print(f"request: GET {path} ({agent})")
    print(f"simulator smoke passed in {elapsed:.2f}s: {output} ({width}x{height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

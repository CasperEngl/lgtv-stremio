#!/usr/bin/env python3
"""
Relay between a television on the home network and one debrid stream.

The set is given only this relay's address. `/playurl.json` is the `plxnative-playurl` trigger
object for the picked stream, written onto the set over Developer Mode ssh; the app then reads the
file from `/stream`. The relay holds the Comet address (which carries the
debrid account key), picks a cached stream with a safe audio track, and passes the file through
from its direct link. Nothing that identifies the account reaches the television or this log.

    relay.py movie tt0133093 --bind <this-machine>
    relay.py series tt0903747:1:1 --match 1080p

What `/stream` owes the player (PlxNative `tests/serve_fixtures.py`, THE SPEC): `Range: bytes=<n>-`
answered with 206 and a body starting at byte n, and a `Content-Length` that is the length of THIS
response's body.
"""

import argparse
import json
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SAFE_AUDIO = ("eac3", "ac3", "aac")
FED_VIDEO = ("hevc", "h264")
ERROR_CLIP_MAX_SECONDS = 600
PROBE_SECONDS = 75
CHUNK = 256 * 1024
USER_AGENT = "Mozilla/5.0"


def log(line):
    print(line, file=sys.stderr, flush=True)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_):
        return None


def direct_link(playback_url):
    """Follow the add-on's playback address one hop to the debrid service's direct link."""
    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(playback_url, headers={"User-Agent": USER_AGENT, "Range": "bytes=0-0"})
    try:
        with opener.open(request, timeout=60):
            return playback_url
    except urllib.error.HTTPError as error:
        location = error.headers.get("Location")
        if error.code in (301, 302, 303, 307, 308) and location:
            return location
        raise


def probe(link):
    """Open the file and read its container and tracks. Returns None when it cannot be read."""
    command = ["timeout", str(PROBE_SECONDS), "ffprobe", "-v", "error", "-of", "json",
               "-show_format", "-show_streams", "-rw_timeout", "25000000", "-user_agent", USER_AGENT, link]
    done = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    return json.loads(done.stdout) if done.returncode == 0 else None


def frame_rate(track):
    numerator, _, denominator = (track.get("avg_frame_rate") or "0/1").partition("/")
    try:
        return round(float(numerator) / float(denominator or 1), 3)
    except (ValueError, ZeroDivisionError):
        return 0.0


def declaration(report):
    """The Load declaration for a probed file, or the reason a television cannot play it."""
    duration = float((report.get("format") or {}).get("duration") or 0)
    if duration < ERROR_CLIP_MAX_SECONDS:
        return None, "error clip"
    tracks = report.get("streams") or []
    video = next((t for t in tracks if t.get("codec_type") == "video"
                  and not (t.get("disposition") or {}).get("attached_pic")), None)
    if video is None or video.get("codec_name") not in FED_VIDEO:
        return None, f"video {video.get('codec_name') if video else 'missing'}"
    # The player feeds the FIRST audio track whose codec matches the declaration, so the first
    # safe audio track in file order is the one that will be heard.
    audio = next((t for t in tracks if t.get("codec_type") == "audio" and t.get("codec_name") in SAFE_AUDIO), None)
    if audio is None:
        return None, "no safe audio track"
    spec = {"vcodec": video["codec_name"], "acodec": audio["codec_name"], "fps": frame_rate(video)}
    dolby_vision = next((d for d in video.get("side_data_list") or [] if "dv_profile" in d), None)
    if dolby_vision:
        spec["dovi"] = {"profile": dolby_vision["dv_profile"],
                        "bl_compat": dolby_vision.get("dv_bl_signal_compatibility_id", 0),
                        "el_present": bool(dolby_vision.get("el_present_flag"))}
    spec["atmos"] = audio["codec_name"] == "eac3" and "atmos" in (audio.get("profile") or "").lower()
    summary = (f"{video['codec_name']} {video.get('width')}x{video.get('height')} "
               f"dv={spec.get('dovi', {}).get('profile', '-')} | "
               f"{audio['codec_name']} {audio.get('channels')}ch {(audio.get('tags') or {}).get('language', 'und')}")
    return spec, summary


class Picked:
    """The stream being relayed: its declaration, and a direct link that can be refreshed."""

    def __init__(self, playback_url, link, spec, size):
        self.playback_url, self.link, self.spec, self.size = playback_url, link, spec, size
        self.lock = threading.Lock()

    def refresh(self):
        with self.lock:
            self.link = direct_link(self.playback_url)
            return self.link


def pick(comet_base, kind, title, match, limit):
    """The first cached stream, in the add-on's order, that probes as playable."""
    request = urllib.request.Request(f"{comet_base}/stream/{kind}/{title}.json", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=90) as response:
        streams = json.load(response).get("streams", [])
    log(f"{len(streams)} streams for {kind} {title}")
    probed = 0
    for rank, stream in enumerate(streams, 1):
        release = (stream.get("behaviorHints") or {}).get("filename") or (stream.get("description") or "").split("\n")[0]
        if "url" not in stream or (match and match.lower() not in f"{stream.get('name')} {release}".lower()):
            continue
        if probed == limit:
            break
        probed += 1
        try:
            link = direct_link(stream["url"])
        except (urllib.error.URLError, TimeoutError) as error:
            log(f"#{rank} {release[:70]}: no direct link ({type(error).__name__})")
            continue
        report = probe(link)
        if report is None:
            log(f"#{rank} {release[:70]}: probe failed")
            continue
        spec, summary = declaration(report)
        if spec is None:
            log(f"#{rank} {release[:70]}: skipped, {summary}")
            continue
        size = int((report.get("format") or {}).get("size") or 0)
        log(f"#{rank} {release[:70]}: PICKED, {summary}, {size / 2**30:.1f} GB")
        return Picked(stream["url"], link, spec, size)
    return None


def handler_for(picked, public_base):
    class Relay(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_):
            pass

        def do_HEAD(self):
            self.do_GET(body=False)

        def do_GET(self, body=True):
            if self.path == "/playurl.json":
                payload = json.dumps({"url": f"{public_base}/stream", **picked.spec}, separators=(",", ":")).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                if body:
                    self.wfile.write(payload)
                log(f"{self.client_address[0]} asked what to play")
            elif self.path == "/stream":
                self.relay_stream(body)
            else:
                self.send_error(404)
            self.close_connection = True

        def open_upstream(self, range_header):
            headers = {"User-Agent": USER_AGENT}
            if range_header:
                headers["Range"] = range_header
            for attempt in (1, 2):
                try:
                    return urllib.request.urlopen(urllib.request.Request(picked.link, headers=headers), timeout=30)
                except urllib.error.HTTPError as error:
                    # A direct link expires; the add-on's playback address hands out a fresh one.
                    if attempt == 2 or error.code not in (401, 403, 404, 410):
                        raise
                    picked.refresh()
            raise AssertionError("unreachable")

        def relay_stream(self, body):
            range_header = self.headers.get("Range")
            try:
                upstream = self.open_upstream(range_header)
            except (urllib.error.URLError, TimeoutError) as error:
                log(f"{self.client_address[0]} stream {range_header or 'whole'}: upstream failed ({type(error).__name__})")
                self.send_error(502)
                return
            with upstream:
                self.send_response(upstream.status)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Accept-Ranges", "bytes")
                for name in ("Content-Length", "Content-Range"):
                    if upstream.headers.get(name):
                        self.send_header(name, upstream.headers[name])
                self.send_header("Connection", "close")
                self.end_headers()
                sent = 0
                try:
                    while body and (chunk := upstream.read(CHUNK)):
                        self.wfile.write(chunk)
                        sent += len(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                log(f"{self.client_address[0]} stream {range_header or 'whole'}: {upstream.status}, sent {sent / 2**20:.0f} MB")

    return Relay


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    parser.add_argument("kind", choices=("movie", "series"))
    parser.add_argument("title", help="IMDb id, with :season:episode for a series")
    parser.add_argument("--comet-url", type=Path, default=Path.home() / ".config/lgtv-stremio/comet-url-g5")
    parser.add_argument("--bind", required=True, help="this machine's address on the home network")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--match", help="only streams whose name or release name contains this")
    parser.add_argument("--probe-limit", type=int, default=12, help="how many streams to probe before giving up")
    args = parser.parse_args()

    comet_base = args.comet_url.read_text().strip().removesuffix("/manifest.json").rstrip("/")
    picked = pick(comet_base, args.kind, args.title, args.match, args.probe_limit)
    if picked is None:
        sys.exit("no playable cached stream found")
    public_base = f"http://{args.bind}:{args.port}"
    server = ThreadingHTTPServer((args.bind, args.port), handler_for(picked, public_base))
    log(f"relaying on {public_base}")
    server.serve_forever()


if __name__ == "__main__":
    main()

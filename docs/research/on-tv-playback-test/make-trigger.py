#!/usr/bin/env python3
"""Turn the stream prototype's `play` output into a `plxnative-playurl` trigger file.

The link carries account tokens, so this never prints it: it reads the prototype's saved output,
writes the trigger JSON to a mode-0600 file, and reports only what is safe to paste anywhere.

    (cd prototype && mise exec -- cargo run --release -- play movie <imdb id>) > /tmp/play.out
    grep -v '^mpv ' /tmp/play.out                    # the codecs and the audio track, no link
    make-trigger.py /tmp/play.out --vcodec hevc --acodec eac3 --out /tmp/plxnative-playurl
"""

import argparse
import json
import os
import re
import sys
from urllib.parse import urlsplit, urlunsplit

VCODECS = ("h264", "hevc", "av1", "vp9")
ACODECS = ("aac", "ac3", "eac3")


def link_from(text: str) -> tuple[int, str]:
    """The audio track number and the link from the prototype's `mpv --aid=N '<link>'` line."""
    found = re.search(r"^mpv --aid=(\d+) '(.+)'$", text, re.MULTILINE)
    if not found:
        sys.exit("no `mpv --aid=N '<link>'` line: the prototype picked no stream")
    return int(found.group(1)), found.group(2)


def with_port(link: str) -> str:
    """The link with its port spelled out: the app reads a missing port as 32400, not 443."""
    parts = urlsplit(link)
    if parts.scheme != "https" or not parts.hostname:
        sys.exit(f"expected an https link, got scheme `{parts.scheme}`")
    if parts.port is not None:
        return link
    return urlunsplit(parts._replace(netloc=f"{parts.hostname}:443"))


def main() -> None:
    args = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    args.add_argument("play_output", help="file holding the prototype's `play` output")
    args.add_argument("--vcodec", required=True, choices=VCODECS)
    args.add_argument("--acodec", required=True, choices=ACODECS)
    args.add_argument("--fps", type=float, default=0.0, help="source frame rate; 0 leaves it out")
    args.add_argument("--out", required=True, help="trigger file to write (mode 0600)")
    opts = args.parse_args()

    with open(opts.play_output, encoding="utf-8") as source:
        track, link = link_from(source.read())
    link = with_port(link)

    trigger = {"url": link, "vcodec": opts.vcodec, "acodec": opts.acodec}
    if opts.fps > 0:
        trigger["fps"] = opts.fps
    payload = json.dumps(trigger, separators=(",", ":"))
    if "'" in payload:
        sys.exit("the link holds an apostrophe, which the copy to the television cannot quote")

    handle = os.open(opts.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        out.write(payload)

    parts = urlsplit(link)
    print(f"wrote {opts.out}: {len(payload)} bytes, port {parts.port}, "
          f"vcodec {opts.vcodec}, acodec {opts.acodec}, fps {opts.fps or 'omitted'}")
    print(f"the prototype picked audio track {track}; the app plays the FIRST {opts.acodec} track")


if __name__ == "__main__":
    main()

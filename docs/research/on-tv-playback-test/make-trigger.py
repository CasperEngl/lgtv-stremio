#!/usr/bin/env python3
"""Turn the stream prototype's `play` or `streams --urls` output into a `plxnative-playurl` trigger file.

The link carries account tokens, so this never prints it: it reads the prototype's saved output,
writes the trigger JSON to a mode-0600 file, and reports only what is safe to paste anywhere.

    (cd prototype && mise exec -- cargo run --release -- play movie <imdb id>) > /tmp/play.out
    grep -v '^mpv ' /tmp/play.out                    # the codecs and the audio track, no link
    make-trigger.py /tmp/play.out --vcodec hevc --acodec eac3 --out /tmp/plxnative-playurl

Dolby Vision is declared with `--dovi-profile 8 --dovi-bl-compat 1` (the app declares it only with
`--vcodec hevc`, spelled so). `play` never picks a DTS track, so for one take the link from a saved
`streams <type> <id> --urls` listing instead: `--line N` names the listing's line, which must be
marked cached. The app feeds the first track whose codec equals `--acodec`, wherever it sits.
"""

import argparse
import json
import os
import re
import sys
from urllib.parse import urlsplit, urlunsplit

VCODECS = ("h264", "hevc", "av1", "vp9")
ACODECS = ("aac", "ac3", "eac3", "dts")


def link_from(text: str) -> tuple[int, str]:
    """The audio track number and the link from the prototype's `mpv --aid=N '<link>'` line."""
    found = re.search(r"^mpv --aid=(\d+) '([^']+)'$", text, re.MULTILINE)
    if not found:
        sys.exit("no `mpv --aid=N '<link>'` line: the prototype picked no stream")
    return int(found.group(1)), found.group(2)


def link_from_listing(text: str, number: int) -> str:
    """The link on line `number` of a `streams --urls` listing; only a cached stream is handed over."""
    lines = text.splitlines()
    if not 1 <= number <= len(lines):
        sys.exit(f"the listing has {len(lines)} lines, not {number}")
    line = lines[number - 1]
    if not line.endswith(" · cached"):
        sys.exit(f"line {number} is not marked cached; an uncached link can queue a download")
    found = re.search(r"(https://\S+)", line)
    if not found:
        sys.exit(f"line {number} holds no https link: was the listing made with --urls?")
    return found.group(1)


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
    args.add_argument("--line", type=int, default=0, help="take the link from this line of a `streams --urls` listing")
    args.add_argument("--dovi-profile", type=int, default=0, choices=(0, 5, 8), help="declare Dolby Vision; 0 leaves it out")
    args.add_argument("--dovi-bl-compat", type=int, default=1, help="base layer: 0 none (profile 5), 1 HDR10, 2 SDR, 4 HLG")
    args.add_argument("--out", required=True, help="trigger file to write (mode 0600)")
    opts = args.parse_args()

    with open(opts.play_output, encoding="utf-8") as source:
        text = source.read()
    track, link = (None, link_from_listing(text, opts.line)) if opts.line else link_from(text)
    link = with_port(link)

    trigger = {"url": link, "vcodec": opts.vcodec, "acodec": opts.acodec}
    if opts.fps > 0:
        trigger["fps"] = opts.fps
    if opts.dovi_profile:
        trigger["dovi"] = {"profile": opts.dovi_profile, "bl_compat": opts.dovi_bl_compat, "el_present": False}
    payload = json.dumps(trigger, separators=(",", ":"))
    if "'" in payload:
        sys.exit("the link holds an apostrophe, which the copy to the television cannot quote")

    handle = os.open(opts.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        out.write(payload)

    parts = urlsplit(link)
    print(f"wrote {opts.out}: {len(payload)} bytes, port {parts.port}, "
          f"vcodec {opts.vcodec}, acodec {opts.acodec}, fps {opts.fps or 'omitted'}, "
          f"dovi {trigger.get('dovi', 'omitted')}")
    if track is not None:
        print(f"the prototype picked audio track {track}")
    print(f"the app plays the FIRST {opts.acodec} track")


if __name__ == "__main__":
    main()

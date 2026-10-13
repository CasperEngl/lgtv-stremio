#!/usr/bin/env python3
"""Write a `plxnative-playurl` trigger for one line of the prototype's `streams --urls` output.

The link carries account tokens, so it is never printed: only what is safe to paste is reported.

    mk-trigger.py <streams-urls.out> <line number> <vcodec> <acodec> <out file>
"""
import json
import os
import re
import sys
from urllib.parse import urlsplit, urlunsplit

source, line_no, vcodec, acodec, out = sys.argv[1:6]
with open(source, encoding="utf-8") as handle:
    line = handle.read().split("\n")[int(line_no) - 1]
link = re.search(r"https://\S+", line).group(0)
parts = urlsplit(link)
if parts.port is None:  # the app reads a missing port as 32400
    link = urlunsplit(parts._replace(netloc=f"{parts.hostname}:443"))
payload = json.dumps({"url": link, "vcodec": vcodec, "acodec": acodec, "fps": 23.976}, separators=(",", ":"))
if "'" in payload:
    sys.exit("the link holds an apostrophe")
fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as handle:
    handle.write(payload)
print(f"wrote {out}: {len(payload)} bytes; {line.split(' · ', 1)[1]}")

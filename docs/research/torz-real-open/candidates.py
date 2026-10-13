#!/usr/bin/env python3
"""List StremThru Torz candidates from a saved `lgtv-stremio streams <type> <id> --urls` listing.

Opens nothing. Each link is reduced to the torrent hash's first 8 characters, the file index and
the filename, so the configuration segment never reaches the output.
Usage: candidates.py <listing.txt> <rows per section>
"""
import re
import sys
import urllib.parse as u

torz = []
comet_cached = set()
addon = ""
for line in open(sys.argv[1], encoding="utf-8"):
    if not line.startswith("  "):
        addon = line.split(":")[0]
        continue
    m = re.search(r"(https?://\S+)", line)
    if not m:
        continue
    path = u.urlsplit(m.group(1)).path
    rest = line[m.end():].strip(" ·\n")
    size = re.search(r"([\d.]+) GB", rest)
    cached = rest.endswith("cached")
    if "Comet" in addon:
        if cached and size:
            comet_cached.add(size.group(1))
        continue
    if "/stremio/torz/" not in path:
        continue
    parts = path.split("/_/strem/")[1].split("/")
    gb = float(size.group(1)) if size else None
    torz.append((cached, gb, parts[2][:8], parts[3], u.unquote(parts[4])[:70]))

for want in (True, False):
    rows = sorted((t for t in torz if t[0] == want), key=lambda t: (t[1] is None, t[1] or 0))
    print("CACHED" if want else "UNCACHED", len(rows))
    for _, gb, digest, index, name in rows[: int(sys.argv[2])]:
        also = " (Comet lists a cached file of this size)" if gb is not None and "%.1f" % gb in comet_cached else ""
        print(f"  {digest} idx={index} {gb} GB | {name}{also}")

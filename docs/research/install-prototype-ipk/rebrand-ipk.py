#!/usr/bin/env python3
"""PROTOTYPE (issue #24): give the placeholder package Rill's tile and splash without rebuilding it.

    rebrand-ipk.py <in.ipk> <artwork dir> <out.ipk>

`<artwork dir>` is `artwork-prototype/out/final/` on branch `wayfinder/rill-final-artwork`: it
holds `rill/icon.png` (80 px), `rill/largeIcon.png` (130 px) and `splash.png` (1920x1080). The
binary and the bundled libraries are copied through byte for byte and the app id stays, so the
result installs over the placeholder. Only the two icons, the splash and the descriptor's title,
tile colour and splash entry change. The container rules are the ones `stremio/mkipk.py` records.
"""
import gzip
import io
import json
import sys
import tarfile
from pathlib import Path

TITLE = "Rill prototype"
TILE_COLOUR = "#0c2330"  # the blue-black of the Rill tile; LG paints `iconColor` behind the icon


def ar_members(blob: bytes) -> dict:
    assert blob[:8] == b"!<arch>\n", "not an ar archive"
    out, at = {}, 8
    while at < len(blob):
        head = blob[at:at + 60]
        size = int(head[48:58])
        out[head[:16].decode().strip()] = blob[at + 60:at + 60 + size]
        at += 60 + size + size % 2
    return out


def ar(members: list) -> bytes:
    out = io.BytesIO(b"!<arch>\n")
    out.seek(0, io.SEEK_END)
    for name, blob in members:
        out.write(f"{name:<16}{0:<12}{0:<6}{0:<6}{'100644':<8}{len(blob):<10}".encode() + b"\x60\n")
        out.write(blob + (b"\n" if len(blob) % 2 else b""))
    return out.getvalue()


def main() -> int:
    src, art, dst = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    members = ar_members(src.read_bytes())
    swap = {
        "icon.png": (art / "rill/icon.png").read_bytes(),
        "largeIcon.png": (art / "rill/largeIcon.png").read_bytes(),
    }
    splash = (art / "splash.png").read_bytes()

    raw = io.BytesIO()
    with tarfile.open(fileobj=io.BytesIO(members["data.tar.gz"]), mode="r:gz") as old, \
            tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as new:
        for info in old:
            blob = old.extractfile(info).read() if info.isfile() else None
            name = Path(info.name).name
            in_app = "/applications/" in info.name and Path(info.name).parent.parent.name == "applications"
            if in_app and name in swap:
                blob = swap[name]
            elif in_app and name == "appinfo.json":
                appinfo = json.loads(blob)
                appinfo.update(title=TITLE, iconColor=TILE_COLOUR, bgColor=TILE_COLOUR,
                               splashBackground="splash.png")
                blob = (json.dumps(appinfo, indent=2) + "\n").encode()
            elif name == "packageinfo.json":
                package = json.loads(blob)
                package["loc_name"] = TITLE
                blob = (json.dumps(package, indent=4) + "\n").encode()
            if blob is not None:
                info.size = len(blob)
            new.addfile(info, io.BytesIO(blob) if blob is not None else None)
            if in_app and name == "largeIcon.png":
                extra = tarfile.TarInfo(str(Path(info.name).with_name("splash.png")))
                extra.size, extra.mode = len(splash), 0o644
                extra.uname = extra.gname = "root"
                new.addfile(extra, io.BytesIO(splash))
    data = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=data, mtime=0, compresslevel=9) as gz:
        gz.write(raw.getvalue())

    dst.write_bytes(ar([
        ("debian-binary", members["debian-binary"]),
        ("control.tar.gz", members["control.tar.gz"]),
        ("data.tar.gz", data.getvalue()),
    ]))
    print(f"wrote {dst} ({dst.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

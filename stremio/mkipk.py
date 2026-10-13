#!/usr/bin/env python3
"""PROTOTYPE (issue #15): package a staged application directory as a webOS .ipk.

    mkipk.py --id <app id> --version <x.y.z> --root <dir holding usr/palm/applications/<id>> --out <ipk>

Upstream's `ci/mkipk.py` builds the same container but reads PlxNative's descriptor, flavours and
storage service, so the Stremio package has its own. The format rules are the ones that file
records: an `ar` archive whose member names carry no trailing slash (LG's installer looks the
names up exactly), a `packageinfo.json` beside the application directory (without it an install
registers nothing), and fixed owners and times so one commit gives one sha256.
"""
import argparse
import gzip
import io
import json
import sys
import tarfile
from pathlib import Path


def targz(src, extra: dict) -> bytes:
    """Tar and gzip `src`'s contents (or nothing, when `src` is None) plus the in-memory `extra`."""
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as tf:
        for path in sorted(src.rglob("*") if src else [], key=lambda p: p.relative_to(src).as_posix()):
            info = tf.gettarinfo(str(path), arcname=path.relative_to(src).as_posix())
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = "root"
            info.mode = 0o755 if path.is_dir() or path.stat().st_mode & 0o111 else 0o644
            if info.isfile():
                with open(path, "rb") as fh:
                    tf.addfile(info, fh)
            else:
                tf.addfile(info)
        for name, blob in sorted(extra.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(blob), 0o644
            info.uname = info.gname = "root"
            tf.addfile(info, io.BytesIO(blob))
    out = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=out, mtime=0, compresslevel=9) as gz:
        gz.write(raw.getvalue())
    return out.getvalue()


def ar(members: list) -> bytes:
    out = io.BytesIO(b"!<arch>\n")
    out.seek(0, io.SEEK_END)
    for name, blob in members:
        out.write(f"{name:<16}{0:<12}{0:<6}{0:<6}{'100644':<8}{len(blob):<10}".encode() + b"\x60\n")
        out.write(blob + (b"\n" if len(blob) % 2 else b""))
    return out.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    app_dir = args.root / "usr/palm/applications" / args.id
    if not app_dir.is_dir():
        sys.exit(f"nothing staged at {app_dir}")
    appinfo = {
        "id": args.id,
        "version": args.version,
        "vendor": "placeholder",
        "type": "native",
        "main": "stremio-tv",
        "title": "Stremio prototype",
        "icon": "icon.png",
        "largeIcon": "largeIcon.png",
        "nativeLifeCycleInterfaceVersion": 2,
        "requiredMemory": 160,
    }
    (app_dir / "appinfo.json").write_text(json.dumps(appinfo, indent=2) + "\n")
    package_dir = args.root / "usr/palm/packages" / args.id
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "packageinfo.json").write_text(json.dumps({
        "app": args.id,
        "id": args.id,
        "loc_name": appinfo["title"],
        "package_format_version": 2,
        "vendor": appinfo["vendor"],
        "version": args.version,
    }, indent=4) + "\n")

    kib = (sum(p.stat().st_size for p in args.root.rglob("*") if p.is_file()) + 1023) // 1024
    control = "\n".join([
        f"Package: {args.id}",
        f"Version: {args.version}",
        "Section: misc",
        "Priority: optional",
        "Architecture: arm",
        f"Installed-Size: {kib}",
        "Maintainer: placeholder <placeholder@example.com>",
        "Description: Stremio prototype",
        "webOS-Package-Format-Version: 2",
        "webOS-Packager-Version: stremio/mkipk.py",
    ]) + "\n"
    args.out.write_bytes(ar([
        ("debian-binary", b"2.0\n"),
        ("control.tar.gz", targz(None, {"control": control.encode()})),
        ("data.tar.gz", targz(args.root, {})),
    ]))
    print(f"wrote {args.out} ({args.out.stat().st_size} bytes), Installed-Size {kib} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())

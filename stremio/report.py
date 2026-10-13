#!/usr/bin/env python3
"""PROTOTYPE (issue #15): the figures the ticket asks for, as a Markdown report on stdout.

Binary and package sizes, where the linked bytes come from by crate (symbol sizes from `nm` on the
unstripped binary), and the third-party package count, counted with upstream's own functions
(`ci/check-build-budgets.py`) so the two numbers compare. Upstream's budget is printed for scale
and never enforced here.
"""
import argparse
import collections
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The crates that exist for Plex: its API, stores, sign-in, telemetry, and the screens and shared
# widgets drawn over them.
PLEX_SIDE = {"plx_plex", "plx_data", "plx_session", "plx_telemetry", "plx_appkit", "plx_screens"}
CRATE = re.compile(r"\b([a-z][a-z0-9_]*)::")


def budgets_module():
    spec = importlib.util.spec_from_file_location("budgets", ROOT / "ci/check-build-budgets.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def symbol_bytes(nm: str, binary: str) -> collections.Counter:
    """Bytes of defined symbols per crate. A generic's bytes go to the first crate its name spells."""
    out = subprocess.run([nm, "-S", "-C", "--defined-only", binary], check=True,
                         capture_output=True, text=True).stdout
    sizes = collections.Counter()
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) < 4 or parts[2].lower() not in "tdrb":
            continue
        found = CRATE.search(parts[3])
        sizes[found.group(1) if found else "(C and unnamed)"] += int(parts[1], 16)
    return sizes


def main() -> int:
    ap = argparse.ArgumentParser()
    for name in ("nm", "profile", "binary", "stripped", "ipk", "toolchain"):
        ap.add_argument(f"--{name}", required=True)
    args = ap.parse_args()
    budgets = budgets_module()
    limits = json.loads((ROOT / "ci/build-budgets.json").read_text())["budgets"]

    stripped = Path(args.stripped).stat().st_size
    print(f"## Stremio prototype build report (cargo profile `{args.profile}`)\n")
    print("| Measure | Value |\n|---|---|")
    print(f"| Stripped ARM binary, as packaged | {stripped:,} B |")
    print(f"| Unstripped ARM binary | {Path(args.binary).stat().st_size:,} B |")
    print(f"| `.ipk` (binary, FFmpeg, libass, icons, licences; no fonts) | {Path(args.ipk).stat().st_size:,} B |")
    upstream = limits["binary_bytes"]
    print(f"| Upstream's stripped binary, for scale (measured {upstream['measured_on']}, limit {upstream['limit']:,} B) "
          f"| {upstream['measured']:,} B |")

    # The demuxer is only reachable through a started player, so its FFmpeg entry names in the
    # binary are the witness that the player was linked and not optimised away.
    demuxer = b"avformat_open_input" in Path(args.stripped).read_bytes()
    print(f"| Player and demuxer linked in | {'yes' if demuxer else 'NO'} |")

    trees = budgets.cargo_trees(ROOT / "stremio", args.toolchain, False)
    ours = budgets.tree_packages(trees["all"], ROOT)
    theirs = budgets.tree_packages(
        budgets.cargo_trees(ROOT / "rust-modules", args.toolchain, True)["all"], ROOT)
    print(f"| Third-party packages compiled for ARM (normal and build edges) | {len(ours)} |")
    print(f"| of which upstream's top crate also compiles (`--no-default-features`) | {len(ours & theirs)} of its {len(theirs)} |")
    print(f"| of which only the Stremio crate brings | {len(ours - theirs)} |")

    sizes = symbol_bytes(args.nm, args.binary)
    total = sum(sizes.values())
    plex = sum(size for crate, size in sizes.items() if crate in PLEX_SIDE)
    print(f"\nSymbol bytes by crate, unstripped binary: {total:,} B named in all; "
          f"Plex-side crates ({', '.join(sorted(PLEX_SIDE))}) {plex:,} B; "
          f"`plx_media` {sizes['plx_media']:,} B; `stremio_core` {sizes['stremio_core']:,} B.\n")
    print("| Crate | Symbol bytes |\n|---|---|")
    for crate, size in sizes.most_common(25):
        print(f"| `{crate}` | {size:,} |")
    print(f"\nOnly in the Stremio crate's graph: {', '.join(sorted(name for name, _ in ours - theirs))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

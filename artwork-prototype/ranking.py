#!/usr/bin/env python3
"""PROTOTYPE, throwaway: every setting of the splash word from rounds 5 to 8 on one sheet, in the
agent's order of preference (best first). The order is an opinion formed from these renders on a
computer screen, offered to the owner on issue 32; it decides nothing.

Run: python3 artwork-prototype/ranking.py
     (needs ImageMagick's magick and the splash files rounds 5 to 8 wrote; writes
     artwork-prototype/out/ranking/sheet.png)
"""
import pathlib
import subprocess

HERE = pathlib.Path(__file__).parent
OUT = HERE / "out" / "ranking"
ROUND = {"t": "round5", "u": "round6", "v": "round7", "w": "round8"}
ORDER = [
    ("v2", "Fredoka"), ("v1", "Comfortaa"), ("u3", "Unbounded"), ("u1", "Fraunces"),
    ("t2", "Inter Bold, tailed l"), ("v3", "Quicksand"), ("w7", "Playfair Display italic"),
    ("w1", "Outfit"), ("v4", "Baloo 2"), ("u5", "Instrument Serif italic"),
    ("u2", "Bricolage Grotesque"), ("v10", "Space Grotesk"), ("w3", "Tilt Warp"),
    ("v5", "Righteous"), ("w2", "Sora"), ("w6", "DM Serif Display"), ("v8", "Gloock"),
    ("t3", "Inter Regular, tailed l"), ("t5", "Noto Sans CJK KR"), ("w5", "Orbitron"),
    ("v9", "Audiowide"), ("v6", "Pacifico"), ("w10", "Caveat"), ("t4", "Inter Bold, capitals"),
    ("t1", "Inter Bold"), ("v7", "Kaushan Script"), ("w8", "Lobster"), ("u4", "Syne"),
    ("w9", "Sacramento"), ("w4", "Poiret One"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cmd = ["magick", "montage", "-font", str(HERE.parent / "pkg" / "appfont.ttf"),
           "-pointsize", "15", "-fill", "#c9ced6", "-background", "#15171c"]
    for rank, (key, name) in enumerate(ORDER, 1):
        src = HERE / "out" / ROUND[key[0]] / f"splash-{key}.png"
        # The word at real pixel size: a 320x170 window of the 1920x1080 splash.
        cmd += ["-label", f"{rank}  {key.upper()} {name}", f"{src}[320x170+800+625]"]
    cmd += ["-tile", "5x", "-geometry", "+8+8", str(OUT / "sheet.png")]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()

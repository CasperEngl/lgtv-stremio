#!/usr/bin/env python3
"""PROTOTYPE, throwaway: the splash word "Rill" in ten further faces from outside the package.

Round 8 of "Settle Rill's final colours, typeface and mark size" (issue 32). Rounds 6 and 7 showed
fifteen outside faces and the owner asked for more. This round draws one sheet:

  splashes.png  two rows of five: geometric and display faces above, serifs and scripts below,
                each as a whole splash and as a crop of the word at real pixel size.

The ten faces come from github.com/google/fonts at one pinned commit, each under the SIL Open
Font License 1.1 (read from the OFL.txt beside each file at that commit). Orbitron, DM Serif
Display ("Source"), Playfair Display, Lobster and Sacramento declare a Reserved Font Name, which
binds a modified font, not a word drawn with the font. The script downloads them into
~/.cache/rill-artwork-prototype/fonts/ and checks each against the sha256 below; no font file is
added to the repository.

Run: python3 artwork-prototype/round8.py
     (needs rsvg-convert, pango-view, ImageMagick's magick and, the first time, the network;
     writes artwork-prototype/out/round8/)

Nothing here is cut for the package: pkg/ and assets/ are upstream's and stay unedited.
"""
import base64
import hashlib
import os
import pathlib
import subprocess
import tempfile
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).parent
OUT = HERE / "out" / "round8"
PKG = HERE.parent / "pkg"
CACHE = pathlib.Path(os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache"))
FONTS = CACHE / "rill-artwork-prototype" / "fonts"
GOOGLE_FONTS = "https://raw.githubusercontent.com/google/fonts/66928797f271fed5ee428544e7229685e2d90127/ofl/"
FONT = "Inter"
BG, INK = "#071a24", "#4fd8c4"  # round 4's guesses, unchanged this round

WAVE = "C105 {u} 150 {u} 200 {y} S295 {v} 340 {y}"


def wave(y, amp=42, x0=60):
    return f"M{x0} {y} " + WAVE.format(y=y, u=y - amp, v=y + amp)


# Round 4's "play-tidy", unchanged.
MARK = f"""
  <path d="M124 70 L330 200 L124 330 Z" fill="{INK}" stroke="{INK}" stroke-width="40"
        stroke-linejoin="round"/>
  <g fill="none" stroke="{BG}" stroke-width="24">
    <path d="{wave(160, 30, 30)} S390 130 420 160"/>
    <path d="{wave(240, 30, 30)} S390 210 420 240"/>
  </g>"""

# Path under google/fonts' ofl/ and the file's sha256.
DOWNLOADS = {
    "outfit/Outfit[wght].ttf":
        "fc7287273e66929776e2ba54f144fe699080bec29f61bf649d70d871468aeade",
    "sora/Sora[wght].ttf":
        "84ff7096ae3ec6c8be47d906d1a0ba4de7f2ce78c615275c77301964a316e16c",
    "tiltwarp/TiltWarp[XROT,YROT].ttf":
        "e650320e405c220853184fa20a60a812f3f0275c3a1b2d1769409ad1cb4bfca5",
    "poiretone/PoiretOne-Regular.ttf":
        "457f2d03263f58e5a6dbcc1b607b10dff6581e7cf9c4ebdf330ec3e6772a3558",
    "orbitron/Orbitron[wght].ttf":
        "f42db2dd16e642258e35782916eceb1dcdbea06fb958d77ad71dc5963587e8fd",
    "dmserifdisplay/DMSerifDisplay-Regular.ttf":
        "8cc3643535edf039aa5d95440a8542735e9197e4f4b8d9303e980fefbf5ab616",
    "playfairdisplay/PlayfairDisplay-Italic[wght].ttf":
        "a5e26dc5e2e77fb2803a0bf02fd4f81ee136ec8dea863ccdb0c59a263b21378b",
    "lobster/Lobster-Regular.ttf":
        "d6568e697fd50cedc0be04d8aae4127fe95add607e7bff954ca88604be80c205",
    "sacramento/Sacramento-Regular.ttf":
        "9341fda10adbfeb7efc94302b34507a3e227d7e7f5c432df3f5ac8753ff73d24",
    "caveat/Caveat[wght].ttf":
        "0bdb6b660482d31531b3945849fba5916b3ef8695da7024a9e6b9ee3c4157988",
}

WORD_PX, WORD_SPACING, WORD_BASELINE = 92, 10, 748  # round 4's guesses, unchanged this round

# The splash word: (label, note, pango font with the size in it, letter spacing in px). The
# scripts join their letters, so they take no added spacing.
WORDS = {
    "w1": ("W1 Outfit", "weight 700", f"Outfit {WORD_PX} @wght=700", WORD_SPACING),
    "w2": ("W2 Sora", "weight 700", f"Sora {WORD_PX} @wght=700", WORD_SPACING),
    "w3": ("W3 Tilt Warp", "one weight", f"Tilt Warp {WORD_PX}", WORD_SPACING),
    "w4": ("W4 Poiret One", "one weight", f"Poiret One {WORD_PX}", WORD_SPACING),
    "w5": ("W5 Orbitron", "weight 700", f"Orbitron {WORD_PX} @wght=700", WORD_SPACING),
    "w6": ("W6 DM Serif Display", "one weight", f"DM Serif Display {WORD_PX}", WORD_SPACING),
    "w7": ("W7 Playfair Display", "italic, weight 700",
           f"Playfair Display Italic {WORD_PX} @wght=700", WORD_SPACING),
    "w8": ("W8 Lobster", "script, no added spacing", f"Lobster {WORD_PX}", 0),
    "w9": ("W9 Sacramento", "script, no added spacing", f"Sacramento {WORD_PX}", 0),
    "w10": ("W10 Caveat", "handwriting, weight 700, no added spacing",
            f"Caveat {WORD_PX} @wght=700", 0),
}
PER_ROW = 5

ENV = dict(os.environ)


def fetch_fonts():
    FONTS.mkdir(parents=True, exist_ok=True)
    for path, want in DOWNLOADS.items():
        dest = FONTS / pathlib.PurePosixPath(path).name
        if not dest.exists():
            with urllib.request.urlopen(GOOGLE_FONTS + urllib.parse.quote(path)) as r:
                dest.write_bytes(r.read())
        got = hashlib.sha256(dest.read_bytes()).hexdigest()
        if got != want:
            raise SystemExit(f"{dest}: sha256 {got}, expected {want}")


def svg(inner, w, h, box):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{box}">'
        f"{inner}</svg>\n"
    )


def word_image(key, tmp):
    """The splash word as a PNG trimmed to its ink, drawn by pango. Returns (data URI, w, h)."""
    _, _, font, spacing = WORDS[key]
    span = f"letter_spacing='{spacing * 1024}'"
    raw, cut = tmp / f"{key}-raw.png", tmp / f"{key}.png"
    subprocess.run(
        ["pango-view", "--no-display", "--markup", f"--font={font}", "--dpi=72", "--margin=40",
         "--background=transparent", f"--foreground={INK}", f"--text=<span {span}>Rill</span>",
         "-o", str(raw)],
        check=True, env=ENV,
    )
    subprocess.run(["magick", str(raw), "-trim", "+repage", str(cut)], check=True)
    w, h = subprocess.run(
        ["magick", "identify", "-format", "%w %h", str(cut)],
        check=True, capture_output=True, text=True,
    ).stdout.split()
    return "data:image/png;base64," + base64.b64encode(cut.read_bytes()).decode(), int(w), int(h)


def splash(word):
    """1920x1080: the field edge to edge, the mark in the middle at round 4's size, and the word's
    ink centred under it with its foot on round 4's baseline."""
    uri, w, h = word
    return (
        f'<rect width="1920" height="1080" fill="{BG}"/>'
        + f'<g transform="translate(800 300) scale(0.8)">{MARK}</g>'
        + f'<image x="{960 - w / 2}" y="{WORD_BASELINE - h}" width="{w}" height="{h}" href="{uri}"/>'
    )


def label(x, y, text, size=15, fill="#c9ced6", weight=400):
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}">{text}</text>'
    )


COL, THUMB_H, CROP_H = 320, 169, 190
ROW_H = 60 + THUMB_H + 50 + CROP_H + 30
SHEET_W, SHEET_H = COL * PER_ROW, ROW_H * -(-len(WORDS) // PER_ROW)


def splash_sheet(words):
    """One cell per face: the whole splash small, then the word cropped at real pixel size."""
    out = [f'<rect width="{SHEET_W}" height="{SHEET_H}" fill="#15171c"/>']
    for i, key in enumerate(WORDS):
        name, source, *_ = WORDS[key]
        x, y = (i % PER_ROW) * COL + 10, (i // PER_ROW) * ROW_H
        out.append(label(x, y + 28, name, 18, "#ffffff", 700))
        out.append(label(x, y + 48, source, 12, "#8b929e"))
        out.append(f'<svg x="{x}" y="{y + 60}" width="{COL - 20}" height="{THUMB_H}" '
                   f'viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid slice">'
                   f"{splash(words[key])}</svg>")
        out.append(label(x, y + 60 + THUMB_H + 32, "the word at real size", 12, "#8b929e"))
        # A window of the real splash, 1:1, centred on the word.
        cx, cy = 960 - (COL - 20) / 2, WORD_BASELINE - 125
        out.append(f'<svg x="{x}" y="{y + 60 + THUMB_H + 50}" width="{COL - 20}" height="{CROP_H}" '
                   f'viewBox="{cx} {cy} {COL - 20} {CROP_H}">{splash(words[key])}</svg>')
    return svg("".join(out), SHEET_W, SHEET_H, f"0 0 {SHEET_W} {SHEET_H}")


def render(name, markup, w, h):
    src = OUT / f"{name}.svg"
    src.write_text(markup)
    subprocess.run(
        ["rsvg-convert", "-w", str(w), "-h", str(h), "-o", str(OUT / f"{name}.png"), str(src)],
        check=True, env=ENV,
    )


def main():
    fetch_fonts()
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t)
        # Only the package's fonts and the ten downloads exist for this run.
        conf = tmp / "fonts.conf"
        conf.write_text(
            '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd">'
            f"<fontconfig><dir>{PKG.resolve()}</dir><dir>{FONTS}</dir>"
            f"<cachedir>{tmp}/cache</cachedir></fontconfig>"
        )
        ENV["FONTCONFIG_FILE"] = str(conf)
        words = {key: word_image(key, tmp) for key in WORDS}
        for key in WORDS:
            render(f"splash-{key}", svg(splash(words[key]), 1920, 1080, "0 0 1920 1080"), 1920, 1080)
        render("splashes", splash_sheet(words), SHEET_W, SHEET_H)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""PROTOTYPE, throwaway: the splash word "Rill" in ten more faces from outside the package.

Round 7 of "Settle Rill's final colours, typeface and mark size" (issue 32). Round 6 showed five
outside faces and the owner asked for more. This round draws one sheet:

  splashes.png  two rows of five: round and soft faces above, scripts and display faces below,
                each as a whole splash and as a crop of the word at real pixel size.

The ten faces come from github.com/google/fonts at one pinned commit, each under the SIL Open
Font License 1.1 (read from the OFL.txt beside each file at that commit). Comfortaa, Quicksand,
Righteous, Kaushan Script and Audiowide declare a Reserved Font Name, which binds a modified
font, not a word drawn with the font. The script downloads them into
~/.cache/rill-artwork-prototype/fonts/ and checks each against the sha256 below; no font file is
added to the repository.

Run: python3 artwork-prototype/round7.py
     (needs rsvg-convert, pango-view, ImageMagick's magick and, the first time, the network;
     writes artwork-prototype/out/round7/)

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
OUT = HERE / "out" / "round7"
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
    "comfortaa/Comfortaa[wght].ttf":
        "0fc3f45dc48b614db9c39181502544b37217ecbf8bee2fb35886992bc96c5bd3",
    "fredoka/Fredoka[wdth,wght].ttf":
        "2ba02e68b152868aef9ba28e24b3648c7d457fe6f25c761f2c2c53fb61a73fc8",
    "quicksand/Quicksand[wght].ttf":
        "39c9b64223561f56aaff6062a6f04063c4fc86809ad6768722c06614d977e1cc",
    "baloo2/Baloo2[wght].ttf":
        "d47a6852548059b1db49a1319d06d499d546c3fa2237cf9eee9c43c8abb025c2",
    "righteous/Righteous-Regular.ttf":
        "2ffb3fe5c27d7e6571210b800448c4e234e651b46c6b4426c1bb567e5341348a",
    "pacifico/Pacifico-Regular.ttf":
        "5b6c0d5334a7bf77dea52b975c5a0c408878c0f7115ed5b6fb151f634b7bf701",
    "kaushanscript/KaushanScript-Regular.ttf":
        "6d8d379d9bba98178bee476d68114c8f83812c18005ecccf679e70f60e03d8f6",
    "gloock/Gloock-Regular.ttf":
        "c3a67e0212f7da01764796ae721cb9bab3e122d142354f97cf9c63fb763e6d77",
    "audiowide/Audiowide-Regular.ttf":
        "c7c0f2b0f6fad8c623e31772ce79f94a4edb9321ffce9fce978ea892d20ae730",
    "spacegrotesk/SpaceGrotesk[wght].ttf":
        "acad6de1fc93436f5c0f1f4137751ef04f1aea3063e7036535970ffcfbd79f72",
}

WORD_PX, WORD_SPACING, WORD_BASELINE = 92, 10, 748  # round 4's guesses, unchanged this round

# The splash word: (label, note, pango font with the size in it, letter spacing in px). The two
# scripts join their letters, so they take no added spacing.
WORDS = {
    "v1": ("V1 Comfortaa", "weight 700", f"Comfortaa {WORD_PX} @wght=700", WORD_SPACING),
    "v2": ("V2 Fredoka", "weight 600", f"Fredoka {WORD_PX} @wght=600", WORD_SPACING),
    "v3": ("V3 Quicksand", "weight 700", f"Quicksand {WORD_PX} @wght=700", WORD_SPACING),
    "v4": ("V4 Baloo 2", "weight 700", f"Baloo 2 {WORD_PX} @wght=700", WORD_SPACING),
    "v5": ("V5 Righteous", "one weight", f"Righteous {WORD_PX}", WORD_SPACING),
    "v6": ("V6 Pacifico", "script, no added spacing", f"Pacifico {WORD_PX}", 0),
    "v7": ("V7 Kaushan Script", "script, no added spacing", f"Kaushan Script {WORD_PX}", 0),
    "v8": ("V8 Gloock", "high-contrast serif", f"Gloock {WORD_PX}", WORD_SPACING),
    "v9": ("V9 Audiowide", "one weight", f"Audiowide {WORD_PX}", WORD_SPACING),
    "v10": ("V10 Space Grotesk", "weight 700", f"Space Grotesk {WORD_PX} @wght=700", WORD_SPACING),
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

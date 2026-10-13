#!/usr/bin/env python3
"""PROTOTYPE, throwaway: the splash word "Rill" in five faces from outside the package.

Round 6 of "Settle Rill's final colours, typeface and mark size" (issue 32). Round 5 set the word
in the faces under pkg/ (Inter and Noto Sans CJK KR); the owner asked for a more interesting face.
The splash is a picture, so the face is drawn into the PNG and its font file need not ship. This
round draws one sheet:

  splashes.png  round 5's T2 (Inter Bold with the tailed l, from pkg/) as the reference, then the
                word in five other faces, each as a whole splash and as a crop of the word at real
                pixel size.

The five faces come from github.com/google/fonts at one pinned commit, each under the SIL Open
Font License 1.1 with no Reserved Font Name (read from the OFL.txt beside each file at that
commit). The script downloads them into ~/.cache/rill-artwork-prototype/fonts/ and checks each
against the sha256 below; no font file is added to the repository.

Run: python3 artwork-prototype/round6.py
     (needs rsvg-convert, pango-view, ImageMagick's magick and, the first time, the network;
     writes artwork-prototype/out/round6/)

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
OUT = HERE / "out" / "round6"
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
    "fraunces/Fraunces[SOFT,WONK,opsz,wght].ttf":
        "177ff6c0f14e5550a3c624247cd1189611d4eb65d000b14944c63d967958abbb",
    "bricolagegrotesque/BricolageGrotesque[opsz,wdth,wght].ttf":
        "413e7357809ddd12fd80a96a8a396de0e401638d4acd3cb3e37532f0472ac682",
    "unbounded/Unbounded[wght].ttf":
        "323b511be380c8d474ef030686b71aedde501f8d9cd46da558b7c40454372c3f",
    "syne/Syne[wght].ttf":
        "ce5ac77142a65cab2248a1a2ebb740b1d4d9c20b52488877d3ff664d1356104a",
    "instrumentserif/InstrumentSerif-Italic.ttf":
        "08939b8bdf534afec24ae0ef5e03f948940cd9a8fe08e7fecbad040e62327385",
}

WORD_PX, WORD_SPACING, WORD_BASELINE = 92, 10, 748  # round 4's guesses, unchanged this round

# The splash word: (label, where it comes from, pango font with the size in it, pango features).
WORDS = {
    "t2": ("T2 Inter Bold, tailed l", "round 5, pkg/appfont-bold.ttf", f"Inter Bold {WORD_PX}", "cv05=1"),
    "u1": ("U1 Fraunces", "soft serif, weight 600",
           f"Fraunces {WORD_PX} @wght=600,SOFT=100,opsz=144", ""),
    "u2": ("U2 Bricolage Grotesque", "weight 700",
           f"Bricolage Grotesque {WORD_PX} @wght=700,opsz=96", ""),
    "u3": ("U3 Unbounded", "weight 500", f"Unbounded {WORD_PX} @wght=500", ""),
    "u4": ("U4 Syne", "weight 800", f"Syne {WORD_PX} @wght=800", ""),
    "u5": ("U5 Instrument Serif", "italic", f"Instrument Serif Italic {WORD_PX}", ""),
}

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
    _, _, font, features = WORDS[key]
    span = f"letter_spacing='{WORD_SPACING * 1024}'"
    if features:
        span += f" font_features='{features}'"
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


COL, THUMB_H, CROP_H = 320, 169, 170
SHEET_W, SHEET_H = COL * len(WORDS), 60 + THUMB_H + 50 + CROP_H + 30


def splash_sheet(words):
    """One column per face: the whole splash small, then the word cropped at real pixel size."""
    out = [f'<rect width="{SHEET_W}" height="{SHEET_H}" fill="#15171c"/>']
    for i, key in enumerate(WORDS):
        name, source, *_ = WORDS[key]
        x = i * COL + 10
        out.append(label(x, 28, name, 18, "#ffffff", 700))
        out.append(label(x, 48, source, 12, "#8b929e"))
        out.append(f'<svg x="{x}" y="60" width="{COL - 20}" height="{THUMB_H}" '
                   f'viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid slice">'
                   f"{splash(words[key])}</svg>")
        out.append(label(x, 60 + THUMB_H + 32, "the word at real size", 12, "#8b929e"))
        # A window of the real splash, 1:1, centred on the word.
        cx, cy = 960 - (COL - 20) / 2, WORD_BASELINE - 120
        out.append(f'<svg x="{x}" y="{60 + THUMB_H + 50}" width="{COL - 20}" height="{CROP_H}" '
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
        # Only the package's fonts and the five downloads exist for this run.
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

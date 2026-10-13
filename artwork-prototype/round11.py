#!/usr/bin/env python3
"""PROTOTYPE, throwaway: where Rill's mark sits on the tile, and the spacing of the splash.

Round 11 of "Settle Rill's final colours, typeface and mark size" (issue 32). Settled so far: the
colours (K4, the owner), the word in Fraunces (the owner), the mark's size (S3), its cuts (C5) and
the splash's size (P3), the last three picked by the agent at the owner's word. This round asks
about the last guessed values. It draws two sheets:

  sheet.png     the mark at five positions across the tile, each in a mock launcher row, then the
                80 and 130 px files at real size.
  splashes.png  the splash with five settings of the gap between mark and word and of the word's
                letter spacing.

Fraunces comes from github.com/google/fonts at one pinned commit under the SIL Open Font License
1.1 with no Reserved Font Name. The script downloads it into
~/.cache/rill-artwork-prototype/fonts/ and checks it against the sha256 below; no font file is
added to the repository. The sheets' labels are set in the package's Inter.

Run: python3 artwork-prototype/round11.py
     (needs rsvg-convert, pango-view, ImageMagick's magick and, the first time, the network;
     writes artwork-prototype/out/round11/)

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
OUT = HERE / "out" / "round11"
PKG = HERE.parent / "pkg"
CACHE = pathlib.Path(os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache"))
FONTS = CACHE / "rill-artwork-prototype" / "fonts"
GOOGLE_FONTS = "https://raw.githubusercontent.com/google/fonts/66928797f271fed5ee428544e7229685e2d90127/ofl/"
FRAUNCES = ("fraunces/Fraunces[SOFT,WONK,opsz,wght].ttf",
            "177ff6c0f14e5550a3c624247cd1189611d4eb65d000b14944c63d967958abbb")
WORD_FONT = "Fraunces {px} @wght=600,SOFT=100,opsz=144"  # round 6's U1, the owner's choice
FONT = "Inter"

TILE_SCALE = 1.05  # round 5's S3
CORNER, WAVE, CUT = 20, 30, 34  # round 9's C5
SPLASH_SCALE, WORD_PX = 1.0, 116  # round 9's P3

AQUA, DARK = "#9aeadc", "#0c2330"  # round 10's K4

# Key: (label, shift of the mark across the tile in units of the 400 box). At S3 the outline spans
# x 99.2..357.5 unshifted; its area sits about 8 units left of the tile's centre and its box 28
# units right of it.
POSITIONS = {
    "m1": ("M1 Weight centred", 8),
    "m2": ("M2 As round 4", 0),
    "m3": ("M3 A third of the way", -9),
    "m4": ("M4 Two thirds of the way", -19),
    "m5": ("M5 Box centred", -28),
}

# Key: (label, gap between mark and word in px, letter spacing in px), on the 1080 px frame.
SPACINGS = {
    "g1": ("G1 As now", 125, 12.6),
    "g2": ("G2 Closer", 85, 12.6),
    "g3": ("G3 Closest", 50, 12.6),
    "g4": ("G4 Closer, tight letters", 85, 3),
    "g5": ("G5 Closer, wide letters", 85, 26),
}

ENV = dict(os.environ)



def shape(ink, bg):
    """The mark in a 400x400 box: a solid triangle with rounded corners and two waves cut out of
    it. Its outline fills x 104..350 and y 50..350."""
    r = CORNER

    def wave(y):
        return (f"M30 {y} C105 {y - WAVE} 150 {y - WAVE} 200 {y} S295 {y + WAVE} 340 {y} "
                f"S390 {y - WAVE} 420 {y}")

    return f"""
  <path d="M{104 + r} {50 + r} L{350 - r} 200 L{104 + r} {350 - r} Z" fill="{ink}"
        stroke="{ink}" stroke-width="{2 * r}" stroke-linejoin="round"/>
  <g fill="none" stroke="{bg}" stroke-width="{CUT}">
    <path d="{wave(160)}"/>
    <path d="{wave(240)}"/>
  </g>"""


def tile(dx, swap=False):
    """Inner markup of one 400x400 tile with the mark shifted `dx` across it; swap is the Rill
    debug tile (the two colours trade)."""
    ink, bg = (DARK, AQUA) if swap else (AQUA, DARK)
    return (
        f'<rect width="400" height="400" fill="{bg}"/>'
        f'<g transform="translate({200 + dx} 200) scale({TILE_SCALE}) translate(-200 -200)">'
        f"{shape(ink, bg)}</g>"
    )


def svg(inner, w, h, box="0 0 400 400"):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{box}">'
        f"{inner}</svg>\n"
    )


def fetch_font():
    path, want = FRAUNCES
    FONTS.mkdir(parents=True, exist_ok=True)
    dest = FONTS / pathlib.PurePosixPath(path).name
    if not dest.exists():
        with urllib.request.urlopen(GOOGLE_FONTS + urllib.parse.quote(path)) as r:
            dest.write_bytes(r.read())
    got = hashlib.sha256(dest.read_bytes()).hexdigest()
    if got != want:
        raise SystemExit(f"{dest}: sha256 {got}, expected {want}")


def word_image(key, spacing_px, tmp):
    """The word "Rill" as a PNG trimmed to its ink, drawn by pango with `spacing_px` between its
    letters. Returns (data URI, width, height)."""
    raw, cut = tmp / f"word-{key}-raw.png", tmp / f"word-{key}.png"
    spacing = round(spacing_px * 1024)
    subprocess.run(
        ["pango-view", "--no-display", "--markup", f"--font={WORD_FONT.format(px=WORD_PX)}",
         "--dpi=72", "--margin=60", "--background=transparent", f"--foreground={AQUA}",
         f"--text=<span letter_spacing='{spacing}'>Rill</span>", "-o", str(raw)],
        check=True, env=ENV,
    )
    subprocess.run(["magick", str(raw), "-trim", "+repage", str(cut)], check=True)
    w, h = subprocess.run(
        ["magick", "identify", "-format", "%w %h", str(cut)],
        check=True, capture_output=True, text=True,
    ).stdout.split()
    return "data:image/png;base64," + base64.b64encode(cut.read_bytes()).decode(), int(w), int(h)


def splash(gap, word):
    """1920x1080: the field edge to edge, the mark over the word `gap` px below it, the pair
    centred on the frame."""
    uri, w, h = word
    s = SPLASH_SCALE
    mark_h = 300 * s
    top = 540 - (mark_h + gap + h) / 2
    return (
        f'<rect width="1920" height="1080" fill="{DARK}"/>'
        + f'<g transform="translate({960 - 200 * s} {top - 50 * s}) scale({s})">'
        + shape(AQUA, DARK)
        + "</g>"
        + f'<image x="{960 - w / 2}" y="{top + mark_h + gap}" width="{w}" height="{h}" href="{uri}"/>'
    )


def nested(inner, x, y, size):
    return f'<svg x="{x}" y="{y}" width="{size}" height="{size}" viewBox="0 0 400 400">{inner}</svg>'


def label(x, y, text, size=15, fill="#c9ced6", anchor="middle", weight=400):
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{FONT}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">{text}</text>'
    )


def launcher_tile(x, y, colour, icon=None, title=""):
    """A mock launcher tile: 170x170 in the tile colour (LG paints `iconColor` there) with the icon
    drawn into a 115x115 box, 5 px above centre, as docs/distribution.md section 10.1 measured."""
    out = f'<rect x="{x}" y="{y}" width="170" height="170" rx="18" fill="{colour}"/>'
    if icon:
        out += nested(icon, x + 27.5, y + 22.5, 115)
    return out + label(x + 85, y + 194, title)


def sheet():
    row_h, w = 300, 1500
    h = row_h * len(POSITIONS) + 60
    out = [f'<rect width="{w}" height="{h}" fill="#15171c"/>']
    for i, (name, dx) in enumerate(POSITIONS.values()):
        y = 60 + i * row_h
        left, right = (99.2 + dx) / 4, (400 - 357.5 - dx) / 4
        out.append(label(30, y + 20, name, 26, "#ffffff", "start", 700))
        out.append(label(30, y + 46, f"{left:.1f} % of the width clear on the left, "
                                     f"{right:.1f} % on the right", 14, "#8b929e", "start"))
        out.append(launcher_tile(40, y + 70, "#000000", None, "neighbour"))
        out.append(launcher_tile(230, y + 70, DARK, tile(dx), "Rill"))
        out.append(launcher_tile(420, y + 70, AQUA, tile(dx, swap=True), "Rill debug"))
        out.append(launcher_tile(610, y + 70, "#ffffff", None, "neighbour"))
        out.append(nested(tile(dx), 810, y + 50, 220))
        for j, swap in enumerate((False, True)):
            out.append(nested(tile(dx, swap), 1060 + j * 90, y + 95, 80))
            out.append(nested(tile(dx, swap), 1230 + j * 135, y + 70, 130))
    out.append(label(40, 34, "Mock launcher row (icon in LG's 115 px box)", 16, "#8b929e", "start"))
    out.append(label(810, 34, "Enlarged", 16, "#8b929e", "start"))
    out.append(label(1060, 34, "Files at real size: 80 px, then 130 px", 16, "#8b929e", "start"))
    return svg("".join(out), w, h, f"0 0 {w} {h}")


SPLASH_W, SPLASH_H = 1920, 2 * 410


def splash_sheet(words):
    """Five whole splashes at a third of their size, three above and two below."""
    out = [f'<rect width="{SPLASH_W}" height="{SPLASH_H}" fill="#15171c"/>']
    for i, (key, (name, gap, spacing)) in enumerate(SPACINGS.items()):
        x, y = (i % 3) * 640 + 10, (i // 3) * 410
        out.append(label(x, y + 30, name, 20, "#ffffff", "start", 700))
        out.append(label(x + 620, y + 30, f"gap {gap} px, letter spacing {spacing} px, "
                                          "in a 1080 px frame", 13, "#8b929e", "end"))
        out.append(f'<svg x="{x}" y="{y + 44}" width="620" height="348.75" viewBox="0 0 1920 1080">'
                   f"{splash(gap, words[key])}</svg>")
    return svg("".join(out), SPLASH_W, SPLASH_H, f"0 0 {SPLASH_W} {SPLASH_H}")

def render(name, markup, w, h):
    src = OUT / f"{name}.svg"
    src.write_text(markup)
    subprocess.run(
        ["rsvg-convert", "-w", str(w), "-h", str(h), "-o", str(OUT / f"{name}.png"), str(src)],
        check=True, env=ENV,
    )


def main():
    fetch_font()
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t)
        # Only the package's fonts and Fraunces exist for this run.
        conf = tmp / "fonts.conf"
        conf.write_text(
            '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd">'
            f"<fontconfig><dir>{PKG.resolve()}</dir><dir>{FONTS}</dir>"
            f"<cachedir>{tmp}/cache</cachedir></fontconfig>"
        )
        ENV["FONTCONFIG_FILE"] = str(conf)
        for key, (_, dx) in POSITIONS.items():
            for variant, swap in (("release", False), ("swap", True)):
                for size in (80, 130):
                    render(f"position-{key}-{variant}-{size}", svg(tile(dx, swap), size, size),
                           size, size)
        render("sheet", sheet(), 1500, 300 * len(POSITIONS) + 60)
        words = {key: word_image(key, spacing, tmp) for key, (_, _, spacing) in SPACINGS.items()}
        for key, (_, gap, _) in SPACINGS.items():
            render(f"splash-{key}", svg(splash(gap, words[key]), 1920, 1080, "0 0 1920 1080"),
                   1920, 1080)
        render("splashes", splash_sheet(words), SPLASH_W, SPLASH_H)


if __name__ == "__main__":
    main()

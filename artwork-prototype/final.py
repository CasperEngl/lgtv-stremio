#!/usr/bin/env python3
"""PROTOTYPE: Rill's icon and splash with every value settled so far, as the five files the
television expects.

The outcome of "Settle Rill's final colours, typeface and mark size" (issue 32), rounds 5 to 11.
Each constant below names who settled it. Nothing here has been seen on a television.

  rill/icon.png            80x80
  rill/largeIcon.png       130x130
  rill-debug/icon.png      80x80, the two colours swapped
  rill-debug/largeIcon.png 130x130, the two colours swapped
  splash.png               1920x1080
  sheet.png                both tiles in a mock launcher row, the four icon files at real size,
                           and the splash

Fraunces comes from github.com/google/fonts at one pinned commit under the SIL Open Font License
1.1 with no Reserved Font Name. The script downloads it into
~/.cache/rill-artwork-prototype/fonts/ and checks it against the sha256 below; no font file is
added to the repository. The sheet's labels are set in the package's Inter.

Run: python3 artwork-prototype/final.py
     (needs rsvg-convert, pango-view, ImageMagick's magick and, the first time, the network;
     writes artwork-prototype/out/final/)

Nothing here is cut for the package: pkg/ and assets/ are upstream's and stay unedited. How these
files reach the package is the build plan's question.
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
OUT = HERE / "out" / "final"
PKG = HERE.parent / "pkg"
CACHE = pathlib.Path(os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache"))
FONTS = CACHE / "rill-artwork-prototype" / "fonts"
GOOGLE_FONTS = "https://raw.githubusercontent.com/google/fonts/66928797f271fed5ee428544e7229685e2d90127/ofl/"
FRAUNCES = ("fraunces/Fraunces[SOFT,WONK,opsz,wght].ttf",
            "177ff6c0f14e5550a3c624247cd1189611d4eb65d000b14944c63d967958abbb")
FONT = "Inter"

# The owner's choices.
AQUA, DARK = "#9aeadc", "#0c2330"  # round 10, K4
WORD_FONT = "Fraunces {px} @wght=600,SOFT=100,opsz=144"  # round 6, U1

# The agent's picks, made when the owner answered "you pick".
TILE_SCALE = 1.05  # round 5, S3: the mark is 64.6 % of the tile's width
CORNER, WAVE, CUT = 20, 30, 34  # round 9, C5, in units of the 400 box
SPLASH_SCALE, WORD_PX = 1.0, 116  # round 9, P3: a 300 px mark over a 116 px word

# The agent's rule for the owner's "visually centred for a human": the tile's centre sits halfway
# between the centre of the mark's ink and the centre of its outline box. Measured on a 1600 px
# render of the tile mark: ink centre x 186.4, box centre x 228.4 (of 400), so the mark moves 7.4
# units left. The same rule on the unscaled splash mark (187.0 and 227.0) moves it 7 px left.
# Vertically the ink centre is 2.7 units low, under 1 px at 130, and is left alone.
TILE_SHIFT, SPLASH_SHIFT = -7.4, -7.0

# The agent's pick: round 11, G2. The owner was shown G1 to G5 and named none.
SPLASH_GAP, WORD_SPACING = 85, 12.6

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


def tile(swap=False):
    """Inner markup of one 400x400 tile; swap is the Rill debug tile (the two colours trade)."""
    ink, bg = (DARK, AQUA) if swap else (AQUA, DARK)
    return (
        f'<rect width="400" height="400" fill="{bg}"/>'
        f'<g transform="translate({200 + TILE_SHIFT} 200) scale({TILE_SCALE}) '
        f'translate(-200 -200)">{shape(ink, bg)}</g>'
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


def word_image(tmp):
    """The word "Rill" as a PNG trimmed to its ink, drawn by pango.
    Returns (data URI, width, height)."""
    raw, cut = tmp / "word-raw.png", tmp / "word.png"
    subprocess.run(
        ["pango-view", "--no-display", "--markup", f"--font={WORD_FONT.format(px=WORD_PX)}",
         "--dpi=72", "--margin=60", "--background=transparent", f"--foreground={AQUA}",
         f"--text=<span letter_spacing='{round(WORD_SPACING * 1024)}'>Rill</span>", "-o", str(raw)],
        check=True, env=ENV,
    )
    subprocess.run(["magick", str(raw), "-trim", "+repage", str(cut)], check=True)
    w, h = subprocess.run(
        ["magick", "identify", "-format", "%w %h", str(cut)],
        check=True, capture_output=True, text=True,
    ).stdout.split()
    return "data:image/png;base64," + base64.b64encode(cut.read_bytes()).decode(), int(w), int(h)


def splash(word):
    """1920x1080: the field edge to edge, the mark over the word, the pair centred on the frame."""
    uri, w, h = word
    s = SPLASH_SCALE
    mark_h = 300 * s
    top = 540 - (mark_h + SPLASH_GAP + h) / 2
    return (
        f'<rect width="1920" height="1080" fill="{DARK}"/>'
        + f'<g transform="translate({960 + SPLASH_SHIFT - 200 * s} {top - 50 * s}) scale({s})">'
        + shape(AQUA, DARK)
        + "</g>"
        + f'<image x="{960 - w / 2}" y="{top + mark_h + SPLASH_GAP}" width="{w}" height="{h}" '
        f'href="{uri}"/>'
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


def sheet(word):
    w, h = 1500, 300 + 60 + 620
    out = [f'<rect width="{w}" height="{h}" fill="#15171c"/>']
    out.append(label(40, 34, "Mock launcher row (icon in LG's 115 px box)", 16, "#8b929e", "start"))
    out.append(label(810, 34, "Enlarged", 16, "#8b929e", "start"))
    out.append(label(1060, 34, "Files at real size: 80 px, then 130 px", 16, "#8b929e", "start"))
    y = 60
    out.append(launcher_tile(40, y + 30, "#000000", None, "neighbour"))
    out.append(launcher_tile(230, y + 30, DARK, tile(), "Rill"))
    out.append(launcher_tile(420, y + 30, AQUA, tile(swap=True), "Rill debug"))
    out.append(launcher_tile(610, y + 30, "#ffffff", None, "neighbour"))
    out.append(nested(tile(), 810, y + 10, 220))
    for j, swap in enumerate((False, True)):
        out.append(nested(tile(swap), 1060 + j * 90, y + 55, 80))
        out.append(nested(tile(swap), 1230 + j * 135, y + 30, 130))
    out.append(label(40, 344, "Splash, at half size", 16, "#8b929e", "start"))
    out.append(f'<svg x="40" y="360" width="960" height="540" viewBox="0 0 1920 1080">'
               f"{splash(word)}</svg>")
    return svg("".join(out), w, h, f"0 0 {w} {h}")


def render(name, markup, w, h):
    src = OUT / f"{name}.svg"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(markup)
    subprocess.run(
        ["rsvg-convert", "-w", str(w), "-h", str(h), "-o", str(OUT / f"{name}.png"), str(src)],
        check=True, env=ENV,
    )


def main():
    fetch_font()
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
        for folder, swap in (("rill", False), ("rill-debug", True)):
            render(f"{folder}/icon", svg(tile(swap), 80, 80), 80, 80)
            render(f"{folder}/largeIcon", svg(tile(swap), 130, 130), 130, 130)
        word = word_image(tmp)
        render("splash", svg(splash(word), 1920, 1080, "0 0 1920 1080"), 1920, 1080)
        render("sheet", sheet(word), 1500, 980)


if __name__ == "__main__":
    main()

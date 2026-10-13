#!/usr/bin/env python3
"""PROTOTYPE, throwaway: five colour pairs for Rill, on the mark, both tiles and the splash.

Round 10 of "Settle Rill's final colours, typeface and mark size" (issue 32). Settled so far: the
word is in Fraunces (the owner, round 6 U1); the mark on the tile is 1.05 of round 4's (S3), its
cuts are 34 units thick (C5) and the splash carries a 300 px mark over a 116 px word (P3), those
three picked by the agent at the owner's word. This round changes only the two colours. It draws
one sheet:

  sheet.png  one row per pair: a mock launcher row (a dark neighbour, Rill, Rill debug, a light
             neighbour), the 80 and 130 px files at real size, and the splash at a sixth of its
             size.

Each row prints the pair's contrast ratio, computed here by the WCAG 2 relative-luminance formula.

Fraunces comes from github.com/google/fonts at one pinned commit under the SIL Open Font License
1.1 with no Reserved Font Name. The script downloads it into
~/.cache/rill-artwork-prototype/fonts/ and checks it against the sha256 below; no font file is
added to the repository. The sheet's labels are set in the package's Inter.

Run: python3 artwork-prototype/round10.py
     (needs rsvg-convert, pango-view, ImageMagick's magick and, the first time, the network;
     writes artwork-prototype/out/round10/)

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
OUT = HERE / "out" / "round10"
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

# Key: (label, note, aqua, blue-black).
PAIRS = {
    "k1": ("K1 As round 4", "aqua on blue-black", "#4fd8c4", "#071a24"),
    "k2": ("K2 Cooler", "towards cyan, on a bluer black", "#56d0e6", "#06162a"),
    "k3": ("K3 Greener", "towards sea green, on a teal black", "#5fe0ae", "#06201e"),
    "k4": ("K4 Paler", "a lighter aqua, on a lifted blue-black", "#9aeadc", "#0c2330"),
    "k5": ("K5 Deeper", "a more saturated aqua, on a near black", "#1fc8b4", "#030e14"),
}

ENV = dict(os.environ)


def luminance(colour):
    def channel(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(int(colour[i:i + 2], 16)) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


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


def tile(aqua, dark, swap=False):
    """Inner markup of one 400x400 tile; swap is the Rill debug tile (the two colours trade)."""
    ink, bg = (dark, aqua) if swap else (aqua, dark)
    return (
        f'<rect width="400" height="400" fill="{bg}"/>'
        f'<g transform="translate(200 200) scale({TILE_SCALE}) translate(-200 -200)">'
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


def word_image(key, colour, tmp):
    """The word "Rill" as a PNG trimmed to its ink, drawn by pango, with round 4's letter spacing
    kept in proportion (10 px at 92). Returns (data URI, width, height)."""
    raw, cut = tmp / f"word-{key}-raw.png", tmp / f"word-{key}.png"
    spacing = round(WORD_PX * 10 / 92 * 1024)
    subprocess.run(
        ["pango-view", "--no-display", "--markup", f"--font={WORD_FONT.format(px=WORD_PX)}",
         "--dpi=72", "--margin=60", "--background=transparent", f"--foreground={colour}",
         f"--text=<span letter_spacing='{spacing}'>Rill</span>", "-o", str(raw)],
        check=True, env=ENV,
    )
    subprocess.run(["magick", str(raw), "-trim", "+repage", str(cut)], check=True)
    w, h = subprocess.run(
        ["magick", "identify", "-format", "%w %h", str(cut)],
        check=True, capture_output=True, text=True,
    ).stdout.split()
    return "data:image/png;base64," + base64.b64encode(cut.read_bytes()).decode(), int(w), int(h)


def splash(aqua, dark, word):
    """1920x1080: the field edge to edge, the mark over the word, the pair centred on the frame."""
    uri, w, h = word
    s = SPLASH_SCALE
    mark_h, gap = 300 * s, 125 * s
    top = 540 - (mark_h + gap + h) / 2
    return (
        f'<rect width="1920" height="1080" fill="{dark}"/>'
        + f'<g transform="translate({960 - 200 * s} {top - 50 * s}) scale({s})">'
        + shape(aqua, dark)
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


def sheet(words):
    row_h, w = 300, 1700
    h = row_h * len(PAIRS) + 60
    out = [f'<rect width="{w}" height="{h}" fill="#15171c"/>']
    for i, (key, (name, note, aqua, dark)) in enumerate(PAIRS.items()):
        y = 60 + i * row_h
        out.append(label(30, y + 20, name, 26, "#ffffff", "start", 700))
        out.append(label(30, y + 46, f"{aqua} on {dark}, contrast {contrast(aqua, dark):.1f} to 1"
                                     f": {note}", 14, "#8b929e", "start"))
        out.append(launcher_tile(40, y + 70, "#000000", None, "neighbour"))
        out.append(launcher_tile(230, y + 70, dark, tile(aqua, dark), "Rill"))
        out.append(launcher_tile(420, y + 70, aqua, tile(aqua, dark, swap=True), "Rill debug"))
        out.append(launcher_tile(610, y + 70, "#ffffff", None, "neighbour"))
        for j, swap in enumerate((False, True)):
            out.append(nested(tile(aqua, dark, swap), 820 + j * 90, y + 95, 80))
            out.append(nested(tile(aqua, dark, swap), 1000 + j * 135, y + 70, 130))
        out.append(f'<svg x="1300" y="{y + 60}" width="380" height="213.75" viewBox="0 0 1920 1080">'
                   f"{splash(aqua, dark, words[key])}</svg>")
    out.append(label(40, 34, "Mock launcher row (icon in LG's 115 px box)", 16, "#8b929e", "start"))
    out.append(label(820, 34, "Files at real size: 80 px, then 130 px", 16, "#8b929e", "start"))
    out.append(label(1300, 34, "Splash", 16, "#8b929e", "start"))
    return svg("".join(out), w, h, f"0 0 {w} {h}")


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
        words = {}
        for key, (_, _, aqua, dark) in PAIRS.items():
            for variant, swap in (("release", False), ("swap", True)):
                for size in (80, 130):
                    render(f"{key}-{variant}-{size}", svg(tile(aqua, dark, swap), size, size),
                           size, size)
            words[key] = word_image(key, aqua, tmp)
            render(f"{key}-splash", svg(splash(aqua, dark, words[key]), 1920, 1080,
                                        "0 0 1920 1080"), 1920, 1080)
        render("sheet", sheet(words), 1700, 300 * len(PAIRS) + 60)


if __name__ == "__main__":
    main()

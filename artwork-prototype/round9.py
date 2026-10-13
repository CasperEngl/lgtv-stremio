#!/usr/bin/env python3
"""PROTOTYPE, throwaway: the exact curves of Rill's mark, and the sizes of the mark and word on the splash.

Round 9 of "Settle Rill's final colours, typeface and mark size" (issue 32). The owner chose
Fraunces for the splash word (round 6, U1). The mark's size on the tile is still round 4's, since
none of round 5's five sizes was picked. This round draws two sheets:

  sheet.png     the mark in five cuts of its corners and waves, all inside the same outline box,
                each in a mock launcher row, then the 80 and 130 px files at real size.
  splashes.png  the splash with the mark and the word at five sizes, the word in Fraunces.

Fraunces comes from github.com/google/fonts at one pinned commit under the SIL Open Font License
1.1 with no Reserved Font Name. The script downloads it into
~/.cache/rill-artwork-prototype/fonts/ and checks it against the sha256 below; no font file is
added to the repository. The sheets' labels are set in the package's Inter.

Run: python3 artwork-prototype/round9.py
     (needs rsvg-convert, pango-view, ImageMagick's magick and, the first time, the network;
     writes artwork-prototype/out/round9/)

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
OUT = HERE / "out" / "round9"
PKG = HERE.parent / "pkg"
CACHE = pathlib.Path(os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache"))
FONTS = CACHE / "rill-artwork-prototype" / "fonts"
GOOGLE_FONTS = "https://raw.githubusercontent.com/google/fonts/66928797f271fed5ee428544e7229685e2d90127/ofl/"
FRAUNCES = ("fraunces/Fraunces[SOFT,WONK,opsz,wght].ttf",
            "177ff6c0f14e5550a3c624247cd1189611d4eb65d000b14944c63d967958abbb")
WORD_FONT = "Fraunces {px} @wght=600,SOFT=100,opsz=144"  # round 6's U1, the owner's choice
FONT = "Inter"
BG, INK = "#071a24", "#4fd8c4"  # round 4's guesses, unchanged this round

ENV = dict(os.environ)


def shape(radius=20, amp=30, cut=24):
    """The mark in a 400x400 box: a solid triangle whose corners are rounded to `radius`, with two
    waves of amplitude `amp` and thickness `cut` taken out of it. Whatever the radius, the
    outline stays inside x 104..350 and y 50..350, the box round 4's mark fills."""
    r = radius

    def wave(y):
        return (f"M30 {y} C105 {y - amp} 150 {y - amp} 200 {y} S295 {y + amp} 340 {y} "
                f"S390 {y - amp} 420 {y}")

    return f"""
  <path d="M{104 + r} {50 + r} L{350 - r} 200 L{104 + r} {350 - r} Z" fill="{{ink}}"
        stroke="{{ink}}" stroke-width="{2 * r}" stroke-linejoin="round"/>
  <g fill="none" stroke="{{bg}}" stroke-width="{cut}">
    <path d="{wave(160)}"/>
    <path d="{wave(240)}"/>
  </g>"""


# Key: (label, note, corner radius, wave amplitude, cut thickness), in units of the 400 box.
CURVES = {
    "c1": ("C1 As round 4", "corner 20, wave 30, cut 24", 20, 30, 24),
    "c2": ("C2 Sharper corners", "corner 8", 8, 30, 24),
    "c3": ("C3 Rounder corners", "corner 34", 34, 30, 24),
    "c4": ("C4 Deeper waves", "wave 44", 20, 44, 24),
    "c5": ("C5 Wider cuts", "cut 34", 20, 30, 34),
}

# Key: (label, scale of the 400 box on the 1080 frame, word size in px). Round 4 drew 0.8 and 92.
SPLASHES = {
    "p1": ("P1 Small", 0.6, 70),
    "p2": ("P2 As round 4", 0.8, 92),
    "p3": ("P3 Large", 1.0, 116),
    "p4": ("P4 Large mark, small word", 1.0, 72),
    "p5": ("P5 Very large", 1.3, 150),
}


def mark(markup, swap=False):
    ink, bg = (BG, INK) if swap else (INK, BG)
    return markup.format(ink=ink, bg=bg)


def tile(markup, swap=False):
    """Inner markup of one 400x400 tile; swap is the Rill debug tile (the two colours trade)."""
    return f'<rect width="400" height="400" fill="{INK if swap else BG}"/>' + mark(markup, swap)


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


def word_image(px, tmp):
    """The word "Rill" at `px` as a PNG trimmed to its ink, drawn by pango, with round 4's letter
    spacing kept in proportion (10 px at 92). Returns (data URI, width, height)."""
    raw, cut = tmp / f"word-{px}-raw.png", tmp / f"word-{px}.png"
    spacing = round(px * 10 / 92 * 1024)
    subprocess.run(
        ["pango-view", "--no-display", "--markup", f"--font={WORD_FONT.format(px=px)}", "--dpi=72",
         "--margin=60", "--background=transparent", f"--foreground={INK}",
         f"--text=<span letter_spacing='{spacing}'>Rill</span>", "-o", str(raw)],
        check=True, env=ENV,
    )
    subprocess.run(["magick", str(raw), "-trim", "+repage", str(cut)], check=True)
    w, h = subprocess.run(
        ["magick", "identify", "-format", "%w %h", str(cut)],
        check=True, capture_output=True, text=True,
    ).stdout.split()
    return "data:image/png;base64," + base64.b64encode(cut.read_bytes()).decode(), int(w), int(h)


def splash(scale, word):
    """1920x1080: the field edge to edge, the mark over the word, the pair centred on the frame.
    The gap between them keeps round 4's proportion (100 px under a 0.8 mark)."""
    uri, w, h = word
    mark_h, gap = 300 * scale, 125 * scale
    top = 540 - (mark_h + gap + h) / 2
    return (
        f'<rect width="1920" height="1080" fill="{BG}"/>'
        + f'<g transform="translate({960 - 200 * scale} {top - 50 * scale}) scale({scale})">'
        + mark(shape())
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
    """One row per cut: a mock launcher row (a blank neighbour, Rill, Rill debug, a blank
    neighbour), the mark large, then the 80 and 130 files at their real pixel size."""
    row_h, w = 300, 1500
    h = row_h * len(CURVES) + 60
    out = [f'<rect width="{w}" height="{h}" fill="#15171c"/>']
    for i, (name, note, *params) in enumerate(CURVES.values()):
        y = 60 + i * row_h
        m = shape(*params)
        out.append(label(30, y + 20, name, 26, "#ffffff", "start", 700))
        out.append(label(30, y + 46, note, 14, "#8b929e", "start"))
        out.append(launcher_tile(40, y + 70, "#2a2d34", None, "neighbour"))
        out.append(launcher_tile(230, y + 70, BG, tile(m), "Rill"))
        out.append(launcher_tile(420, y + 70, INK, tile(m, swap=True), "Rill debug"))
        out.append(launcher_tile(610, y + 70, "#e9e9ec", None, "neighbour"))
        out.append(nested(tile(m), 810, y + 50, 220))
        for j, swap in enumerate((False, True)):
            out.append(nested(tile(m, swap), 1060 + j * 90, y + 95, 80))
            out.append(nested(tile(m, swap), 1230 + j * 135, y + 70, 130))
    out.append(label(40, 34, "Mock launcher row (icon in LG's 115 px box)", 16, "#8b929e", "start"))
    out.append(label(810, 34, "Enlarged", 16, "#8b929e", "start"))
    out.append(label(1060, 34, "Files at real size: 80 px, then 130 px", 16, "#8b929e", "start"))
    return svg("".join(out), w, h, f"0 0 {w} {h}")


SPLASH_W, SPLASH_H = 1920, 2 * 410


def splash_sheet(words):
    """Five whole splashes at a third of their size, three above and two below."""
    out = [f'<rect width="{SPLASH_W}" height="{SPLASH_H}" fill="#15171c"/>']
    for i, (key, (name, scale, px)) in enumerate(SPLASHES.items()):
        x, y = (i % 3) * 640 + 10, (i // 3) * 410
        out.append(label(x, y + 30, name, 20, "#ffffff", "start", 700))
        note = f"mark {300 * scale:.0f} px high, word set at {px} px, in a 1080 px frame"
        out.append(label(x + 620, y + 30, note, 13, "#8b929e", "end"))
        out.append(f'<svg x="{x}" y="{y + 44}" width="620" height="348.75" viewBox="0 0 1920 1080">'
                   f"{splash(scale, words[key])}</svg>")
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
        for key, (_, _, *params) in CURVES.items():
            for variant, swap in (("release", False), ("swap", True)):
                for size in (80, 130):
                    render(f"curve-{key}-{variant}-{size}",
                           svg(tile(shape(*params), swap), size, size), size, size)
        render("sheet", sheet(), 1500, 300 * len(CURVES) + 60)
        words = {key: word_image(px, tmp) for key, (_, _, px) in SPLASHES.items()}
        for key, (_, scale, _) in SPLASHES.items():
            render(f"splash-{key}", svg(splash(scale, words[key]), 1920, 1080, "0 0 1920 1080"),
                   1920, 1080)
        render("splashes", splash_sheet(words), SPLASH_W, SPLASH_H)


if __name__ == "__main__":
    main()

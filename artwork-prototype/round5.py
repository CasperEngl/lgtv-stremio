#!/usr/bin/env python3
"""PROTOTYPE, throwaway: the size of Rill's mark on the tile, and the typeface of the splash word.

Round 5, the first of "Settle Rill's final colours, typeface and mark size" (issue 32). Round 4
(issue 22) chose the mark: two waves cut out of a solid play triangle with rounded corners. This
round changes nothing about that shape or its colours. It draws two sheets:

  sheet.png     the mark at five sizes, each in a mock launcher row beside two stand-in neighbours
                that span 70 % and 91 % of the tile's width (the range upstream measured for store
                icons, docs/distribution.md section 10), then the 80 and 130 px files at real size.
  splashes.png  the word "Rill" under the mark in five settings of the faces the package already
                carries (pkg/appfont.ttf and pkg/appfont-bold.ttf are Inter, pkg/appfont-cjk.ttf is
                Noto Sans CJK KR, all SIL Open Font License 1.1, pkg/OFL.txt), each as a whole
                splash and as a crop of the word at real pixel size.

Every letter here, the sheets' own labels included, is drawn from the font files under pkg/ and
from no system face: fontconfig is pointed at pkg/ alone.

Run: python3 artwork-prototype/round5.py
     (needs rsvg-convert, pango-view and ImageMagick's magick; writes artwork-prototype/out/round5/)

Nothing here is cut for the package: pkg/ and assets/ are upstream's and stay unedited.
"""
import base64
import os
import pathlib
import subprocess
import tempfile

HERE = pathlib.Path(__file__).parent
OUT = HERE / "out" / "round5"
PKG = HERE.parent / "pkg"
FONT = "Inter"
BG, INK = "#071a24", "#4fd8c4"  # round 4's guesses, unchanged this round

WAVE = "C105 {u} 150 {u} 200 {y} S295 {v} 340 {y}"


def wave(y, amp=42, x0=60):
    return f"M{x0} {y} " + WAVE.format(y=y, u=y - amp, v=y + amp)


# Round 4's "play-tidy", unchanged. With its 40-unit stroke the triangle spans x 104..350 and
# y 50..350 of the 400 box: 246 wide (61.5 %) and 300 high (75 %).
MARK = f"""
  <path d="M124 70 L330 200 L124 330 Z" fill="{{ink}}" stroke="{{ink}}" stroke-width="40"
        stroke-linejoin="round"/>
  <g fill="none" stroke="{{bg}}" stroke-width="24">
    <path d="{wave(160, 30, 30)} S390 130 420 160"/>
    <path d="{wave(240, 30, 30)} S390 210 420 240"/>
  </g>"""
MARK_W, MARK_H = 246, 300

# Scale factors about the tile's centre. 1.05 is the largest that keeps the 14 px padding upstream
# emits at 130 px (ink at most 102 of 130, 78.5 %); 1.14 brings the width to the 70 % that the
# narrowest measured store icon spans.
SIZES = {"s1": 0.90, "s2": 1.00, "s3": 1.05, "s4": 1.14, "s5": 1.22}

# The splash word: (label, where it comes from, text, pango font, pango font features).
WORDS = {
    "t1": ("T1 Inter Bold", "pkg/appfont-bold.ttf", "Rill", "Inter Bold", ""),
    "t2": ("T2 Inter Bold, tailed l", "pkg/appfont-bold.ttf, alternate cv05", "Rill", "Inter Bold", "cv05=1"),
    "t3": ("T3 Inter Regular, tailed l", "pkg/appfont.ttf, alternate cv05", "Rill", "Inter", "cv05=1"),
    "t4": ("T4 Inter Bold, capitals", "pkg/appfont-bold.ttf", "RILL", "Inter Bold", ""),
    "t5": ("T5 Noto Sans CJK KR", "pkg/appfont-cjk.ttf", "Rill", "Noto Sans CJK KR", ""),
}
WORD_PX, WORD_SPACING, WORD_BASELINE = 92, 10, 748  # round 4's guesses, unchanged this round

ENV = dict(os.environ)


def mark(swap=False, factor=1.0):
    ink, bg = (BG, INK) if swap else (INK, BG)
    m = MARK.format(ink=ink, bg=bg)
    if factor == 1.0:
        return m
    return f'<g transform="translate(200 200) scale({factor}) translate(-200 -200)">{m}</g>'


def tile(factor, swap=False):
    """Inner markup of one 400x400 tile; swap is the Rill debug tile (the two colours trade)."""
    return f'<rect width="400" height="400" fill="{INK if swap else BG}"/>' + mark(swap, factor)


def svg(inner, w, h, box="0 0 400 400"):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{box}">'
        f"{inner}</svg>\n"
    )


def word_image(key, tmp):
    """The splash word as a PNG trimmed to its ink, drawn by pango from the package's own font
    file (rsvg-convert ignores font-feature-settings, so it cannot reach Inter's tailed l).
    Returns (data URI, width, height)."""
    _, _, text, font, features = WORDS[key]
    span = f"letter_spacing='{WORD_SPACING * 1024}'"
    if features:
        span += f" font_features='{features}'"
    raw, cut = tmp / f"{key}-raw.png", tmp / f"{key}.png"
    subprocess.run(
        ["pango-view", "--no-display", "--markup", f"--font={font} {WORD_PX}", "--dpi=72",
         "--margin=20", "--background=transparent", f"--foreground={INK}",
         f"--text=<span {span}>{text}</span>", "-o", str(raw)],
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
        + f'<g transform="translate(800 300) scale(0.8)">{mark()}</g>'
        + f'<image x="{960 - w / 2}" y="{WORD_BASELINE - h}" width="{w}" height="{h}" href="{uri}"/>'
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


def stand_in(bg, ink, width, height):
    """A neighbour that is nobody's logo: a plain block spanning a measured share of the width."""
    return (
        f'<rect width="400" height="400" fill="{bg}"/>'
        f'<rect x="{200 - width / 2}" y="{200 - height / 2}" width="{width}" height="{height}" '
        f'rx="18" fill="{ink}"/>'
    )


def sheet():
    """One row per size: a mock launcher row (two stand-in neighbours, Rill, Rill debug, a blank
    neighbour), then the 80 and 130 files at their real pixel size."""
    row_h, w = 300, 1500
    h = row_h * len(SIZES) + 60
    out = [f'<rect width="{w}" height="{h}" fill="#15171c"/>']
    for i, (key, f) in enumerate(SIZES.items()):
        y = 60 + i * row_h
        wide, high = MARK_W * f / 4, MARK_H * f / 4
        name = f"{key.upper()}  {wide:.1f} % wide" + ("  (round 4)" if f == 1.0 else "")
        out.append(label(30, y + 20, name, 26, "#ffffff", "start", 700))
        pad = 130 * (100 - high) / 200
        out.append(label(30, y + 46, f"{high:.1f} % high, {pad:.1f} px clear above and below at 130",
                         14, "#8b929e", "start"))
        out.append(launcher_tile(40, y + 70, "#000000", stand_in("#000000", "#f2f2f2", 280, 140),
                                 "stand-in, 70 % wide"))
        out.append(launcher_tile(230, y + 70, "#ffffff", stand_in("#ffffff", "#d0202a", 364, 91),
                                 "stand-in, 91 % wide"))
        out.append(launcher_tile(420, y + 70, BG, tile(f), "Rill"))
        out.append(launcher_tile(610, y + 70, INK, tile(f, swap=True), "Rill debug"))
        out.append(launcher_tile(800, y + 70, "#2a2d34", None, "neighbour"))
        for j, swap in enumerate((False, True)):
            out.append(nested(tile(f, swap), 1040 + j * 100, y + 95, 80))
            out.append(nested(tile(f, swap), 1220 + j * 140, y + 70, 130))
    out.append(label(40, 34, "Mock launcher row (icon in LG's 115 px box)", 16, "#8b929e", "start"))
    out.append(label(1040, 34, "Files at real size: 80 px, then 130 px", 16, "#8b929e", "start"))
    return svg("".join(out), w, h, f"0 0 {w} {h}")


def splash_sheet(words):
    """One column per setting: the whole splash small, then the word cropped at real pixel size."""
    col, thumb_h, crop_h = 300, 169, 150
    w, h = col * len(WORDS), 60 + thumb_h + 50 + crop_h + 30
    out = [f'<rect width="{w}" height="{h}" fill="#15171c"/>']
    for i, key in enumerate(WORDS):
        name, source, *_ = WORDS[key]
        x = i * col + 10
        out.append(label(x, 28, name, 18, "#ffffff", "start", 700))
        out.append(label(x, 48, source, 12, "#8b929e", "start"))
        out.append(f'<svg x="{x}" y="60" width="{col - 20}" height="{thumb_h}" '
                   f'viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid slice">'
                   f"{splash(words[key])}</svg>")
        out.append(label(x, 60 + thumb_h + 32, "the word at real size", 12, "#8b929e", "start"))
        # A window of the real splash, 1:1, centred on the word.
        cx, cy = 960 - (col - 20) / 2, WORD_BASELINE - 110
        out.append(f'<svg x="{x}" y="{60 + thumb_h + 50}" width="{col - 20}" height="{crop_h}" '
                   f'viewBox="{cx} {cy} {col - 20} {crop_h}">{splash(words[key])}</svg>')
    return svg("".join(out), w, h, f"0 0 {w} {h}")


def render(name, markup, w, h):
    src = OUT / f"{name}.svg"
    src.write_text(markup)
    subprocess.run(
        ["rsvg-convert", "-w", str(w), "-h", str(h), "-o", str(OUT / f"{name}.png"), str(src)],
        check=True, env=ENV,
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t)
        # Only the package's fonts exist for this run, so no system face can stand in for one.
        conf = tmp / "fonts.conf"
        conf.write_text(
            '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd">'
            f"<fontconfig><dir>{PKG.resolve()}</dir><cachedir>{tmp}/cache</cachedir></fontconfig>"
        )
        ENV["FONTCONFIG_FILE"] = str(conf)
        for key, f in SIZES.items():
            for variant, swap in (("release", False), ("swap", True)):
                for size in (80, 130):
                    render(f"size-{key}-{variant}-{size}", svg(tile(f, swap), size, size), size, size)
        sheet_h = 300 * len(SIZES) + 60
        render("sheet", sheet(), 1500, sheet_h)
        words = {key: word_image(key, tmp) for key in WORDS}
        for key in WORDS:
            render(f"splash-{key}", svg(splash(words[key]), 1920, 1080, "0 0 1920 1080"), 1920, 1080)
        w, h = 300 * len(WORDS), 60 + 169 + 50 + 150 + 30
        render("splashes", svg(splash_sheet(words), w, h, f"0 0 {w} {h}"), w, h)


if __name__ == "__main__":
    main()

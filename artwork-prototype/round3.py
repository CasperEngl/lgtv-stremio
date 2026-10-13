#!/usr/bin/env python3
"""PROTOTYPE, throwaway: rough icon and splash directions for Rill.

Round 3 of "What do the app's icon and splash look like?" (issue 22). Round 1 chose the waves,
round 2 chose the dark tile and none of its three cuts; this draws five more cuts on dark, each as
vector shapes in a 400x400 box and rendered at the sizes the television expects (80x80 icon,
130x130 large icon, 1920x1080 splash), with two treatments for the "Rill debug" install, plus one
contact sheet that puts every tile in a mock launcher row.

Run: python3 artwork-prototype/round3.py   (needs rsvg-convert; writes artwork-prototype/out/round3/)

Nothing here is cut for the package: pkg/ and assets/ are upstream's and stay unedited.
"""
import pathlib
import subprocess

OUT = pathlib.Path(__file__).parent / "out" / "round3"
FONT = "Adwaita Sans, Noto Sans, sans-serif"

# Each direction: bg and ink are the tile's two colours, accent is optional. `mark` is SVG markup
# in a 400x400 box that uses the placeholders {ink} and {accent}, so the debug treatments can
# recolour it.
WAVE = "C105 {u} 150 {u} 200 {y} S295 {v} 340 {y}"


def wave(y, amp=42, x0=60):
    return f"M{x0} {y} " + WAVE.format(y=y, u=y - amp, v=y + amp)


WAVES = {
    # Three solid waves, heavy to thin.
    "taper": ("4 Taper", f"""
  <g fill="none" stroke="{{ink}}" stroke-linecap="round">
    <path d="{wave(122)}" stroke-width="50"/>
    <path d="{wave(208)}" stroke-width="34"/>
    <path d="{wave(280)}" stroke-width="20"/>
  </g>"""),
    # Two strands crossing each other, like a braided stream.
    "braid": ("5 Braid", f"""
  <g fill="none" stroke="{{ink}}" stroke-width="40" stroke-linecap="round">
    <path d="{wave(200, -90)}" opacity="0.5"/>
    <path d="{wave(200, 90)}"/>
  </g>"""),
    # A solid disc with two waves cut out of it.
    "disc": ("6 Disc", f"""
  <clipPath id="disc"><circle cx="200" cy="200" r="152"/></clipPath>
  <circle cx="200" cy="200" r="152" fill="{{ink}}"/>
  <g fill="none" stroke="{{bg}}" stroke-width="34" clip-path="url(#disc)">
    <path d="{wave(168, 44, 30)} S390 124 420 168"/>
    <path d="{wave(250, 44, 30)} S390 206 420 250"/>
  </g>"""),
    # Three lines that run level and then turn downhill together.
    "bend": ("7 Bend", """
  <g fill="none" stroke="{ink}" stroke-width="34" stroke-linecap="round">
    <path d="M62 96 H196 A136 136 0 0 1 332 232 V338"/>
    <path d="M62 164 H196 A68 68 0 0 1 264 232 V338" opacity="0.7"/>
    <path d="M62 232 H176 Q196 232 196 252 V338" opacity="0.4"/>
  </g>"""),
    # Waves cut to a play triangle. Stremio's logo has a play triangle inside its diamond; this
    # has no diamond, but it is the one cut here that sits near that mark.
    "play": ("8 Play", f"""
  <clipPath id="play"><path d="M112 62 L346 200 L112 338 Z"/></clipPath>
  <g fill="none" stroke="{{ink}}" stroke-width="44" clip-path="url(#play)">
    <path d="{wave(120, 30, 30)} S390 90 420 120"/>
    <path d="{wave(200, 30, 30)} S390 170 420 200"/>
    <path d="{wave(280, 30, 30)} S390 250 420 280"/>
  </g>"""),
}
TILES = {"dark": ("#071a24", "#4fd8c4")}
DIRECTIONS = {
    w: {"name": wname, "bg": bg, "ink": ink, "accent": ink, "mark": m}
    for w, (wname, m) in WAVES.items()
    for bg, ink in TILES.values()
}


def mark(d, swap=False):
    ink, bg = (d["bg"], d["ink"]) if swap else (d["ink"], d["bg"])
    return d["mark"].format(ink=ink, accent=ink, bg=bg)


def tile(d, variant="release"):
    """Inner markup of one 400x400 tile. Variants: release, bar (bottom "DEBUG" bar on the release
    colours) and swap (the two colours trade places, no text)."""
    if variant == "swap":
        return f'<rect width="400" height="400" fill="{d["ink"]}"/>' + mark(d, swap=True)
    body = f'<rect width="400" height="400" fill="{d["bg"]}"/>'
    if variant == "release":
        return body + mark(d)
    # The bar takes the bottom 23 %; the mark shrinks into the space above it. The bar leaves the
    # top-left corner pixel alone, so one tile colour serves both installs.
    return (
        body
        + f'<g transform="translate(48 6) scale(0.76)">{mark(d)}</g>'
        + f'<rect y="308" width="400" height="92" fill="{d["ink"]}"/>'
        + f'<text x="200" y="377" text-anchor="middle" font-family="{FONT}" font-weight="700" '
        f'font-size="66" letter-spacing="5" fill="{d["bg"]}">DEBUG</text>'
    )


def svg(inner, w, h, box="0 0 400 400"):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{box}">{inner}</svg>\n'


def splash(d, word):
    """1920x1080: the tile colour edge to edge, the mark in the middle, with or without "Rill"
    set in a system typeface underneath (the typeface is a guess)."""
    inner = f'<rect width="1920" height="1080" fill="{d["bg"]}"/>'
    if not word:
        return inner + f'<g transform="translate(780 360) scale(0.9)">{mark(d)}</g>'
    return (
        inner
        + f'<g transform="translate(800 300) scale(0.8)">{mark(d)}</g>'
        + f'<text x="960" y="748" text-anchor="middle" font-family="{FONT}" font-weight="700" '
        f'font-size="92" letter-spacing="10" fill="{d["ink"]}">Rill</text>'
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
    """One row per direction: a mock launcher row (blank neighbours, Rill, the two debug
    treatments), then the 130 and 80 files at their real pixel size."""
    row_h, w = 300, 1500
    out = [f'<rect width="{w}" height="{row_h * len(DIRECTIONS) + 60}" fill="#15171c"/>']
    heads = [(420, "Rill"), (610, "Rill debug: bar"), (800, "Rill debug: swapped colours")]
    for i, (key, d) in enumerate(DIRECTIONS.items()):
        y = 60 + i * row_h
        out.append(label(30, y + 20, d["name"], 26, "#ffffff", "start", 700))
        out.append(label(30, y + 46, f'{d["bg"]} / {d["ink"]}', 14, "#8b929e", "start"))
        out.append(launcher_tile(40, y + 70, "#2a2d34", None, "neighbour"))
        out.append(launcher_tile(230, y + 70, "#e9e9ec", None, "neighbour"))
        for (x, _), variant in zip(heads, ("release", "bar", "swap")):
            colour = d["ink"] if variant == "swap" else d["bg"]
            title = "Rill" if variant == "release" else "Rill debug"
            out.append(launcher_tile(x, y + 70, colour, tile(d, variant), title))
        out.append(launcher_tile(990, y + 70, "#2a2d34", None, "neighbour"))
        # Real pixel sizes, release then the two debug treatments.
        for j, variant in enumerate(("release", "bar", "swap")):
            out.append(nested(tile(d, variant), 1190 + j * 100, y + 70, 80))
        out.append(nested(tile(d, "release"), 1190, y + 170, 130))
        out.append(nested(tile(d, "bar"), 1340, y + 170, 130))
    out.append(label(40, 34, "Mock launcher row (icon in LG's 115 px box)", 16, "#8b929e", "start"))
    for x, text in heads:
        out.append(label(x + 85, 54, text, 14, "#8b929e"))
    out.append(label(1190, 34, "Files at real size: 80 px row, 130 px row", 16, "#8b929e", "start"))
    return svg("".join(out), w, row_h * len(DIRECTIONS) + 60, f"0 0 {w} {row_h * len(DIRECTIONS) + 60}")


def render(name, markup, w, h):
    src = OUT / f"{name}.svg"
    src.write_text(markup)
    subprocess.run(
        ["rsvg-convert", "-w", str(w), "-h", str(h), "-o", str(OUT / f"{name}.png"), str(src)],
        check=True,
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for key, d in DIRECTIONS.items():
        for variant in ("release", "bar", "swap"):
            for size in (80, 130):
                render(f"{key}-{variant}-{size}", svg(tile(d, variant), size, size), size, size)
    render("sheet", sheet(), 1500, 300 * len(DIRECTIONS) + 60)


if __name__ == "__main__":
    main()

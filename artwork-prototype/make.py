#!/usr/bin/env python3
"""PROTOTYPE, throwaway: rough icon and splash directions for Rill.

Answers "What do the app's icon and splash look like?" (issue 22). Four directions, each drawn as
vector shapes in a 400x400 box and rendered at the sizes the television expects (80x80 icon,
130x130 large icon, 1920x1080 splash), with two treatments for the "Rill debug" install, plus one
contact sheet that puts every tile in a mock launcher row.

Run: python3 artwork-prototype/make.py   (needs rsvg-convert; writes artwork-prototype/out/)

Nothing here is cut for the package: pkg/ and assets/ are upstream's and stay unedited.
"""
import pathlib
import subprocess

OUT = pathlib.Path(__file__).parent / "out"
FONT = "Adwaita Sans, Noto Sans, sans-serif"

# Each direction: bg and ink are the tile's two colours, accent is optional. `mark` is SVG markup
# in a 400x400 box that uses the placeholders {ink} and {accent}, so the debug treatments can
# recolour it.
DIRECTIONS = {
    "a-current": {
        "name": "A Current",
        "bg": "#071a24",
        "ink": "#4fd8c4",
        "accent": "#4fd8c4",
        "mark": """
  <g fill="none" stroke="{ink}" stroke-width="34" stroke-linecap="round">
    <path d="M60 138 C105 96 150 96 200 138 S295 180 340 138"/>
    <path d="M60 206 C105 164 150 164 200 206 S295 248 340 206" opacity="0.7"/>
    <path d="M60 274 C105 232 150 232 200 274 S250 302 272 290" opacity="0.4"/>
  </g>""",
    },
    "b-stems": {
        "name": "B Stems",
        "bg": "#f3efe6",
        "ink": "#10231f",
        "accent": "#1aa37a",
        "mark": """
  <g fill="none" stroke="{ink}" stroke-width="38" stroke-linecap="round" stroke-linejoin="round">
    <path d="M78 288 V180"/>
    <path d="M78 226 C78 190 106 174 146 180"/>
    <path d="M202 288 V180"/>
    <path d="M262 288 V112"/>
    <path d="M322 112 V258 Q322 288 352 288"/>
  </g>
  <circle cx="202" cy="124" r="23" fill="{accent}"/>""",
    },
    "c-monogram": {
        "name": "C Monogram",
        "bg": "#1e5bff",
        "ink": "#ffffff",
        "accent": "#ffffff",
        "mark": """
  <g fill="none" stroke="{ink}" stroke-width="44" stroke-linecap="round" stroke-linejoin="round">
    <path d="M128 308 V100 H206 A58 58 0 0 1 206 216 H128"/>
    <path d="M196 216 C226 262 250 322 318 296"/>
  </g>""",
    },
    "d-meander": {
        "name": "D Meander",
        "bg": "#0e1f17",
        "ink": "#c6f24e",
        "accent": "#c6f24e",
        "mark": """
  <path d="M236 52 C330 108 96 150 180 204 S318 290 164 348" fill="none" stroke="{ink}"
        stroke-width="46" stroke-linecap="round"/>""",
    },
}


def mark(d, ink=None, accent=None):
    return d["mark"].format(ink=ink or d["ink"], accent=accent or d["accent"])


def tile(d, variant="release"):
    """Inner markup of one 400x400 tile. Variants: release, bar (bottom "DEBUG" bar on the release
    colours) and swap (the two colours trade places, no text)."""
    if variant == "swap":
        return f'<rect width="400" height="400" fill="{d["ink"]}"/>' + mark(d, d["bg"], d["bg"])
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


def splash(key, d):
    """1920x1080: the tile colour edge to edge, the mark in the middle. B is already a wordmark;
    the others get "Rill" set in a system typeface underneath (the typeface is a guess)."""
    inner = f'<rect width="1920" height="1080" fill="{d["bg"]}"/>'
    if key == "b-stems":
        return inner + f'<g transform="translate(760 330)">{mark(d)}</g>'
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
    OUT.mkdir(exist_ok=True)
    for key, d in DIRECTIONS.items():
        for variant in ("release", "bar", "swap"):
            for size in (80, 130):
                render(f"{key}-{variant}-{size}", svg(tile(d, variant), size, size), size, size)
        render(f"{key}-splash", svg(splash(key, d), 1920, 1080, "0 0 1920 1080"), 1920, 1080)
    s = sheet()
    render("sheet", s, 1500, 300 * len(DIRECTIONS) + 60)
    # All four splashes on one page, quarter size each.
    quads = "".join(
        f'<svg x="{(i % 2) * 960}" y="{(i // 2) * 540}" width="960" height="540" '
        f'viewBox="0 0 1920 1080">{splash(k, d)}</svg>'
        for i, (k, d) in enumerate(DIRECTIONS.items())
    )
    render("splashes", svg(quads, 1920, 1080, "0 0 1920 1080"), 1920, 1080)


if __name__ == "__main__":
    main()

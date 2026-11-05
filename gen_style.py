#!/usr/bin/env python3
"""Genereerib mkgmap stiili (style/tsoonid/{polygons,lines}) ja TYP-faili (style/tsoonid.txt)."""
from pathlib import Path

# kood: (polügoni tüüp, joone tüüp, värv, viiru samm px, suund, joone laius, kuvamise resolutsioon, nimi)
ZONES = {
    "reservaat":     (0x04, 0x1e, "#B00000", 4,  "/",  4, 18, "Loodusreservaat"),
    "skv_looduslik": (0x16, 0x1e, "#E00000", 8,  "/",  3, 18, "Sihtkaitsevöönd (looduslik)"),
    "skv_hooldatav": (0x1e, 0x1e, "#FF7A00", 8,  "/",  3, 18, "Sihtkaitsevöönd (hooldatav)"),
    "piiranguvoond": (0x17, 0x1e, "#D4B000", 16, "/",  2, 18, "Piiranguvöönd"),
    "kaitseala":     (None, 0x1c, "#006400", 0,  "",   2, 16, "Kaitseala piir"),
    "hoiuala":       (0x1f, 0x1d, "#8000C0", 16, "/",  2, 18, "Hoiuala"),
    "pysielupaik":   (0x19, 0x1d, "#E000E0", 16, "\\", 2, 20, "Püsielupaik"),
    "yksikobj":      (0x1a, 0x1d, "#900050", 8,  "\\", 2, 20, "Üksikobjekti kaitsetsoon"),
    "rmk":           (0x50, 0x1f, "#0050E0", 16, "\\", 2, 18, "RMK maa"),
}

# teed: kood -> (joone tüüp, resolutsioon, nimi, TYP Xpm read)
ROADS = {
    # pinnastee: helepruun joon tumepruuni äärega
    "pinnastee": (0x0a, 21, "Pinnastee",
                  ['LineWidth=3', 'BorderWidth=1', 'Xpm="0 0 2 0"',
                   '"1 c #D9A85B"', '"2 c #6B4423"']),
    # rada: tumepruun katkendjoon
    "rada": (0x16, 22, "Rada",
             ['Xpm="32 3 2 1"', '"! c #5A3A1A"', '"  c none"',
              *['"' + "!" * 10 + " " * 6 + "!" * 10 + " " * 6 + '"'] * 3]),
}

# joonistusjärjekord (suurem = peal)
DRAW = ["rmk", "kaitseala", "hoiuala", "pysielupaik", "piiranguvoond",
        "skv_hooldatav", "skv_looduslik", "yksikobj", "reservaat"]


def hatch(step, direction):
    rows = []
    for y in range(32):
        row = ""
        for x in range(32):
            d = (x + y) if direction == "/" else (x - y)
            row += "!" if d % step in (0, 1) else " "
        rows.append(f'"{row}"')
    return rows


def main():
    sdir = Path("style/tsoonid")
    pol, lin = [], []
    seen_lines = set()
    typ = ["[_id]", "FID=7337", "ProductCode=1", "CodePage=1252", "[end]", "",
           "[_drawOrder]"]
    for i, code in enumerate(DRAW, start=1):
        pt = ZONES[code][0]
        if pt:
            typ.append(f"Type=0x{pt:03x},{min(i, 8)}")
    typ += ["[end]", ""]

    for code, (pt, lt, color, step, d, width, res, label) in ZONES.items():
        if pt:
            pol.append(f"zp={code} [0x{pt:02x} resolution {res}]")
            typ += ["[_polygon]", f"type=0x{pt:02x}", f"String1=0x00,{label}",
                    "FontStyle=NoLabel (invisible)", 'Xpm="32 32 2 1"',
                    f'"! c {color}"', '"  c none"', *hatch(step, d), "[end]", ""]
        lin.append(f"zl={code} [0x{lt:02x} resolution {res}]")
        if lt in seen_lines:
            continue
        seen_lines.add(lt)
        typ += ["[_line]", f"type=0x{lt:02x}", "UseOrientation=N",
                f"LineWidth={width}", "BorderWidth=0", 'Xpm="0 0 1 0"', f'"1 c {color}"',
                f"String1=0x00,{label}", "FontStyle=SmallFont", "[end]", ""]

    for code, (lt, res, label, xpm) in ROADS.items():
        lin.append(f"zl={code} [0x{lt:02x} resolution {res}]")
        typ += ["[_line]", f"type=0x{lt:02x}", "UseOrientation=N", *xpm,
                f"String1=0x00,{label}", "FontStyle=SmallFont", "[end]", ""]

    (sdir / "polygons").write_text("\n".join(pol) + "\n")
    (sdir / "lines").write_text("\n".join(lin) + "\n")
    Path("style/tsoonid.txt").write_text("\n".join(typ) + "\n", encoding="cp1252")


if __name__ == "__main__":
    main()

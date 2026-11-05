#!/usr/bin/env python3
"""Teisendab data/raw/<piirkond>/ kihid OSM XML-iks, mida mkgmap oskab Garmini kaardiks teha.

Kasutus: .venv/bin/python build.py viljandi|eesti
Tulemus: data/proc/<piirkond>.osm
"""
import json
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

from pyproj import Transformer
from shapely import make_valid
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon, shape
from shapely.ops import transform, unary_union

SIMPLIFY_M = 3.0      # alade lihtsustus meetrites
SIMPLIFY_ROAD_M = 1.5  # teede lihtsustus
MIN_AREA_M2 = 200     # väiksemad tükid visatakse ära

# kihi fail -> (tsooni kood stiilis, kas teha viirutusega pind)
LAYERS = {
    "reservaat": ("reservaat", True),
    "skv_looduslik": ("skv_looduslik", True),
    "skv_hooldatav": ("skv_hooldatav", True),
    "piiranguvoond": ("piiranguvoond", True),
    "kaitseala": ("kaitseala", False),
    "hoiuala": ("hoiuala", True),
    "pysielupaik": ("pysielupaik", True),
    "yksikobj_tsoon": ("yksikobj", True),
    "rmk": ("rmk", True),
}

to_wgs = Transformer.from_crs(3301, 4326, always_xy=True).transform


def polys(geom):
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    if hasattr(geom, "geoms"):
        return [p for g in geom.geoms for p in polys(g)]
    return []


def lines(geom):
    if isinstance(geom, LineString):
        return [geom]
    if isinstance(geom, MultiLineString):
        return list(geom.geoms)
    if hasattr(geom, "geoms"):
        return [p for g in geom.geoms for p in lines(g)]
    return []


def load(path):
    return json.loads(path.read_text())["features"]


class OsmWriter:
    """Kirjutab sõlmed, jooned ja relatsioonid otse ajutistesse failidesse (vähe mälu)."""

    def __init__(self, out):
        self.out = Path(out)
        self.parts = [open(self.out.with_suffix(f".{n}.tmp"), "w", encoding="utf-8")
                      for n in ("n", "w", "r")]
        self.nid = self.wid = self.rid = 0
        self.counts = [0, 0, 0]

    def way(self, coords, tags=None, closed=False):
        coords = list(coords)
        if closed:
            coords = coords[:-1]
        ids = []
        fn = self.parts[0]
        for lon, lat in coords:
            self.nid += 1
            fn.write(f'<node id="{self.nid}" lat="{lat:.7f}" lon="{lon:.7f}"/>\n')
            ids.append(self.nid)
        if closed:
            ids.append(ids[0])
        self.wid += 1
        nd = "".join(f'<nd ref="{i}"/>' for i in ids)
        self.parts[1].write(f'<way id="{self.wid}">{nd}{self._tags(tags or {})}</way>\n')
        self.counts[0] += len(coords)
        self.counts[1] += 1
        return self.wid

    def polygon(self, poly, tags):
        if not poly.interiors:
            return self.way(poly.exterior.coords, tags, closed=True)
        outer = self.way(poly.exterior.coords, closed=True)
        inners = [self.way(r.coords, closed=True) for r in poly.interiors]
        self.rid += 1
        mem = f'<member type="way" ref="{outer}" role="outer"/>' + "".join(
            f'<member type="way" ref="{i}" role="inner"/>' for i in inners)
        self.parts[2].write(f'<relation id="{self.rid}">{mem}'
                            f'{self._tags({**tags, "type": "multipolygon"})}</relation>\n')
        self.counts[2] += 1

    @staticmethod
    def _tags(tags):
        return "".join(f"<tag k={quoteattr(k)} v={quoteattr(str(v))}/>"
                       for k, v in tags.items() if v)

    def close(self):
        for f in self.parts:
            f.close()
        with open(self.out, "w", encoding="utf-8") as o:
            o.write("<?xml version='1.0' encoding='UTF-8'?>\n<osm version='0.6'>\n")
            for f in self.parts:
                p = Path(f.name)
                with open(p, encoding="utf-8") as i:
                    while chunk := i.read(1 << 24):
                        o.write(chunk)
                p.unlink()
            o.write("</osm>\n")


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else "viljandi"
    raw = Path("data/raw") / slug
    whole = slug == "eesti"
    # maakonna puhul lõikame maakonna piiriga; kogu Eesti puhul ei lõika (ka mereosad jäävad)
    county = None if whole else make_valid(shape(load(raw / "maakond.geojson")[0]["geometry"]))

    def clip(g):
        return g if county is None else g.intersection(county)

    # RMK maa = riigi katastriüksused, millel on RMK metsaeraldis
    rmk_ids = set(json.loads((raw / "rmk_tunnused.json").read_text()))
    rmk = [make_valid(shape(f["geometry"])) for f in load(raw / "riigimaa.geojson")
           if f["properties"]["tunnus"] in rmk_ids and f["geometry"]]
    print(f"RMK katastriüksusi: {len(rmk)}")
    rmk_union = unary_union(rmk).buffer(0.5).buffer(-0.5)  # ühenda naabertükid
    del rmk

    out = Path("data/proc") / f"{slug}.osm"
    out.parent.mkdir(parents=True, exist_ok=True)
    osm = OsmWriter(out)
    stats = {}
    for layer, (code, fill) in LAYERS.items():
        if layer == "rmk":
            items = [(rmk_union, "RMK")]
        else:
            items = [(make_valid(shape(f["geometry"])), f["properties"].get("nimi"))
                     for f in load(raw / f"{layer}.geojson") if f["geometry"]]
        n = 0
        for geom, name in items:
            geom = clip(geom).simplify(SIMPLIFY_M, preserve_topology=True)
            for p in polys(geom):
                if p.area < MIN_AREA_M2:
                    continue
                p = transform(to_wgs, p)
                if fill:
                    osm.polygon(p, {"zp": code})
                # äärejoon (eraldi jooned, et nimi ääre peal näha oleks)
                for r in [p.exterior, *p.interiors]:
                    osm.way(r.coords, {"zl": code, "name": name}, closed=True)
                n += 1
        stats[layer] = n

    # pinnasteed ja rajad
    n = {"pinnastee": 0, "rada": 0}
    for f in load(raw / "teed.geojson"):
        if not f["geometry"]:
            continue
        pr = f["properties"]
        code = "rada" if pr["tyyp"] == 70 else "pinnastee"
        g = clip(shape(f["geometry"])).simplify(SIMPLIFY_ROAD_M)
        for ln in lines(g):
            if len(ln.coords) < 2:
                continue
            osm.way(transform(to_wgs, ln).coords, {"zl": code, "name": pr.get("nimetus")})
            n[code] += 1
    stats.update(n)

    osm.close()
    print(stats)
    print(f"{out}: {osm.counts[0]} punkti, {osm.counts[1]} joont, {osm.counts[2]} multipolygoni")


if __name__ == "__main__":
    main()

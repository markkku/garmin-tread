#!/usr/bin/env python3
"""Laeb Keskkonnaportaali / Maa- ja Ruumiameti WFS-ist kihid ühe maakonna kohta.

Kasutus: python3 fetch.py "Viljandi maakond"
Tulemus: data/raw/<maakond>/*.geojson (EPSG:3301)
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

WFS = "https://gsavalik.envir.ee/geoserver/ows"
PAGE = 5000
SORT = {"eelis": "id", "etak": "fid", "kataster": "tunnus", "mr_portaal": "eraldis_id"}

# pinnasteed (kate = pinnas) ja rajad; kergliiklusteed ja kõvakattega rajad välja
TEED_CQL = "(teekate=40 OR tyyp=70) AND tyyp<>80 AND NOT (tyyp=70 AND teekate=10)"

# kiht -> (WFS tüüp, lisafilter)
EELIS = {
    "reservaat": "eelis:kr_reservaat",
    "skv_looduslik": "eelis:kr_looduslik_skv",
    "skv_hooldatav": "eelis:kr_hooldatav_skv",
    "piiranguvoond": "eelis:kr_piirang",
    "kaitseala": "eelis:kr_kaitseala",
    "hoiuala": "eelis:kr_hoiuala",
    "pysielupaik": "eelis:kr_plk",
    "yksikobj_tsoon": "eelis:kr_yksikobjekti_kaitsetsoon",
    "natura_loodusala": "eelis:kr_loodusala",
    "natura_linnuala": "eelis:kr_linnuala",
}


def get(params):
    q = {"service": "WFS", "version": "2.0.0", "request": "GetFeature",
         "outputFormat": "application/json", **params}
    url = WFS + "?" + urllib.parse.urlencode(q)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=300) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            print(f"  viga ({e}), proovin uuesti", file=sys.stderr)
    raise RuntimeError(url)


def fetch_all(type_name, cql=None, props=None):
    feats, start = [], 0
    while True:
        p = {"typeNames": type_name, "count": PAGE, "startIndex": start}
        sort = SORT.get(type_name.split(":")[0])
        if sort:
            p["sortBy"] = sort
        if cql:
            p["CQL_FILTER"] = cql
        if props:
            p["propertyName"] = props
        d = get(p)
        feats += d["features"]
        print(f"  {type_name}: {len(feats)}/{d.get('numberMatched')}")
        if len(d["features"]) < PAGE:
            return feats
        start += PAGE


def save(path, feats):
    fc = {"type": "FeatureCollection",
          "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::3301"}},
          "features": feats}
    path.write_text(json.dumps(fc, ensure_ascii=False))


def bbox(geom):
    xs, ys = [], []

    def walk(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        else:
            for x in c:
                walk(x)
    walk(geom["coordinates"])
    return min(xs), min(ys), max(xs), max(ys)


def both(a, b):
    return " AND ".join(f"({x})" for x in (a, b) if x) or None


def main():
    county = sys.argv[1] if len(sys.argv) > 1 else "Viljandi maakond"
    whole = county.lower() == "eesti"
    slug = "eesti" if whole else county.split()[0].lower()
    out = Path("data/raw") / slug
    out.mkdir(parents=True, exist_ok=True)

    print("Maakonna piir")
    mk = fetch_all("baasandmed:ehak_maakond", cql=None if whole else f"nimi='{county}'")
    save(out / "maakond.geojson", mk)
    if whole:
        bb = None
    else:
        x0, y0, x1, y1 = bbox(mk[0]["geometry"])
        # GeoServeri CQL BBOX EPSG:3301 puhul ootab telgede järjekorda (northing, easting)
        bb = f"BBOX(shape,{y0},{x0},{y1},{x1})"

    for name, t in EELIS.items():
        print(name)
        save(out / f"{name}.geojson", fetch_all(t, cql=bb))

    print("Riigimaa katastriüksused")
    save(out / "riigimaa.geojson", fetch_all(
        "kataster:ky_kehtiv",
        cql=both("omvorm='Riigiomand'", None if whole else f"mk_nimi='{county}'"),
        props="tunnus,geom"))

    print("Pinnasteed ja rajad")
    save(out / "teed.geojson", fetch_all(
        "etak:e_501_tee_j", cql=both(TEED_CQL, bb), props="tyyp,teekate,nimetus,shape"))

    print("RMK eraldised (ainult katastritunnus)")
    rmk = fetch_all("mr_portaal:eraldis-rmk", cql=bb, props="katastri_nr")
    tunnused = sorted({f["properties"].get("katastri_nr") for f in rmk} - {None})
    (out / "rmk_tunnused.json").write_text(json.dumps(tunnused))
    print(f"RMK katastriüksusi: {len(tunnused)}")


if __name__ == "__main__":
    main()

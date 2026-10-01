"""Build the site's map data from OMI zone boundaries + current OMI values.

Inputs
  raw/kmz/<KML_NAME>-2018-2.kml   zone boundaries (OMI 2nd semester 2018, via onData)
  raw/values_<sem>.json           current values (scripts/fetch_values.py)
Outputs
  site/data/<istat>.geojson       one per city, simplified, values joined
  site/data/index.json            city list, colour breaks, semester, unmapped zones

Zones are joined on the OMI zone code (e.g. "C16"): the 2018 KML carries no LinkZona.
Codes present only in the KML were redefined after 2018 (no current values); codes
present only in the values were created after 2018 (no boundary). Both are reported.

Usage: python scripts/build_data.py [semester]   (default: 20252)
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from cities import CITIES

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "data"
FASCIA = {"B": "Centrale", "C": "Semicentrale", "D": "Periferica", "E": "Suburbana", "R": "Extraurbana"}


def parse_coords(text):
    pts = []
    for tok in text.split():
        lon, lat = tok.split(",")[:2]
        pts.append([round(float(lon), 6), round(float(lat), 6)])
    if pts and pts[0] != pts[-1]:
        pts.append(pts[0])
    return pts


def parse_kml(path):
    kml = path.read_text(encoding="utf-8")
    features = []
    for pm in re.findall(r"<Placemark>.*?</Placemark>", kml, re.S):
        code = re.search(r'<Data name="CODZONA">.*?<value>([^<]*)</value>', pm, re.S).group(1).strip()
        polys = []
        for poly in re.findall(r"<Polygon>.*?</Polygon>", pm, re.S):
            outer = re.search(r"<outerBoundaryIs>.*?<coordinates>(.*?)</coordinates>", poly, re.S)
            inners = re.findall(r"<innerBoundaryIs>.*?<coordinates>(.*?)</coordinates>", poly, re.S)
            polys.append([parse_coords(outer.group(1))] + [parse_coords(i) for i in inners])
        geom = ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
                else {"type": "MultiPolygon", "coordinates": polys})
        features.append({"type": "Feature", "properties": {"zona": code}, "geometry": geom})
    return {"type": "FeatureCollection", "features": features}


def simplify(fc):
    """Topology-preserving simplification via mapshaper (no slivers between zones)."""
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp) / "in.json", Path(tmp) / "out.json"
        src.write_text(json.dumps(fc), encoding="utf-8")
        subprocess.run(
            f'npx --yes mapshaper "{src}" -clean -simplify 20% keep-shapes '
            f'-o "{dst}" format=geojson precision=0.00001',
            shell=True, check=True, capture_output=True)
        return json.loads(dst.read_text(encoding="utf-8"))


def pick_row(rows):
    """One residential quotation per zone; see design doc for the order."""
    def find(tip, pred):
        return next((r for r in rows if r["tipologia"] == tip and pred(r)
                     and r["loc_min"] and r["loc_max"]), None)
    normale = lambda r: r["stato"].upper() == "NORMALE"
    prevalent = lambda r: r["stato"].isupper()
    return (find("Abitazioni civili", normale) or find("Abitazioni civili", prevalent)
            or find("Abitazioni di tipo economico", normale)
            or find("Abitazioni di tipo economico", prevalent))


def zone_props(z, sem):
    row = pick_row(z["rows"])
    ottimo = next((r for r in z["rows"] if r["tipologia"] == "Abitazioni civili"
                   and r["stato"].upper() == "OTTIMO" and r["loc_max"]), None)
    p = {
        "zona": z["codzona"], "linkzona": z["linkzona"],
        "fascia": z["codzona"][0], "fascia_label": FASCIA.get(z["codzona"][0], z["fascia_label"]),
        "descr": z["descr"].strip(), "semestre": sem,
        "loc_min": None, "loc_max": None, "loc_mid": None,
    }
    if not z["rows"]:
        p["nonres"] = True  # no residential quotation at all: parks, hospitals, airports...
    if row:
        p.update(loc_min=row["loc_min"], loc_max=row["loc_max"],
                 loc_mid=round((row["loc_min"] + row["loc_max"]) / 2, 2),
                 sup=row["sup_loc"], tipologia=row["tipologia"], stato=row["stato"].upper())
    if ottimo:
        p.update(ott_min=ottimo["loc_min"], ott_max=ottimo["loc_max"])
    return p


# Fixed class breaks in €/m² per month, shared by every city so colours mean the same
# everywhere. Wider steps at the top keep Milano's centre (20-40 €/m²) readable.
BREAKS = [8, 10, 12, 15, 20, 25]


def bbox(fc):
    xs, ys = [], []
    def walk(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        else:
            for x in c:
                walk(x)
    for f in fc["features"]:
        walk(f["geometry"]["coordinates"])
    return [min(xs), min(ys), max(xs), max(ys)]


def main():
    sem = sys.argv[1] if len(sys.argv) > 1 else "20252"
    sem_label = f"{sem[:4]}-S{sem[4]}"
    values = json.loads((ROOT / "raw" / f"values_{sem}.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    index = {"semestre": sem_label, "boundaries": "2018-S2", "breaks": BREAKS, "cities": []}

    for c in CITIES:
        fc = simplify(parse_kml(ROOT / "raw" / "kmz" / f"{c['kml_name']}-2018-2.kml"))
        by_code = {z["codzona"]: z for z in values[c["istat"]]}
        mapped = set()
        for f in fc["features"]:
            code = f["properties"]["zona"]
            if code in by_code:
                f["properties"] = zone_props(by_code[code], sem_label)
                mapped.add(code)
            else:
                f["properties"] = {"zona": code, "fascia": code[0],
                                   "fascia_label": FASCIA.get(code[0], ""), "redefined": True,
                                   "loc_min": None, "loc_max": None, "loc_mid": None}
        unmapped = [zone_props(z, sem_label) for code, z in by_code.items() if code not in mapped]
        redefined = [f["properties"]["zona"] for f in fc["features"] if f["properties"].get("redefined")]
        (OUT / f"{c['istat']}.geojson").write_text(
            json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        b = bbox(fc)
        index["cities"].append({
            "name": c["name"], "istat": c["istat"], "bbox": [round(x, 5) for x in b],
            "zones": len(fc["features"]), "unmapped": unmapped, "redefined": redefined,
        })
        size = (OUT / f"{c['istat']}.geojson").stat().st_size
        print(f"{c['name']}: {len(fc['features'])} polygons, {len(mapped)} with current values, "
              f"redefined={redefined}, unmapped={[u['zona'] for u in unmapped]}, {size/1024:.0f} KB")

    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

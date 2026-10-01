"""Check which comuni still have the same OMI zone codes as the 2018-S2 boundaries.

For each candidate, downloads the province KMZ from onData (cached in raw/kmz/),
lists the current zones from the public OMI consultation service, and reports
how many codes match. A city is a good candidate when nearly all codes match.

Usage: python scripts/check_cities.py [semester]
"""
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import fetch_values as fv

ROOT = Path(__file__).resolve().parent.parent
KMZ_URL = ("https://raw.githubusercontent.com/ondata/quotazioni-immobiliari-agenzia-entrate/"
           "master/kmz/{}")

# (display name, KML comune name, province code, KML province name, belfiore)
CANDIDATES = [
    ("Napoli", "NAPOLI", "NA", "NAPOLI", "F839"),
    ("Genova", "GENOVA", "GE", "GENOVA", "D969"),
    ("Palermo", "PALERMO", "PA", "PALERMO", "G273"),
    ("Venezia", "VENEZIA", "VE", "VENEZIA", "L736"),
    ("Verona", "VERONA", "VR", "VERONA", "L781"),
    ("Padova", "PADOVA", "PD", "PADOVA", "G224"),
    ("Bari", "BARI", "BA", "BARI", "A662"),
    ("Catania", "CATANIA", "CT", "CATANIA", "C351"),
    ("Trieste", "TRIESTE", "TS", "TRIESTE", "L424"),
    ("Brescia", "BRESCIA", "BS", "BRESCIA", "B157"),
    ("Bergamo", "BERGAMO", "BG", "BERGAMO", "A794"),
    ("Parma", "PARMA", "PR", "PARMA", "G337"),
    ("Modena", "MODENA", "MO", "MODENA", "F257"),
    ("Pisa", "PISA", "PI", "PISA", "G702"),
    ("Cagliari", "CAGLIARI", "CA", "CAGLIARI", "B354"),
    ("Trento", "TRENTO", "TN", "TRENTO", "L378"),
    ("Perugia", "PERUGIA", "PG", "PERUGIA", "G478"),
    ("Reggio Emilia", "REGGIO NELL'EMILIA", "RE", "REGGIO EMILIA", "H223"),
    ("Monza", "MONZA", "MB", "MONZA E DELLA BRIANZA", "F704"),
    ("Como", "COMO", "CO", "COMO", "C933"),
    ("Varese", "VARESE", "VA", "VARESE", "L682"),
    ("Salerno", "SALERNO", "SA", "SALERNO", "H703"),
    ("Pescara", "PESCARA", "PE", "PESCARA", "G482"),
    ("Lecce", "LECCE", "LE", "LECCE", "E506"),
    ("Rimini", "RIMINI", "RN", "RIMINI", "H294"),
]


def kmz_names():
    import json
    req = urllib.request.urlopen(
        "https://api.github.com/repos/ondata/quotazioni-immobiliari-agenzia-entrate/contents/kmz")
    return [f["name"] for f in json.load(req)]


def kml_codes(comune, prov, names):
    out = ROOT / "raw" / "kmz" / f"{comune}-2018-2.kml"
    if not out.exists():
        name = next((n for n in names if urllib.parse.unquote(n).endswith(f"di {prov} 2018-2.kmz")), None)
        if not name:
            return None
        kmz = ROOT / "raw" / "kmz" / f"{prov}-2018-2.kmz"
        if not kmz.exists():
            urllib.request.urlretrieve(KMZ_URL.format(urllib.parse.quote(name)), kmz)
        z = zipfile.ZipFile(kmz)
        member = next((m for m in z.namelist() if m.upper() == f"COMUNI/COMUNE DI {comune} 2018-2.KML"), None)
        if not member:
            return None
        out.write_bytes(z.read(member))
    kml = out.read_text(encoding="utf-8")
    return set(re.findall(r'<Data name="CODZONA">.*?<value>([^<]*)</value>', kml, re.S))


def current_codes(pr, co, sem):
    fv.session.get(fv.BASE + "ricerca.htm", timeout=60)
    fv.post("ricerca.php", {"level": "1", "lingua": "IT", "pr": pr})
    html = fv.post("ricerca.php", {"level": "2", "lingua": "IT", "pr": pr, "anno_semestre": sem, "co": co})
    return {label.split("/")[0] for _, label in fv.zone_options(html)}


def main():
    sem = sys.argv[1] if len(sys.argv) > 1 else "20252"
    names = kmz_names()
    for name, comune, pr, prov, co in CANDIDATES:
        old = kml_codes(comune, prov, names)
        if old is None:
            print(f"{name:14} no 2018 KML")
            continue
        cur = current_codes(pr, co, sem)
        match = len(cur & old)
        print(f"{name:14} now={len(cur):3} 2018={len(old):3} match={match:3} "
              f"({match / max(len(cur), 1):.0%})  new={sorted(cur - old)[:8]} gone={sorted(old - cur)[:8]}",
              flush=True)


if __name__ == "__main__":
    main()

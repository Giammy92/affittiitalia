"""Fetch OMI rent quotations for every zone of the configured comuni.

Source: Agenzia delle Entrate public consultation service
("Banca dati delle quotazioni immobiliari", no login). Results are cached as
HTML under raw/omi_cache/<semester>/ so re-runs only fetch what's missing.
Requests are spaced out (DELAY seconds) to keep the load on the service light.

Usage: python scripts/fetch_values.py [semester]   (default: 20252)
"""
import json
import re
import sys
import time
from pathlib import Path

import requests

from cities import CITIES

BASE = "https://www1.agenziaentrate.gov.it/servizi/Consultazione/"
DELAY = 1.5
ROOT = Path(__file__).resolve().parent.parent

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; AffittiItalia/0.1; non-commercial)"})


def post(path, data):
    time.sleep(DELAY)
    r = session.post(BASE + path, data=data, headers={"Referer": BASE + "ricerca.php"}, timeout=60)
    r.raise_for_status()
    r.encoding = "latin1"
    return r.text


def hidden_fields(html):
    return dict(re.findall(r'type="hidden" name="(\w+)" value="([^"]*)"', html))


def zone_options(html):
    m = re.search(r'name="linkzonastrada"[^>]*>(.*?)</select>', html, re.S)
    return re.findall(r'<option value="([^"]*)">([^<]*)', m.group(1)) if m else []


def num(s):
    s = s.strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_result(html):
    """Return the quotation rows of a risultato.php page."""
    start = html.find("Risultato interrogazione")
    m = re.search(r"<table.*?</table>", html[start:], re.S)
    rows = []
    if not m:
        return rows
    for tr in re.findall(r"<tr.*?</tr>", m.group(0), re.S):
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<td.*?</td>", tr, re.S)]
        if len(cells) != 8:
            continue
        tip, stato, cmin, cmax, _csup, lmin, lmax, lsup = cells
        rows.append({
            "tipologia": tip.rstrip("*").strip(),
            "stato": stato,
            "compr_min": num(cmin), "compr_max": num(cmax),
            "loc_min": num(lmin), "loc_max": num(lmax),
            "sup_loc": lsup or None,
        })
    return rows


def fetch_city(pr, co, sem, cache):
    session.get(BASE + "ricerca.htm", timeout=60)
    post("ricerca.php", {"level": "1", "lingua": "IT", "pr": pr})
    html = post("ricerca.php", {"level": "2", "lingua": "IT", "pr": pr, "anno_semestre": sem, "co": co})
    zones = zone_options(html)
    out = []
    for i, (linkzona, label) in enumerate(zones, 1):
        f = cache / f"{linkzona}.html"
        if not f.exists():
            step = post("ricerca.php", {"level": "4", "lingua": "IT", "pr": pr, "co": co,
                                        "anno_semestre": sem, "linkzonastrada": linkzona})
            data = hidden_fields(step)
            data["utilizzo"] = "Residenziale"
            f.write_text(post("risultato.php", data), encoding="utf-8")
            print(f"  [{i}/{len(zones)}] {label[:60]}", flush=True)
        codzona, fascia, descr = (label.split("/", 2) + ["", ""])[:3]
        out.append({"linkzona": linkzona, "codzona": codzona, "fascia_label": fascia,
                    "descr": descr, "rows": parse_result(f.read_text(encoding="utf-8"))})
    return out


def main():
    sem = sys.argv[1] if len(sys.argv) > 1 else "20252"
    cache = ROOT / "raw" / "omi_cache" / sem
    cache.mkdir(parents=True, exist_ok=True)
    result = {}
    for c in CITIES:
        print(f"{c['name']} ({sem})", flush=True)
        result[c["istat"]] = fetch_city(c["pr"], c["belfiore"], sem, cache)
    out = ROOT / "raw" / f"values_{sem}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()

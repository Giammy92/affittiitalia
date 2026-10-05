"""Aggregate anonymous rent reports into site/data/reports.json.

Reports are collected by a Google Form (fields: citta, zona, affitto, mq, locali, arredato)
whose response sheet is published as CSV. This script downloads that CSV, drops implausible
or stale rows and outliers, and publishes per-zone medians only where a zone has at least
MIN_REPORTS reports, so no individual rent can be read off the site.

Usage: python scripts/build_reports.py [csv_url_or_path]
       (default: REPORTS_CSV_URL env var, then the URL in reports_config.json)
"""
import csv
import io
import json
import os
import statistics
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "data" / "reports.json"
CONFIG = ROOT / "scripts" / "reports_config.json"
MIN_REPORTS = 3
MAX_AGE_DAYS = 365
# Plausibility bounds: anything outside is a typo or spam
RENT = (100, 20000)       # €/month
SQM = (10, 500)           # m²
EUR_M2 = (3, 80)          # €/m² per month


def load_csv(source):
    if source.startswith("http"):
        with urllib.request.urlopen(source, timeout=60) as r:
            text = r.read().decode("utf-8")
    else:
        text = Path(source).read_text(encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def num(s):
    s = (s or "").strip().replace("€", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_time(s):
    for fmt in ("%d/%m/%Y %H.%M.%S", "%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s.strip(), fmt).replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            pass
    return None


def clean(rows, valid_zones, now):
    """Yield (city, zone, rent, sqm, furnished) for plausible, recent rows."""
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    for r in rows:
        r = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
        city, zone = r.get("citta", ""), r.get("zona", "").upper()
        rent, sqm = num(r.get("affitto")), num(r.get("mq"))
        when = parse_time(r.get("informazioni cronologiche") or r.get("timestamp") or "")
        if (city, zone) not in valid_zones or rent is None or sqm is None:
            continue
        if when and when < cutoff:
            continue
        if not (RENT[0] <= rent <= RENT[1] and SQM[0] <= sqm <= SQM[1] and EUR_M2[0] <= rent / sqm <= EUR_M2[1]):
            continue
        yield city, zone, rent, sqm, r.get("arredato", "").lower().startswith("s")


def drop_outliers(vals):
    """Tukey fences on €/m² once there are enough reports to estimate them."""
    if len(vals) < 5:
        return vals
    q = statistics.quantiles([v[0] for v in vals], n=4)
    lo, hi = q[0] - 1.5 * (q[2] - q[0]), q[2] + 1.5 * (q[2] - q[0])
    return [v for v in vals if lo <= v[0] <= hi]


def aggregate(rows, valid_zones, now):
    by_zone = {}
    for city, zone, rent, sqm, furnished in clean(rows, valid_zones, now):
        by_zone.setdefault((city, zone), []).append((rent / sqm, rent, sqm, furnished))
    out = {}
    for (city, zone), vals in by_zone.items():
        vals = drop_outliers(vals)
        if len(vals) < MIN_REPORTS:
            continue
        out.setdefault(city, {})[zone] = {
            "n": len(vals),
            "eur_m2": round(statistics.median(v[0] for v in vals), 2),
            "rent": int(round(statistics.median(v[1] for v in vals), -1)),
            "sqm": int(round(statistics.median(v[2] for v in vals))),
        }
    return out


def valid_zone_set():
    index = json.loads((ROOT / "site" / "data" / "index.json").read_text(encoding="utf-8"))
    zones = set()
    for c in index["cities"]:
        fc = json.loads((ROOT / "site" / "data" / f"{c['istat']}.geojson").read_text(encoding="utf-8"))
        zones |= {(c["istat"], f["properties"]["zona"]) for f in fc["features"]}
        zones |= {(c["istat"], u["zona"]) for u in c.get("unmapped", [])}
    return zones


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REPORTS_CSV_URL", "")
    if not source and CONFIG.exists():
        source = json.loads(CONFIG.read_text(encoding="utf-8")).get("csv_url", "")
    if not source:
        print("No reports source configured; nothing to do.")
        return
    now = datetime.now(timezone.utc)
    zones = aggregate(load_csv(source), valid_zone_set(), now)
    data = {"min_reports": MIN_REPORTS, "window_days": MAX_AGE_DAYS, "zones": zones}
    new = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=1)
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    if new != old:
        OUT.write_text(new, encoding="utf-8")
        print(f"updated reports.json: {sum(len(z) for z in zones.values())} zones with ≥{MIN_REPORTS} reports")
    else:
        print("reports.json unchanged")


if __name__ == "__main__":
    main()

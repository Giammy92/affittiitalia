"""Static, indexable pages: one per city (site/<slug>/index.html), plus sitemap.xml.

The map is a JS app that search engines index poorly; these pages carry the same data as
plain HTML tables ("affitti Milano zona per zona") and link into the map for each zone.

Usage: python scripts/build_pages.py   (after build_data.py)
"""
import html
import json
import re
import statistics
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BASE_URL = "https://giammy92.github.io/affittiitalia/"
COLORS = ["#fef0d9", "#fdd49e", "#fdbb84", "#fc8d59", "#ef6548", "#d7301f", "#990000"]
REF_M2 = 65


def slug(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def it_num(n, d=None):
    if d is None:
        d = 0 if float(n).is_integer() else 2
    s = f"{n:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def round10(n):
    return int(round(n / 10.0) * 10)


SMALL = {"di", "del", "della", "dello", "dei", "degli", "delle", "da", "dal", "dalla", "al", "alla",
         "alle", "ai", "agli", "a", "e", "ed", "in", "su", "sul", "sulla", "per", "con"}


def title_case(s):
    s = s.lower().replace("`", "'")
    s = re.sub(r"(^|[\s,.'(\-/:])(\w)", lambda m: m.group(1) + m.group(2).upper(), s)
    # Italian keeps prepositions/articles lowercase except at the start
    return re.sub(r"(?<=\s)(\w+)\b", lambda m: m.group(1).lower() if m.group(1).lower() in SMALL else m.group(1), s)


def short_name(z):
    """Headline-friendly zone name: first segment of the OMI description, cut at a word."""
    label = title_case(z.get("descr") or z["zona"])
    first = re.split(r"\s*[(,]\s*", label)[0].strip() or label
    return first if len(first) <= 38 else first[:36].rsplit(" ", 1)[0] + "…"


def sem_label(s):
    y, h = s.split("-S")
    return f"{h}° semestre {y}"


def color_for(mid, breaks):
    i = 0
    while i < len(breaks) and mid >= breaks[i]:
        i += 1
    return COLORS[i]


def zones_for(city):
    fc = json.loads((SITE / "data" / f"{city['istat']}.geojson").read_text(encoding="utf-8"))
    zones = [f["properties"] for f in fc["features"] if f["properties"].get("loc_mid") is not None]
    zones += [u for u in city.get("unmapped", []) if u.get("loc_mid") is not None]
    return sorted(zones, key=lambda p: p["loc_mid"])


CSS = """
:root{--ink:#14213d;--ink2:#4a5568;--muted:#718096;--line:#e2e8f0;--accent:#e4572e}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:#fff;line-height:1.55}
header,main,footer{max-width:880px;margin:0 auto;padding:0 16px}
header{display:flex;align-items:center;gap:10px;padding-top:16px;padding-bottom:16px;border-bottom:1px solid var(--line)}
header a{color:var(--ink);text-decoration:none;font-size:18px}
header b{color:var(--accent)}
h1{font-size:28px;line-height:1.25;margin:28px 0 8px}
.lead{color:var(--ink2);font-size:17px;margin:0 0 18px}
.cta{display:inline-block;background:var(--ink);color:#fff;text-decoration:none;padding:11px 18px;border-radius:10px;font-weight:600}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:24px 0}
.fact{border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.fact span{display:block;font-size:13px;color:var(--muted)}
.fact b{font-size:20px}
table{width:100%;border-collapse:collapse;font-size:14.5px;margin:12px 0 24px}
th,td{text-align:left;padding:9px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12.5px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.03em}
td.n,th.n{text-align:right;white-space:nowrap}
td a{color:var(--ink);text-decoration:none;font-weight:600}
td a:hover{color:var(--accent)}
i.sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}
.up{color:#9b2c2c}.down{color:#22543d}
.note{font-size:13.5px;color:var(--ink2);background:#fffbea;border:1px solid #f6e05e;border-radius:10px;padding:10px 12px}
.cities{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 28px;padding:0;list-style:none}
.cities a{display:block;border:1px solid var(--line);border-radius:999px;padding:5px 12px;color:var(--ink);text-decoration:none;font-size:14px}
footer{font-size:13px;color:var(--muted);border-top:1px solid var(--line);padding-top:16px;padding-bottom:32px}
footer a{color:var(--accent)}
@media (max-width:600px){.hide-sm{display:none}h1{font-size:23px}}
"""


def page(city, cities, index):
    name = city["name"]
    zones = zones_for(city)
    sem = sem_label(index["semestre"])
    mids = [z["loc_mid"] for z in zones]
    med = statistics.median(mids)
    cheap, dear = zones[0], zones[-1]
    trends = [z["trend"] for z in zones if z.get("trend") is not None]
    med_trend = statistics.median(trends) if trends else None
    s = slug(name)
    url = f"{BASE_URL}{s}/"
    desc = (f"Affitti a {name} zona per zona: valori ufficiali OMI dell'Agenzia delle Entrate "
            f"({sem}). Media {it_num(med, 2)} €/m² al mese, da {it_num(cheap['loc_min'])} a "
            f"{it_num(dear['loc_max'])} €/m². Stima per {REF_M2} m² e mappa interattiva.")

    rows = []
    for z in zones:
        label = title_case(z.get("descr") or "")
        trend = ""
        if z.get("trend") is not None:
            t = z["trend"]
            cls = "up" if t > 0.5 else "down" if t < -0.5 else ""
            trend = f'<span class="{cls}">{"+" if t > 0 else ""}{it_num(t, 1)}%</span>'
        rows.append(
            f'<tr><td><i class="sw" style="background:{color_for(z["loc_mid"], index["breaks"])}"></i>'
            f'<a href="../#{s}/{html.escape(z["zona"])}">{html.escape(label)}</a>'
            f'<br><small style="color:var(--muted)">Zona {html.escape(z["zona"])} · {html.escape(z.get("fascia_label") or "")}</small></td>'
            f'<td class="n">{it_num(z["loc_min"])}–{it_num(z["loc_max"])} €</td>'
            f'<td class="n">{it_num(round10(z["loc_min"] * REF_M2))}–{it_num(round10(z["loc_max"] * REF_M2))} €</td>'
            f'<td class="n hide-sm">{trend}</td></tr>')

    trend_fact = ""
    if med_trend is not None:
        trend_fact = (f'<div class="fact"><span>Variazione mediana dal {sem_label(index["trend_from"])}</span>'
                      f'<b>{"+" if med_trend > 0 else ""}{it_num(med_trend, 1)}%</b></div>')
    others = "".join(f'<li><a href="../{slug(c["name"])}/">{html.escape(c["name"])}</a></li>'
                     for c in cities if c is not city)
    ld = {
        "@context": "https://schema.org", "@type": "Dataset",
        "name": f"Affitti a {name} per zona OMI ({sem})",
        "description": desc, "url": url, "license": "Fonte: Agenzia Entrate - OMI",
        "creator": {"@type": "Organization", "name": "Agenzia delle Entrate – Osservatorio del Mercato Immobiliare"},
        "spatialCoverage": {"@type": "Place", "name": f"{name}, Italia"},
        "temporalCoverage": index["semestre"].replace("-S1", "-01/06").replace("-S2", "-07/12"),
    }
    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Affitti a {html.escape(name)} per zona: prezzi al m² {index["semestre"][:4]} (dati OMI) — AffittiItalia</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="Affitti a {html.escape(name)} zona per zona">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:image" content="{BASE_URL}og.png">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='%2314213d'/><path d='M8 17 16 9l8 8v7h-5v-5h-6v5H8z' fill='%23fc8d59'/></svg>">
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
<header><a href="../">Affitti<b>Italia</b></a></header>
<main>
<h1>Affitti a {html.escape(name)}: quanto costa zona per zona</h1>
<p class="lead">Valori ufficiali di locazione dell'Osservatorio del Mercato Immobiliare (Agenzia delle Entrate), {sem}. Per ogni zona: canone in €/m² al mese e stima per un appartamento di {REF_M2} m².</p>
<a class="cta" href="../#{s}">Apri la mappa di {html.escape(name)} →</a>
<div class="facts">
  <div class="fact"><span>Canone mediano delle zone</span><b>{it_num(med, 2)} €/m²</b></div>
  <div class="fact"><span>Zona più economica</span><b>{html.escape(short_name(cheap))}</b></div>
  <div class="fact"><span>Zona più cara</span><b>{html.escape(short_name(dear))}</b></div>
  {trend_fact}
</div>
<p class="note">Sono valori di riferimento ufficiali, non annunci: nelle zone più richieste i canoni di mercato attuali possono essere superiori del 15–30%. Superficie lorda (commerciale).</p>
<h2>Tutte le zone di {html.escape(name)}, dalla più economica</h2>
<table>
<thead><tr><th>Zona</th><th class="n">€/m² al mese</th><th class="n">{REF_M2} m² al mese</th><th class="n hide-sm">vs {index["trend_from"][:4] if index.get("trend_from") else ""}</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody>
</table>
<h2>Altre città</h2>
<ul class="cities">{others}</ul>
</main>
<footer>Fonte dati: Agenzia Entrate – OMI, {sem}. Progetto indipendente, non affiliato all'Agenzia delle Entrate. <a href="../privacy.html">Privacy</a> · <a href="../">Mappa</a></footer>
</body>
</html>
"""


def main():
    index = json.loads((SITE / "data" / "index.json").read_text(encoding="utf-8"))
    cities = index["cities"]
    urls = [BASE_URL]
    for c in cities:
        out = SITE / slug(c["name"]) / "index.html"
        out.parent.mkdir(exist_ok=True)
        out.write_text(page(c, cities, index), encoding="utf-8")
        urls.append(f"{BASE_URL}{slug(c['name'])}/")
    today = date.today().isoformat()
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
        + "</urlset>\n", encoding="utf-8")
    # Static links from the map page so crawlers find the city pages
    idx = SITE / "index.html"
    links = " · ".join(f'<a href="{slug(c["name"])}/">{html.escape(c["name"])}</a>' for c in cities)
    page_html = re.sub(r"<!-- cities -->.*?<!-- /cities -->",
                       f'<!-- cities --><p class="src">Prezzi per città: {links}</p><!-- /cities -->',
                       idx.read_text(encoding="utf-8"), flags=re.S)
    idx.write_text(page_html, encoding="utf-8")
    print(f"wrote {len(cities)} city pages + sitemap.xml")


if __name__ == "__main__":
    main()

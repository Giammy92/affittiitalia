# AffittiItalia

Map of official rent values by area for Milano, Roma and Bologna, built on OMI quotations
from the Agenzia delle Entrate. Type an address or tap a zone to see the €/m² monthly
range and an estimate for your flat size; set a budget to see which zones fit.

Static site, no backend. Data source: **Agenzia Entrate – OMI**.

## Layout

```
scripts/cities.py        launch cities (OMI province + cadastral code)
scripts/fetch_values.py  current OMI values per zone (public consultation service, cached)
scripts/build_data.py    joins values to zone boundaries → site/data/*.geojson + index.json
raw/kmz/*.kml            OMI zone boundaries, 2nd semester 2018 (via onData)
raw/values_<sem>.json    fetched values
site/                    the website (index.html, app.js, style.css, privacy.html, data/)
```

## Refresh data (every semester)

```bash
python scripts/fetch_values.py 20261   # new semester code: YYYYS
python scripts/build_data.py 20261
```

Requires Python 3 with `requests`, and Node (for `npx mapshaper`).

## Run locally

```bash
python -m http.server 8765 --directory site
```

## Known limits

- Boundaries are from 2018-S2 (latest freely available without login). Values are current.
  Zones redefined since 2018 are flagged on the map; new zones without a boundary are listed
  in the panel. Torino and Firenze were rezoned and are excluded until current boundaries
  are added. To fix this: download current "Perimetri zone OMI" (KML) from the Agenzia's
  *Forniture dati OMI* service (requires SPID/Fisconline) and drop them into `raw/kmz/`.
- OMI values are reference values, typically below current asking rents in hot markets.
- OMI rent values are €/m² per month, usually on gross (commercial) surface.

## Analytics

Set `GOATCOUNTER` in `site/app.js` to a GoatCounter site code to enable cookie-free
analytics (events: `search_submit`, `zone_click`, `zone_from_search`, `budget_used`, `share`).

# AffittiItalia

Map of official rent values by area for 15 Italian cities, built on OMI quotations
from the Agenzia delle Entrate. Type an address or tap a zone to see the €/m² monthly
range, an estimate for your flat size and the change vs. two years earlier; set a budget
to see which zones fit; open the zone list to compare every zone in the city.

Live: https://giammy92.github.io/affittiitalia/

Static site, no backend. Data source: **Agenzia Entrate – OMI**.

## Layout

```
scripts/cities.py        launch cities (OMI province + cadastral code, boundary source)
scripts/check_cities.py  which comuni still match their 2018 zone boundaries
scripts/fetch_values.py  OMI values per zone for a semester (public consultation service, cached)
scripts/build_data.py    joins values to zone boundaries → site/data/*.geojson + index.json
scripts/build_pages.py   static, indexable page per city (site/<city>/) + sitemap.xml
scripts/make_og.py       social preview image site/og.png
scripts/refresh.py       detects a new OMI semester and runs the whole rebuild
scripts/build_reports.py aggregates anonymous rent reports → site/data/reports.json
tests/                   pipeline tests (python -m unittest discover -s tests)
raw/kmz/*.kml            OMI zone boundaries, 2nd semester 2018 (via onData)
raw/geo/*.geojson        newer open-data boundaries (Milano 2024-S2, Comune di Milano, CC BY 4.0)
raw/values_<sem>.json    fetched values
docs/launch-posts.md     launch post drafts + what to watch for
site/                    the website (index.html, app.js, style.css, privacy.html, data/)
```

## Refresh data (every semester)

Automatic: `.github/workflows/refresh-data.yml` runs monthly, and when the Agenzia publishes
a new semester it fetches it, rebuilds, commits and redeploys. Run it by hand from the
Actions tab ("Refresh OMI data"). Manual equivalent:

```bash
python scripts/fetch_values.py 20261          # new semester code: YYYYS
python scripts/fetch_values.py 20241          # same semester two years earlier (trend)
python scripts/build_data.py 20261 20241
python scripts/build_pages.py
python scripts/make_og.py
```

Requires Python 3 with `requests`, and Node (for `npx mapshaper`).

## Run locally

```bash
python -m http.server 8765 --directory site
```

## Known limits

- Boundaries: Milano uses the Comune di Milano's 2024-S2 open data; other cities use
  2018-S2 (latest freely available without login). Values are current. Zones redefined
  since 2018 are flagged; new zones without a boundary are listed in the panel. Torino,
  Firenze, Napoli and others were rezoned and are excluded until current boundaries are
  added: download "Perimetri zone OMI" (KML) from the Agenzia's *Forniture dati OMI*
  service (requires SPID/Fisconline) into `raw/kmz/`.
- OMI values are reference values, typically below current asking rents in hot markets.
- OMI rent values are €/m² per month, usually on gross (commercial) surface.

## Anonymous rent reports ("Quanto paghi tu?")

Visitors can anonymously report their rent from a zone's panel. Reports go to a Google Form;
`.github/workflows/reports.yml` runs `scripts/build_reports.py` every 6 hours, which reads the
form's published CSV, drops implausible/stale rows and outliers, and writes per-zone medians
to `site/data/reports.json` (only zones with ≥3 reports are published).

Setup (once):
1. Create a Google Form with six **short-answer** questions titled exactly:
   `citta`, `zona`, `affitto`, `mq`, `locali`, `arredato`. Settings: don't collect emails.
2. ⋮ menu → **Get pre-filled link** → fill each field with any value → **Get link**.
   The link's `entry.NNN=` ids go into `REPORT_FORM.entries` in `site/app.js`, and the
   form's `…/formResponse` URL into `REPORT_FORM.action`.
3. Responses → **Link to Sheets**; in the sheet, File → Share → **Publish to web** →
   that sheet as **CSV**. Put the URL in `scripts/reports_config.json` (`csv_url`).

## Analytics

Set `GOATCOUNTER` in `site/app.js` to a GoatCounter site code to enable cookie-free
analytics (events: `search_submit`, `zone_click`, `zone_from_search`, `budget_used`, `list_open`, `share`).

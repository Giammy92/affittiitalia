'use strict';

// Optional cookie-free analytics: set to your GoatCounter code (e.g. "affittiitalia") to enable.
const GOATCOUNTER = '';
const COLORS = ['#fef0d9', '#fdd49e', '#fdbb84', '#fc8d59', '#ef6548', '#d7301f', '#990000'];
const ND_COLOR = '#cbd5e0';
const GEOCODE_URL = 'https://nominatim.openstreetmap.org/search';
const PHOTON_URL = 'https://photon.komoot.io/api/';

const $ = (s) => document.querySelector(s);
const state = { index: null, city: null, layer: null, marker: null, selected: null, cache: new Map() };

const eur = (n, d = 0) => n.toLocaleString('it-IT', { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: 'always' });
const eurM2 = (n) => eur(n, n % 1 ? 2 : 0);
const round10 = (n) => Math.round(n / 10) * 10;
const slug = (s) => s.toLowerCase().normalize('NFD').replace(/[^\w]/g, '');
// Italian title case: prepositions/articles stay lowercase unless first
const SMALL = new Set(['di', 'del', 'della', 'dello', 'dei', 'degli', 'delle', 'da', 'dal', 'dalla', 'al', 'alla',
  'alle', 'ai', 'agli', 'a', 'e', 'ed', 'in', 'su', 'sul', 'sulla', 'per', 'con']);
const titleCase = (s) => s.toLowerCase()
  .replace(/(^|[\s,.'`(\-/:])(\p{L})/gu, (m, p, c) => p + c.toUpperCase())
  .replace(/`/g, "'")
  .replace(/(\s)(\p{L}+)(?![\p{L}])/gu, (m, sp, w) => sp + (SMALL.has(w.toLowerCase()) ? w.toLowerCase() : w));
const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function track(name) {
  if (window.goatcounter && window.goatcounter.count) {
    window.goatcounter.count({ path: name, event: true });
  }
}

function sqm() {
  const v = parseFloat($('#sqm').value);
  return v >= 15 && v <= 400 ? v : 65;
}

function colorFor(mid) {
  if (mid == null) return ND_COLOR;
  const b = state.index.breaks;
  let i = 0;
  while (i < b.length && mid >= b[i]) i++;
  return COLORS[i];
}

// ---------- Map ----------
const map = L.map('map', { zoomControl: false, attributionControl: true }).setView([42.5, 12.5], 6);
L.control.zoom({ position: 'bottomright' }).addTo(map);
// OSM standard tiles (no key; light use with attribution). Greyed via CSS so zone colours read clearly.
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · Dati: Agenzia Entrate – OMI',
  maxZoom: 19,
}).addTo(map);

function inBudget(p) {
  const budget = parseFloat($('#budget').value);
  if (!budget || p.loc_min == null) return null;
  return p.loc_min * sqm() <= budget;
}

function styleFor(feature) {
  const p = feature.properties;
  const fit = inBudget(p);
  const selected = state.selected === feature;
  return {
    fillColor: colorFor(p.loc_mid),
    fillOpacity: fit === false ? 0.08 : (p.loc_mid == null ? 0.35 : 0.62),
    color: selected ? '#14213d' : '#ffffff',
    weight: selected ? 3 : 1,
    opacity: fit === false ? 0.4 : 1,
  };
}

function restyle() {
  if (state.layer) state.layer.setStyle(styleFor);
  if (state.selected) state.layer.eachLayer((l) => { if (l.feature === state.selected) l.bringToFront(); });
  updateBudgetMsg();
}

function updateBudgetMsg() {
  const budget = parseFloat($('#budget').value);
  const el = $('#budgetMsg');
  if (!budget || !state.layer) { el.textContent = ''; return; }
  let ok = 0, tot = 0;
  state.layer.eachLayer((l) => {
    const r = inBudget(l.feature.properties);
    if (r !== null) { tot++; if (r) ok++; }
  });
  el.textContent = ok
    ? `In ${ok} zone su ${tot} il canone minimo OMI per ${sqm()} m² sta entro ${eur(budget)} €/mese.`
    : `Nessuna zona rientra in ${eur(budget)} €/mese per ${sqm()} m². Prova a ridurre la superficie.`;
}

function renderLegend() {
  const b = state.index.breaks;
  const labels = [`< ${eurM2(b[0])}`, ...b.slice(0, -1).map((v, i) => `${eurM2(v)}–${eurM2(b[i + 1])}`), `≥ ${eurM2(b[b.length - 1])}`];
  $('#legend').innerHTML = '<h4>€/m² al mese (media zona)</h4>' +
    labels.map((l, i) => `<div class="row"><i style="background:${COLORS[i]}"></i>${l}</div>`).join('') +
    `<div class="row"><i style="background:${ND_COLOR}"></i>n.d.</div>`;
}

// ---------- Geometry ----------
function ringContains(ring, x, y) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}
function polyContains(rings, x, y) {
  return ringContains(rings[0], x, y) && !rings.slice(1).some((h) => ringContains(h, x, y));
}
function featureContains(f, lng, lat) {
  const g = f.geometry;
  return g.type === 'Polygon' ? polyContains(g.coordinates, lng, lat)
    : g.coordinates.some((p) => polyContains(p, lng, lat));
}

// ---------- Panel ----------
// On phones the panel is a bottom sheet: keep the focused zone/point above it.
function sheetPad() {
  const panel = $('#panel');
  return window.innerWidth < 768 && !panel.hidden ? panel.offsetHeight : 0;
}
function focusBounds(bounds) {
  map.fitBounds(bounds, { maxZoom: 15, animate: false, paddingTopLeft: [30, 30], paddingBottomRight: [30, 30 + sheetPad()] });
}
function focusPoint(latlng, zoom) {
  map.setView(latlng, zoom, { animate: false });
  const pad = sheetPad();
  if (pad) map.panBy([0, pad / 2], { animate: false });
}

function openPanel(html) {
  $('#panelBody').innerHTML = html;
  $('#panel').hidden = false;
  document.body.classList.add('panel-open');
}
function closePanel() {
  $('#panel').hidden = true;
  document.body.classList.remove('panel-open');
  state.selected = null;
  restyle();
  history.replaceState(null, '', `#${slug(state.city.name)}`);
}

function zoneHtml(p) {
  const city = state.city;
  const head = `<span class="chip">Zona ${escapeHtml(p.zona)}</span><span class="chip">${escapeHtml(p.fascia_label || '')}</span>`;
  if (p.redefined) {
    const repl = city.unmapped.filter((u) => u.loc_min != null);
    return `${head}<h2>Zona ridefinita dopo il 2018</h2>
      <p class="sub">L'Agenzia delle Entrate ha ridisegnato quest'area: i confini aggiornati non sono ancora disponibili qui.</p>
      ${repl.length ? `<p class="sub" style="margin-top:10px">Zone attuali di ${escapeHtml(city.name)} senza confini sulla mappa:</p>
      <ul class="list">${repl.map((u) => `<li><b>${escapeHtml(u.zona)}</b> · ${escapeHtml(titleCase(u.descr))}<br>${eurM2(u.loc_min)}–${eurM2(u.loc_max)} €/m² al mese</li>`).join('')}</ul>` : ''}`;
  }
  const label = titleCase(p.descr || '');
  const short = label.length > 70 ? label.slice(0, 66).replace(/[,\s]+\S*$/, '') + '…' : label;
  const title = short === label ? `<h2>${escapeHtml(label)}</h2>`
    : `<h2 id="dz">${escapeHtml(short)}</h2><button class="descr-more" id="more">mostra tutto</button>`;
  if (p.loc_min == null) {
    const why = p.nonres
      ? "Zona non residenziale (ad es. parchi, ospedali, aree agricole o servizi): l'OMI non pubblica canoni di locazione per le abitazioni."
      : p.sale_min
        ? `Per questa zona l'OMI pubblica solo i prezzi di vendita: ${eur(p.sale_min)}–${eur(p.sale_max)} €/m² (abitazioni civili, stato normale). Nessun valore di locazione.`
        : 'Dati di locazione non disponibili per questa zona.';
    return `${head}${title}<p class="warn">${why}</p>${meta(p)}`;
  }
  const lorda = p.sup !== 'N';
  return `${head}${title}
    <p class="big">${eurM2(p.loc_min)}–${eurM2(p.loc_max)} € <small>/m² al mese</small></p>
    <p class="sub">Abitazioni ${p.tipologia === 'Abitazioni di tipo economico' ? 'di tipo economico' : 'civili'}, stato normale${p.ott_max ? ` · stato ottimo fino a ${eurM2(p.ott_max)} €/m²` : ''}</p>
    ${trendHtml(p)}
    <div class="estimate">
      <div class="lbl">Stima per <input id="psqm" type="number" min="15" max="400" step="5" value="${sqm()}" aria-label="Superficie"> m² ${lorda ? 'lordi (commerciali)' : 'netti'}</div>
      <div class="val" id="pest"></div>
    </div>
    <p class="warn">Valori di riferimento OMI, non annunci: nelle zone più richieste i canoni di mercato attuali possono essere superiori del 15–30%.</p>
    <button class="share" id="shareBtn">Copia link a questa zona</button>
    ${meta(p)}`;
}

function trendHtml(p) {
  if (p.trend == null) return '';
  const up = p.trend > 0.5, down = p.trend < -0.5;
  const cls = up ? 'up' : down ? 'down' : 'flat';
  const arrow = up ? '▲' : down ? '▼' : '=';
  const sign = p.trend > 0 ? '+' : '';
  return `<p class="trend ${cls}">${arrow} ${sign}${eur(p.trend, 1)}% rispetto al ${escapeHtml(p.trend_from.replace(/(\d{4})-S(\d)/, '$2° semestre $1'))}</p>`;
}

function meta(p) {
  return `<p class="meta">Fonte: Agenzia Entrate – OMI, ${escapeHtml(state.index.semestre.replace('-S', ', semestre '))}. Confini zona: ${escapeHtml(state.city.boundaries.replace('-S', ', sem. '))}.</p>`;
}

function updateEstimate(p) {
  const el = $('#pest');
  if (!el) return;
  const m2 = parseFloat($('#psqm').value) || sqm();
  el.textContent = `${eur(round10(p.loc_min * m2))} – ${eur(round10(p.loc_max * m2))} €/mese`;
}

function selectFeature(f, { zoom = false, source = 'click' } = {}) {
  state.selected = f;
  restyle();
  const p = f.properties;
  openPanel(zoneHtml(p));
  updateEstimate(p);
  const more = $('#more');
  if (more) more.onclick = () => { $('#dz').textContent = titleCase(p.descr); more.remove(); };
  const ps = $('#psqm');
  if (ps) ps.oninput = () => { $('#sqm').value = ps.value; updateEstimate(p); restyle(); };
  const sb = $('#shareBtn');
  if (sb) sb.onclick = async () => {
    try { await navigator.clipboard.writeText(location.href); toast('Link copiato'); } catch { toast(location.href); }
    track('share');
  };
  history.replaceState(null, '', `#${slug(state.city.name)}/${p.zona}`);
  if (zoom) {
    state.layer.eachLayer((l) => { if (l.feature === f) focusBounds(l.getBounds()); });
  }
  track(source === 'search' ? 'zone_from_search' : 'zone_click');
}

// ---------- Zone list (sorted by rent; respects the budget filter) ----------
function openList() {
  const feats = state.cache.get(state.city.istat).features.filter((f) => f.properties.loc_mid != null);
  feats.sort((a, b) => a.properties.loc_mid - b.properties.loc_mid);
  const m2 = sqm();
  const budget = parseFloat($('#budget').value);
  const rows = feats.map((f, i) => {
    const p = f.properties;
    const fit = inBudget(p);
    return `<li class="zrow${fit === false ? ' out' : ''}"><button data-i="${i}">
      <i style="background:${colorFor(p.loc_mid)}"></i>
      <span class="zname"><b>${escapeHtml(p.zona)}</b> ${escapeHtml(titleCase(p.descr || ''))}</span>
      <span class="zval">${eurM2(p.loc_min)}–${eurM2(p.loc_max)} €/m²<small>${eur(round10(p.loc_min * m2))}–${eur(round10(p.loc_max * m2))} €/mese</small></span>
    </button></li>`;
  }).join('');
  state.selected = null;
  restyle();
  openPanel(`<h2>Zone di ${escapeHtml(state.city.name)}</h2>
    <p class="sub">Dalla più economica alla più cara · stima per ${m2} m²${budget ? ` · in grigio le zone oltre ${eur(budget)} €/mese` : ''}</p>
    <ul class="zlist">${rows}</ul>`);
  $('#panelBody').querySelectorAll('.zlist button').forEach((b) => {
    b.onclick = () => selectFeature(feats[+b.dataset.i], { zoom: true, source: 'list' });
  });
  track('list_open');
}

// ---------- Data ----------
async function loadCity(city, zoneCode) {
  state.city = city;
  $('#city').value = city.istat;
  if (state.layer) { map.removeLayer(state.layer); state.layer = null; }
  if (state.marker) { map.removeLayer(state.marker); state.marker = null; }
  $('#panel').hidden = true;
  document.body.classList.remove('panel-open');
  state.selected = null;
  let gj = state.cache.get(city.istat);
  if (!gj) {
    gj = await fetch(`data/${city.istat}.geojson`).then((r) => r.json());
    state.cache.set(city.istat, gj);
  }
  state.layer = L.geoJSON(gj, {
    style: styleFor,
    onEachFeature: (f, l) => {
      const p = f.properties;
      l.bindTooltip(`<b>${escapeHtml(p.zona)}</b> · ${p.loc_min != null ? `${eurM2(p.loc_min)}–${eurM2(p.loc_max)} €/m²` : (p.redefined ? 'zona ridefinita' : 'n.d.')}`,
        { sticky: true, className: 'zone-tip', direction: 'top' });
      l.on('click', () => selectFeature(f));
    },
  }).addTo(map);
  const [w, s, e, n] = city.bbox;
  const f = zoneCode && gj.features.find((x) => x.properties.zona === zoneCode);
  if (!f) map.fitBounds([[s, w], [n, e]], { padding: [20, 20], animate: false });
  restyle();
  if (f) {
    selectFeature(f, { zoom: true, source: 'link' });
  } else {
    history.replaceState(null, '', `#${slug(city.name)}`);
  }
  track(`city_${slug(city.name)}`);
}

// ---------- Geocoding (submit only, bounded to the city; Nominatim usage policy) ----------
const geoCache = new Map();
async function geocode(q, city) {
  const key = `${city.istat}|${q.toLowerCase()}`;
  if (geoCache.has(key)) return geoCache.get(key);
  const [w, s, e, n] = city.bbox;
  let res = null;
  try {
    const u = `${GEOCODE_URL}?format=jsonv2&limit=1&countrycodes=it&bounded=1&viewbox=${w},${n},${e},${s}&q=${encodeURIComponent(q)}`;
    const r = await fetch(u, { headers: { 'Accept-Language': 'it' } });
    if (!r.ok) throw new Error(r.status);
    const j = await r.json();
    if (j[0]) res = { lat: +j[0].lat, lng: +j[0].lon, label: j[0].display_name };
  } catch {
    // Fallback: Photon (komoot), biased to the city centre
    const u = `${PHOTON_URL}?limit=1&lang=it&bbox=${w},${s},${e},${n}&q=${encodeURIComponent(q)}`;
    const r = await fetch(u);
    if (r.ok) {
      const j = await r.json();
      const f = j.features && j.features[0];
      if (f) res = { lat: f.geometry.coordinates[1], lng: f.geometry.coordinates[0], label: f.properties.name };
    }
  }
  geoCache.set(key, res);
  return res;
}

let lastGeocode = 0;
$('#search').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const q = $('#q').value.trim();
  if (!q || !state.city) return;
  const wait = 1100 - (Date.now() - lastGeocode);
  if (wait > 0) await new Promise((r) => setTimeout(r, wait));
  lastGeocode = Date.now();
  track('search_submit');
  let hit;
  try { hit = await geocode(q, state.city); } catch { hit = null; }
  if (!hit) { toast(`Indirizzo non trovato a ${state.city.name}`); return; }
  if (state.marker) map.removeLayer(state.marker);
  state.marker = L.circleMarker([hit.lat, hit.lng], { radius: 8, color: '#14213d', weight: 3, fillColor: '#fff', fillOpacity: 1 }).addTo(map);
  const f = state.cache.get(state.city.istat).features.find((x) => featureContains(x, hit.lng, hit.lat));
  if (!f) {
    focusPoint([hit.lat, hit.lng], 14);
    toast('Indirizzo fuori dalle zone OMI caricate');
    return;
  }
  selectFeature(f, { source: 'search' });
  focusPoint([hit.lat, hit.lng], Math.max(map.getZoom(), 14));
});

// ---------- UI ----------
let toastTimer;
function toast(msg) {
  const t = $('#toast');
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, 3500);
}

$('#closePanel').onclick = closePanel;
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !$('#panel').hidden) closePanel(); });
$('#infoBtn').onclick = () => $('#info').showModal();
$('#listBtn').onclick = openList;
$('#city').onchange = () => loadCity(state.index.cities.find((c) => c.istat === $('#city').value));
let budgetTracked = false;
$('#budget').oninput = () => { restyle(); if (!budgetTracked) { budgetTracked = true; track('budget_used'); } };
$('#sqm').oninput = () => {
  restyle();
  if (state.selected) { const ps = $('#psqm'); if (ps) { ps.value = $('#sqm').value; updateEstimate(state.selected.properties); } }
};

function routeFromHash() {
  const [citySlug, zone] = decodeURIComponent(location.hash.slice(1)).split('/');
  const city = state.index.cities.find((c) => slug(c.name) === citySlug) || state.index.cities[0];
  return { city, zone };
}

window.addEventListener('hashchange', () => {
  const { city, zone } = routeFromHash();
  if (city !== state.city) { loadCity(city, zone); return; }
  const cur = state.selected && state.selected.properties.zona;
  if (zone && zone !== cur) {
    const f = state.cache.get(city.istat).features.find((x) => x.properties.zona === zone);
    if (f) selectFeature(f, { zoom: true, source: 'link' });
  }
});

async function init() {
  if (GOATCOUNTER) {
    const s = document.createElement('script');
    s.async = true;
    s.dataset.goatcounter = `https://${GOATCOUNTER}.goatcounter.com/count`;
    s.src = '//gc.zgo.at/count.js';
    document.head.appendChild(s);
  }
  state.index = await fetch('data/index.json').then((r) => r.json());
  $('#city').innerHTML = state.index.cities.map((c) => `<option value="${c.istat}">${escapeHtml(c.name)}</option>`).join('');
  renderLegend();
  const { city, zone } = routeFromHash();
  await loadCity(city, zone);
  try {
    if (!localStorage.getItem('ai_seen')) { $('#info').showModal(); localStorage.setItem('ai_seen', '1'); }
  } catch { /* storage unavailable: skip the first-visit intro */ }
}
init();

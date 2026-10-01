"""Launch cities. `belfiore` is the cadastral code OMI uses; `istat` names output files.

Only comuni whose current OMI zone codes still (almost) match the 2018-S2 boundaries
are listed; see scripts/check_cities.py. Milano stays first: it's the default city.
"""
CITIES = [
    # Comune di Milano publishes current OMI perimeters (CC BY 4.0) on dati.comune.milano.it
    {"name": "Milano", "kml_name": "MILANO", "pr": "MI", "belfiore": "F205", "istat": "015146",
     "geojson": "raw/geo/milano-2024-2.geojson", "geojson_zone_prop": "Zona", "boundaries": "2024-S2"},
    {"name": "Roma", "kml_name": "ROMA", "pr": "RM", "belfiore": "H501", "istat": "058091"},
    {"name": "Bari", "kml_name": "BARI", "pr": "BA", "belfiore": "A662", "istat": "072006"},
    {"name": "Bologna", "kml_name": "BOLOGNA", "pr": "BO", "belfiore": "A944", "istat": "037006"},
    {"name": "Cagliari", "kml_name": "CAGLIARI", "pr": "CA", "belfiore": "B354", "istat": "092009"},
    {"name": "Catania", "kml_name": "CATANIA", "pr": "CT", "belfiore": "C351", "istat": "087015"},
    {"name": "Genova", "kml_name": "GENOVA", "pr": "GE", "belfiore": "D969", "istat": "010025"},
    {"name": "Padova", "kml_name": "PADOVA", "pr": "PD", "belfiore": "G224", "istat": "028060"},
    {"name": "Palermo", "kml_name": "PALERMO", "pr": "PA", "belfiore": "G273", "istat": "082053"},
    {"name": "Pescara", "kml_name": "PESCARA", "pr": "PE", "belfiore": "G482", "istat": "068028"},
    {"name": "Pisa", "kml_name": "PISA", "pr": "PI", "belfiore": "G702", "istat": "050026"},
    {"name": "Rimini", "kml_name": "RIMINI", "pr": "RN", "belfiore": "H294", "istat": "099014"},
    {"name": "Trento", "kml_name": "TRENTO", "pr": "TN", "belfiore": "L378", "istat": "022205"},
    {"name": "Trieste", "kml_name": "TRIESTE", "pr": "TS", "belfiore": "L424", "istat": "032006"},
    {"name": "Venezia", "kml_name": "VENEZIA", "pr": "VE", "belfiore": "L736", "istat": "027042"},
]

"""Launch cities. `belfiore` is the cadastral code OMI uses; `istat` names output files;
`subito` is the region/province/comune path of Subito.it's rental search for the city.

Only comuni whose current OMI zone codes still (almost) match the 2018-S2 boundaries
are listed; see scripts/check_cities.py. Milano stays first: it's the default city.
"""
CITIES = [
    # Comune di Milano publishes current OMI perimeters (CC BY 4.0) on dati.comune.milano.it
    {"name": "Milano", "kml_name": "MILANO", "pr": "MI", "belfiore": "F205", "istat": "015146", "subito": "lombardia/milano/milano",
     "geojson": "raw/geo/milano-2024-2.geojson", "geojson_zone_prop": "Zona", "boundaries": "2024-S2"},
    {"name": "Roma", "kml_name": "ROMA", "pr": "RM", "belfiore": "H501", "istat": "058091", "subito": "lazio/roma/roma"},
    {"name": "Bari", "kml_name": "BARI", "pr": "BA", "belfiore": "A662", "istat": "072006", "subito": "puglia/bari/bari"},
    {"name": "Bologna", "kml_name": "BOLOGNA", "pr": "BO", "belfiore": "A944", "istat": "037006", "subito": "emilia-romagna/bologna/bologna"},
    {"name": "Cagliari", "kml_name": "CAGLIARI", "pr": "CA", "belfiore": "B354", "istat": "092009", "subito": "sardegna/cagliari/cagliari"},
    {"name": "Catania", "kml_name": "CATANIA", "pr": "CT", "belfiore": "C351", "istat": "087015", "subito": "sicilia/catania/catania"},
    {"name": "Genova", "kml_name": "GENOVA", "pr": "GE", "belfiore": "D969", "istat": "010025", "subito": "liguria/genova/genova"},
    {"name": "Padova", "kml_name": "PADOVA", "pr": "PD", "belfiore": "G224", "istat": "028060", "subito": "veneto/padova/padova"},
    {"name": "Palermo", "kml_name": "PALERMO", "pr": "PA", "belfiore": "G273", "istat": "082053", "subito": "sicilia/palermo/palermo"},
    {"name": "Pescara", "kml_name": "PESCARA", "pr": "PE", "belfiore": "G482", "istat": "068028", "subito": "abruzzo/pescara/pescara"},
    {"name": "Pisa", "kml_name": "PISA", "pr": "PI", "belfiore": "G702", "istat": "050026", "subito": "toscana/pisa/pisa"},
    {"name": "Rimini", "kml_name": "RIMINI", "pr": "RN", "belfiore": "H294", "istat": "099014", "subito": "emilia-romagna/rimini/rimini"},
    {"name": "Trento", "kml_name": "TRENTO", "pr": "TN", "belfiore": "L378", "istat": "022205", "subito": "trentino-alto-adige/trento/trento"},
    {"name": "Trieste", "kml_name": "TRIESTE", "pr": "TS", "belfiore": "L424", "istat": "032006", "subito": "friuli-venezia-giulia/trieste/trieste"},
    {"name": "Venezia", "kml_name": "VENEZIA", "pr": "VE", "belfiore": "L736", "istat": "027042", "subito": "veneto/venezia/venezia"},
]

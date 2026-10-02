"""Pipeline tests. Run: python -m unittest discover -s tests"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_data  # noqa: E402
import build_pages  # noqa: E402
import fetch_values  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def row(tip, stato, lmin, lmax, cmin=1000.0, cmax=2000.0, sup="L"):
    return {"tipologia": tip, "stato": stato, "compr_min": cmin, "compr_max": cmax,
            "loc_min": lmin, "loc_max": lmax, "sup_loc": sup}


class ParseResult(unittest.TestCase):
    def test_parses_real_result_page(self):
        html = (FIXTURES / "risultato_MI00004772.html").read_text(encoding="utf-8")
        rows = fetch_values.parse_result(html)
        self.assertEqual(rows[0], row("Abitazioni civili", "NORMALE", 13.5, 18.0, 4200.0, 6400.0))
        self.assertEqual([r["tipologia"] for r in rows], ["Abitazioni civili", "Abitazioni civili", "Box"])

    def test_page_without_table_gives_no_rows(self):
        self.assertEqual(fetch_values.parse_result("<html>Risultato interrogazione</html>"), [])

    def test_italian_numbers(self):
        self.assertEqual(fetch_values.num("1.250,5"), 1250.5)
        self.assertIsNone(fetch_values.num(""))


class PickRow(unittest.TestCase):
    def test_prefers_civili_normale(self):
        rows = [row("Abitazioni civili", "Ottimo", 20, 30), row("Abitazioni civili", "NORMALE", 10, 15)]
        self.assertEqual(build_data.pick_row(rows)["loc_min"], 10)

    def test_falls_back_to_prevalent_then_economico(self):
        self.assertEqual(build_data.pick_row([row("Abitazioni civili", "SCADENTE", 7, 9)])["loc_min"], 7)
        rows = [row("Abitazioni civili", "NORMALE", None, None),
                row("Abitazioni di tipo economico", "NORMALE", 6, 8)]
        self.assertEqual(build_data.pick_row(rows)["tipologia"], "Abitazioni di tipo economico")

    def test_sale_only_zone_has_no_rent_row(self):
        self.assertIsNone(build_data.pick_row([row("Abitazioni civili", "NORMALE", None, None)]))


class ZoneProps(unittest.TestCase):
    def zone(self, rows):
        return {"codzona": "C16", "linkzona": "MI1", "fascia_label": "Semicentrale", "descr": "X", "rows": rows}

    def test_midpoint_and_trend(self):
        p = build_data.zone_props(self.zone([row("Abitazioni civili", "NORMALE", 12, 18)]), "2025-S2")
        self.assertEqual(p["loc_mid"], 15)
        build_data.add_trend(p, {"MI1": (12.0, "Abitazioni civili")}, "2023-S2")
        self.assertEqual(p["trend"], 25.0)

    def test_no_trend_across_different_tipologia(self):
        p = build_data.zone_props(self.zone([row("Abitazioni civili", "NORMALE", 12, 18)]), "2025-S2")
        build_data.add_trend(p, {"MI1": (12.0, "Abitazioni di tipo economico")}, "2023-S2")
        self.assertNotIn("trend", p)

    def test_non_residential_and_sale_only_flags(self):
        self.assertTrue(build_data.zone_props(self.zone([]), "2025-S2")["nonres"])
        p = build_data.zone_props(self.zone([row("Abitazioni civili", "NORMALE", None, None, 2800, 3900)]), "2025-S2")
        self.assertEqual((p["sale_min"], p["loc_min"]), (2800, None))


class Formatting(unittest.TestCase):
    def test_italian_title_case(self):
        self.assertEqual(build_pages.title_case("SANTA MARIA DI GALERIA (VIA DI SANTA MARIA)"),
                         "Santa Maria di Galeria (Via di Santa Maria)")
        self.assertEqual(build_pages.title_case("DI FRONTE AL PORTO"), "Di Fronte al Porto")

    def test_italian_numbers(self):
        self.assertEqual(build_pages.it_num(1170), "1.170")
        self.assertEqual(build_pages.it_num(13.5), "13,50")


if __name__ == "__main__":
    unittest.main()

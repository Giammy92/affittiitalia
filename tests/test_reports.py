"""Tests for anonymous rent report aggregation."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_reports as br  # noqa: E402

NOW = datetime(2026, 10, 5, tzinfo=timezone.utc)
ZONES = {("015146", "C16"), ("015146", "B12")}


def row(zona="C16", affitto="1200", mq="60", when="01/10/2026 10.00.00", citta="015146"):
    return {"Informazioni cronologiche": when, "citta": citta, "zona": zona,
            "affitto": affitto, "mq": mq, "locali": "2", "arredato": "Sì"}


class Aggregate(unittest.TestCase):
    def test_needs_minimum_reports(self):
        self.assertEqual(br.aggregate([row(), row()], ZONES, NOW), {})
        out = br.aggregate([row(), row(affitto="1300"), row(affitto="1100")], ZONES, NOW)
        self.assertEqual(out["015146"]["C16"]["n"], 3)
        self.assertEqual(out["015146"]["C16"]["eur_m2"], 20.0)

    def test_drops_implausible_stale_and_unknown(self):
        rows = [row(), row(), row(),
                row(affitto="12"),                      # typo
                row(affitto="9000", mq="20"),           # 450 €/m²
                row(when="01/01/2024 10.00.00"),        # older than 12 months
                row(zona="Z99"), row(citta="999999")]   # not a real zone
        self.assertEqual(br.aggregate(rows, ZONES, NOW)["015146"]["C16"]["n"], 3)

    def test_outliers_removed_with_enough_reports(self):
        rows = [row(affitto=str(a)) for a in (1150, 1200, 1250, 1180, 1220)] + [row(affitto="4000")]
        self.assertEqual(br.aggregate(rows, ZONES, NOW)["015146"]["C16"]["n"], 5)

    def test_number_formats(self):
        self.assertEqual(br.num("1.250,00 €"), 1250.0)
        self.assertEqual(br.num("1250"), 1250.0)
        self.assertIsNone(br.num("mille"))


if __name__ == "__main__":
    unittest.main()

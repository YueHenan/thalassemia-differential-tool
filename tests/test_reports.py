import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from database import ScreeningDatabase
from prediction_core import PredictionModel
from reporting import create_record, export_record, report_text


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.model = PredictionModel.load()
        self.record = create_record(self.model, dict(RBC=4.5, Hb=100, MCV=68, MCH=22, RDW=16), hb_unit="g/L",
                                    patient={"name": "=SYNTHETIC_TEST", "id": "NOT_A_PATIENT", "test_date": "2026-10-26"})

    def tearDown(self):
        self.temp.cleanup()

    def test_report_retains_model_units_and_exact_threshold(self):
        for language in ("en", "zh"):
            text = report_text(self.record, language)
            self.assertIn(format(self.model.threshold, ".17g"), text)
            self.assertIn(self.model.equation(), text)
            self.assertIn(self.model.sha256, text)
            self.assertIn("100 g/L", text)
            self.assertIn("10 g/dL", text)
            self.assertIn(self.model.version, text)

    def test_SQLite_roundtrip_preserves_complete_prediction(self):
        database = ScreeningDatabase(self.directory / "synthetic.sqlite3")
        identity = database.save_record(self.record)
        self.assertEqual(database.get_record(identity), self.record)
        self.assertEqual(database.get_all_records()[0]["prediction"], self.record["prediction"])

    def test_json_csv_text_agree_and_spreadsheet_text_is_literal(self):
        for extension in (".json", ".csv", ".txt"):
            export_record(self.record, self.directory / ("report" + extension))
        loaded = json.loads((self.directory / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(loaded, self.record)
        with (self.directory / "report.csv").open(encoding="utf-8-sig", newline="") as stream:
            row = next(csv.DictReader(stream))
        self.assertEqual(float(row["probability"]), self.record["prediction"]["probability"])
        self.assertEqual(float(row["probability_threshold"]), self.model.threshold)
        self.assertEqual(row["model_sha256"], self.model.sha256)
        self.assertEqual(row["patient_name"], "'=SYNTHETIC_TEST")
        self.assertIn(self.model.equation(), (self.directory / "report.txt").read_text(encoding="utf-8"))

    @unittest.skipUnless(importlib.util.find_spec("openpyxl"), "openpyxl not installed")
    def test_excel_contains_complete_versioned_snapshot(self):
        from openpyxl import load_workbook
        path = self.directory / "report.xlsx"
        export_record(self.record, path, "zh")
        book = load_workbook(path, data_only=False)
        rows = list(book["Structured results"].values)
        mapped = dict(zip(rows[0], rows[1]))
        self.assertAlmostEqual(mapped["probability"], self.record["prediction"]["probability"], places=14)
        self.assertEqual(mapped["model_version"], self.model.version)
        self.assertEqual(mapped["patient_name"], "'=SYNTHETIC_TEST")
        snapshot = json.loads("\n".join(row[0] for row in book["JSON snapshot"].values))
        self.assertEqual(snapshot, self.record)

    @unittest.skipUnless(importlib.util.find_spec("reportlab"), "reportlab not installed")
    def test_PDF_both_languages(self):
        for language in ("en", "zh"):
            path = self.directory / f"report_{language}.pdf"
            export_record(self.record, path, language)
            self.assertTrue(path.read_bytes().startswith(b"%PDF-"))
            self.assertGreater(path.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()

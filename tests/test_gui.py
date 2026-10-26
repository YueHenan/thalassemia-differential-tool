import os
from pathlib import Path
import tempfile
import unittest


class GuiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import tkinter as tk
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception as exc:
            if os.environ.get("REQUIRE_GUI_TESTS") == "1":
                raise
            raise unittest.SkipTest(f"Tk display unavailable: {exc}")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "root"):
            cls.root.destroy()

    def setUp(self):
        from thalassemia_differential_gui import DifferentialGUI
        self.temp = tempfile.TemporaryDirectory()
        self.app = DifferentialGUI(self.root, db_path=Path(self.temp.name) / "synthetic.sqlite3")
        self.app.load_example()

    def tearDown(self):
        for child in self.root.winfo_children():
            child.destroy()
        self.temp.cleanup()

    def test_calculate_translate_save_and_export_same_snapshot(self):
        from database import ScreeningDatabase
        record = self.app.calculate(show_errors=False)
        self.root.update()
        self.assertIn(record["prediction"]["model_version"], self.app.result_text.get("1.0", "end"))
        self.app.toggle_language()
        self.root.update()
        text = self.app.result_text.get("1.0", "end")
        self.assertIn("Research use only", text)
        self.assertLess(text.index("Combined OR rule"), text.index("Inputs (canonical units)"))
        self.assertIn(format(self.app.model.threshold, ".17g"), text)
        self.assertEqual(self.app.current_record, record)
        identity = self.app.save_record(show_messages=False)
        saved = ScreeningDatabase(self.app.db_path).get_record(identity)
        self.assertEqual(saved, record)
        path = Path(self.temp.name) / "gui_report.json"
        self.app.export_result(path, show_messages=False)
        self.assertTrue(path.exists())

    def test_changed_input_or_patient_cannot_export_stale_result(self):
        self.app.calculate(show_errors=False)
        self.app.input_vars["Hb"].set("9")
        self.assertIsNone(self.app.current_record)
        self.assertEqual(str(self.app.btn_export["state"]), "disabled")
        self.app.calculate(show_errors=False)
        self.app.patient_vars["name"].set("SYNTHETIC")
        self.assertIsNone(self.app.current_record)

    def test_Hb_unit_change_is_explicit_and_recalculates(self):
        original = self.app.calculate(show_errors=False)["prediction"]
        self.app.input_vars["Hb"].set("100")
        self.app.hb_unit.set("g/L")
        converted = self.app.calculate(show_errors=False)["prediction"]
        self.assertEqual(original, converted)
        self.app.hb_unit.set("g/dL")
        with self.assertRaisesRegex(ValueError, "Hb"):
            self.app.calculate(show_errors=False)
        self.assertIsNone(self.app.current_record)

    def test_Hb89_requires_explicit_g_L_and_keeps_guardrails(self):
        self.app.input_vars["Hb"].set("89")
        with self.assertRaisesRegex(ValueError, "Hb"):
            self.app.calculate(show_errors=False)
        self.app.hb_unit.set("g/L")
        self.assertEqual(self.app.calculate(show_errors=False)["prediction"]["inputs"]["Hb"], 8.9)
        for name, invalid in {"MCV": "151", "RBC": "11", "MCH": "51", "RDW": "51"}.items():
            self.app.load_example()
            self.app.input_vars[name].set(invalid)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, name):
                self.app.calculate(show_errors=False)

    def test_clear_disables_actions_and_removes_result(self):
        self.app.calculate(show_errors=False)
        self.app.clear_inputs()
        self.assertIsNone(self.app.current_record)
        self.assertTrue(all(variable.get() == "" for variable in self.app.input_vars.values()))
        self.assertEqual(str(self.app.btn_save["state"]), "disabled")


if __name__ == "__main__":
    unittest.main()

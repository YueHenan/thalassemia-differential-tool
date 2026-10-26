#!/usr/bin/env python3
"""Bilingual research GUI, version 2.0.0; model parameters come only from model.json.

Retains optional patient fields, explicit calculation, local SQLite saving, bilingual
reports and PDF/Excel/CSV/text export. Numerical work is isolated in prediction_core.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys
import sqlite3

from prediction_core import APP_VERSION, FEATURES, Inputs, PredictionModel
from reporting import RESEARCH_NOTICE, benchmark_text, create_record, export_record, report_text

LABELS = {
    "zh": {
        "title": "THA/IDA 研究计算器", "patient": "患者信息（可选）", "inputs": "血常规输入",
        "name": "姓名", "id": "患者ID", "age": "年龄（岁）", "gender": "性别",
        "hometown": "籍贯", "test_date": "检测日期", "calculate": "计算", "save": "保存到本机",
        "export": "导出报告", "clear": "清空", "example": "合成示例", "language": "English",
        "error": "输入或操作失败", "success": "完成", "saved": "记录已保存", "exported": "报告已导出",
        "results": "研究计算结果", "stale": "输入已变化，请重新计算。",
        "empty": "请输入血常规结果并确认Hb单位，然后点击计算。",
        "unit_note": "Hb必须明确选择g/dL或g/L；仅选g/L时除以10。RDW按百分数输入，例如20%。不自动猜测或修正数值。",
        "development": "开发队列表观效能（不是外部验证）", "research": "仅供研究；不可替代确诊检查",
    },
    "en": {
        "title": "THA/IDA research calculator", "patient": "Patient information (optional)", "inputs": "CBC inputs",
        "name": "Name", "id": "Patient ID", "age": "Age (years)", "gender": "Sex", "hometown": "Hometown",
        "test_date": "Test date", "calculate": "Calculate", "save": "Save locally", "export": "Export report",
        "clear": "Clear", "example": "Synthetic example", "language": "中文", "error": "Input or operation failed",
        "success": "Done", "saved": "Record saved", "exported": "Report exported", "results": "Research calculation",
        "stale": "Inputs changed. Calculate again before saving or exporting.",
        "empty": "Enter CBC results, check the Hb unit, then select Calculate.",
        "unit_note": "Choose Hb g/dL or g/L explicitly; only g/L is divided by 10. Enter RDW as percentage points, e.g. 20. No value-based unit correction is applied.",
        "development": "Development-cohort apparent performance (not external validation)",
        "research": "Research only; does not replace confirmatory investigations",
    },
}


# Entry guardrails retained from v1, applied after explicit Hb-unit conversion.
# They are not model calibration limits or a validation of clinical suitability.
GUI_INPUT_RANGES = {"RBC": (1, 10), "Hb": (2, 25), "MCV": (30, 150),
                    "MCH": (10, 50), "RDW": (5, 50)}


def validate_gui_inputs(values, hb_unit, lang="en"):
    normalised = Inputs.from_mapping(values, hb_unit=hb_unit).values()
    errors = []
    for name, (minimum, maximum) in GUI_INPUT_RANGES.items():
        if not minimum <= normalised[name] <= maximum:
            unit = " g/dL" if name == "Hb" else ""
            if lang == "zh":
                errors.append(f"{name} 超出录入范围 {minimum}–{maximum}{unit}；请核对数值和单位。")
            else:
                errors.append(f"{name} is outside the entry range {minimum}–{maximum}{unit}; check the value and unit.")
    if errors:
        raise ValueError("\n".join(errors))
    return normalised


class DifferentialGUI:
    def __init__(self, root, *, model: PredictionModel | None = None, db_path: str | Path | None = None):
        import tkinter as tk
        from tkinter import ttk
        self.root = root
        self.model = model or PredictionModel.load()
        self.db_path = db_path
        self.lang = "zh"
        self.current_record = None
        self.current_record_id = None
        self.input_vars = {name: tk.StringVar(root) for name in FEATURES}
        self.hb_unit = tk.StringVar(root, value="g/dL")
        self.patient_vars = {key: tk.StringVar(root) for key in ("name", "id", "age", "gender", "hometown", "test_date")}
        self.patient_vars["test_date"].set(date.today().isoformat())
        for variable in [*self.input_vars.values(), self.hb_unit, *self.patient_vars.values()]:
            variable.trace_add("write", self.invalidate_result)
        root.geometry("1100x860")
        root.minsize(820, 640)
        style = ttk.Style(root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Title.TLabel", font=("Arial", 16, "bold"))
        style.configure("Research.TLabel", foreground="#8a3d10")
        self.create_widgets()

    @property
    def t(self):
        return LABELS[self.lang]

    def create_widgets(self):
        import tkinter as tk
        from tkinter import ttk, scrolledtext
        for child in self.root.winfo_children():
            child.destroy()
        self.root.title(f"{self.t['title']} · v{APP_VERSION}")
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(6, weight=1)
        header = ttk.Frame(frame)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=f"{self.t['title']} · v{self.model.version}", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(header, text=self.t["language"], command=self.toggle_language).grid(row=0, column=1, sticky="e")
        ttk.Label(frame, text=self.t["research"], style="Research.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 2))
        benchmark = benchmark_text(self.model.performance(), self.lang)
        ttk.Label(frame, text=f"{self.t['development']}: {benchmark}", wraplength=1000).grid(row=2, column=0, sticky="w", pady=(0, 8))

        patient = ttk.LabelFrame(frame, text=self.t["patient"], padding=8)
        patient.grid(row=3, column=0, sticky="ew", pady=4)
        self.patient_entries = {}
        for index, (key, variable) in enumerate(self.patient_vars.items()):
            row, col = divmod(index, 3)
            patient.columnconfigure(col * 2 + 1, weight=1)
            ttk.Label(patient, text=self.t[key]).grid(row=row, column=col * 2, sticky="w", padx=(0, 4), pady=3)
            if key == "gender":
                entry = ttk.Combobox(patient, textvariable=variable, values=("", "男 / Male", "女 / Female", "其他 / Other"), width=18)
            else:
                entry = ttk.Entry(patient, textvariable=variable, width=18)
            entry.grid(row=row, column=col * 2 + 1, sticky="ew", padx=(0, 12), pady=3)
            self.patient_entries[key] = entry

        inputs = ttk.LabelFrame(frame, text=self.t["inputs"], padding=8)
        inputs.grid(row=4, column=0, sticky="ew", pady=5)
        self.entries = {}
        units = {"RBC": "10^12/L", "MCV": "fL", "MCH": "pg", "RDW": "%"}
        for index, name in enumerate(FEATURES):
            cell = ttk.Frame(inputs)
            cell.grid(row=0, column=index, sticky="ew", padx=(0, 12))
            inputs.columnconfigure(index, weight=1)
            ttk.Label(cell, text=name).pack(anchor="w")
            entry = ttk.Entry(cell, textvariable=self.input_vars[name], width=10)
            entry.pack(fill="x", pady=3)
            self.entries[name] = entry
            if name == "Hb":
                ttk.Combobox(cell, textvariable=self.hb_unit, values=("g/dL", "g/L"), state="readonly", width=9).pack(anchor="w")
            else:
                ttk.Label(cell, text=units[name]).pack(anchor="w")
        ttk.Label(inputs, text=self.t["unit_note"], wraplength=980).grid(row=1, column=0, columnspan=5, sticky="w", pady=(8, 0))

        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, sticky="ew", pady=5)
        for key, callback in [("calculate", self.calculate), ("save", self.save_record), ("export", self.export_result),
                              ("clear", self.clear_inputs), ("example", self.load_example)]:
            button = ttk.Button(buttons, text=self.t[key], command=callback)
            button.pack(side="left", padx=(0, 8))
            setattr(self, "btn_" + key, button)
        result_frame = ttk.LabelFrame(frame, text=self.t["results"], padding=6)
        result_frame.grid(row=6, column=0, sticky="nsew", pady=3)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        self.result_text = scrolledtext.ScrolledText(result_frame, wrap=tk.WORD, height=22, font=("Arial", 10), state="disabled")
        self.result_text.grid(row=0, column=0, sticky="nsew")
        if self.current_record:
            self.display_record()
        else:
            self.set_result_text(self.t["empty"])
        self.update_action_state()

    def set_result_text(self, value: str):
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", value)
        self.result_text.configure(state="disabled")

    def update_action_state(self):
        state = "normal" if self.current_record is not None else "disabled"
        for key in ("save", "export"):
            if hasattr(self, "btn_" + key):
                getattr(self, "btn_" + key).configure(state=state)

    def invalidate_result(self, *_):
        had_result = self.current_record is not None
        self.current_record = None
        self.current_record_id = None
        if had_result and hasattr(self, "result_text"):
            self.set_result_text(self.t["stale"])
        self.update_action_state()

    def toggle_language(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        self.create_widgets()

    def calculate(self, *, show_errors=True):
        from tkinter import messagebox
        try:
            values = {key: variable.get().strip() for key, variable in self.input_vars.items()}
            validate_gui_inputs(values, self.hb_unit.get(), self.lang)
            patient = {key: variable.get().strip() for key, variable in self.patient_vars.items()}
            if patient["age"]:
                from prediction_core import finite_number
                if finite_number(patient["age"], "Age") < 0:
                    raise ValueError("Age must be non-negative")
            if patient["test_date"]:
                date.fromisoformat(patient["test_date"])
            self.current_record = create_record(self.model, values, hb_unit=self.hb_unit.get(), patient=patient)
            self.current_record_id = None
            self.display_record()
            self.update_action_state()
            return self.current_record
        except (ValueError, KeyError, OverflowError) as exc:
            self.current_record = None
            self.current_record_id = None
            self.update_action_state()
            if show_errors:
                messagebox.showerror(self.t["error"], str(exc), parent=self.root)
                return None
            raise

    def display_record(self):
        if self.current_record:
            self.set_result_text(report_text(self.current_record, self.lang))

    def save_record(self, *, show_messages=True):
        from tkinter import messagebox
        if not self.current_record:
            return None
        try:
            from database import ScreeningDatabase
            database = ScreeningDatabase(self.db_path)
            self.current_record_id = database.save_record(self.current_record)
            if show_messages:
                messagebox.showinfo(self.t["success"], f"{self.t['saved']}: {self.current_record_id}\n{database.path}", parent=self.root)
            return self.current_record_id
        except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
            if show_messages:
                messagebox.showerror(self.t["error"], str(exc), parent=self.root)
                return None
            raise

    def export_result(self, path=None, *, show_messages=True):
        from tkinter import filedialog, messagebox
        if not self.current_record:
            return None
        if path is None:
            path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".pdf",
                initialfile=f"THA_IDA_v{self.model.version}_report.pdf",
                filetypes=[("PDF", "*.pdf"), ("Excel", "*.xlsx"), ("CSV", "*.csv"), ("Text", "*.txt"), ("JSON", "*.json")])
        if not path:
            return None
        try:
            export_record(self.current_record, path, self.lang)
            if show_messages:
                messagebox.showinfo(self.t["success"], f"{self.t['exported']}:\n{path}", parent=self.root)
            return Path(path)
        except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
            if show_messages:
                messagebox.showerror(self.t["error"], str(exc), parent=self.root)
                return None
            raise

    def clear_inputs(self):
        for variable in [*self.input_vars.values(), *self.patient_vars.values()]:
            variable.set("")
        self.hb_unit.set("g/dL")
        self.patient_vars["test_date"].set(date.today().isoformat())
        self.current_record = None
        self.current_record_id = None
        self.set_result_text(self.t["empty"])
        self.update_action_state()

    def load_example(self):
        # Deliberately constructed example, not copied from a patient record.
        for key, value in dict(RBC="4.5", Hb="10", MCV="68", MCH="22", RDW="16").items():
            self.input_vars[key].set(value)
        self.hb_unit.set("g/dL")


def main(argv=None):
    parser = argparse.ArgumentParser(description="THA/IDA research calculator")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--self-test", action="store_true", help="Compare predictions with bundled synthetic R reference vectors")
    parser.add_argument("--smoke-test", action="store_true", help="Exercise a hidden Tk window with a synthetic example")
    parser.add_argument("--output", type=Path, help="JSON output for automated self/smoke test")
    args = parser.parse_args(argv)
    if args.version:
        if sys.stdout:
            print(APP_VERSION)
        return 0
    if args.self_test:
        from self_check import run_self_check
        result = run_self_check()
        if args.output:
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        if sys.stdout:
            print(json.dumps(result))
        return 0 if result["passed"] else 1
    import tkinter as tk
    root = tk.Tk()
    if args.smoke_test:
        root.withdraw()
    try:
        app = DifferentialGUI(root)
    except (OSError, ValueError, KeyError) as exc:
        from tkinter import messagebox
        messagebox.showerror("Model unavailable", str(exc), parent=root)
        root.destroy()
        return 1
    if args.smoke_test:
        import tempfile
        from database import ScreeningDatabase
        app.load_example()
        record = app.calculate(show_errors=False)
        app.toggle_language()
        root.update()
        with tempfile.TemporaryDirectory(prefix="thalassemia_synthetic_check_") as temp_dir:
            temp = Path(temp_dir)
            app.db_path = temp / "synthetic.sqlite3"
            identity = app.save_record(show_messages=False)
            if ScreeningDatabase(app.db_path).get_record(identity) != record:
                raise RuntimeError("Packaged database snapshot mismatch")
            exports = []
            for language in ("zh", "en"):
                if app.lang != language:
                    app.toggle_language()
                for extension in (".pdf", ".xlsx", ".csv", ".txt", ".json"):
                    path = temp / f"synthetic_{language}{extension}"
                    app.export_result(path, show_messages=False)
                    if not path.is_file() or path.stat().st_size == 0:
                        raise RuntimeError(f"Packaged export failed: {extension}")
                    if extension == ".json" and json.loads(path.read_text(encoding="utf-8")) != record:
                        raise RuntimeError("Packaged JSON snapshot mismatch")
                    if extension == ".pdf" and not path.read_bytes().startswith(b"%PDF-"):
                        raise RuntimeError("Packaged PDF signature mismatch")
                    if extension == ".xlsx":
                        from openpyxl import load_workbook
                        book = load_workbook(path, read_only=True)
                        snapshot = json.loads("\n".join(row[0] for row in book["JSON snapshot"].values))
                        book.close()
                        if snapshot != record:
                            raise RuntimeError("Packaged Excel snapshot mismatch")
                    exports.append(language + extension)
        result = {"passed": record is not None, "model_version": record["prediction"]["model_version"],
                  "model_sha256": record["prediction"]["model_sha256"], "tk_version": tk.TkVersion,
                  "languages_rendered": ["zh", "en"], "exports_checked": exports,
                  "sqlite_snapshot_roundtrip": True}
        if args.output:
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        root.destroy()
        return 0
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

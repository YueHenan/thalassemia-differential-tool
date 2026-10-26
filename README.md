# THA/IDA research calculator — version 2.0.0

A bilingual desktop research implementation of a teacher-confidence-weighted logistic model combined with five-index voting. This version accompanies the revised manuscript by Yongwei Yue and colleagues. It is an investigational tool, not diagnostic confirmation or an independently validated clinical product.

Version 2.0.0 retrains the final model after the author-confirmed Hb unit correction and reselects the DF and student probability thresholds on the corrected development data. It replaces the earlier rounded fitted coefficients and hard-coded performance text. The original v1.0.0 release is a separate historical version.

## Run from source

Use Python 3.11 or later with Tkinter. The prediction core and GUI use the standard library; PDF and Excel exports additionally use the pinned packages below.

```bash
python -m pip install -r requirements.txt
python thalassemia_differential_gui.py
```

The interface supports Chinese/English switching, optional patient details, a deliberately synthetic example, local SQLite saving, and PDF, Excel, CSV, text and JSON report exports. Changing any input or patient field invalidates the previous result so an old prediction cannot be exported under new inputs.

## Inputs and model

| Input | Canonical unit |
| --- | --- |
| RBC | 10^12/L |
| Hb | g/dL |
| MCV | fL |
| MCH | pg |
| RDW | Percentage points: enter 20 for 20% |

The GUI explicitly allows Hb in g/dL or g/L. Only an explicit g/L selection divides the entered value by 10. The application never changes 89 to 8.9 based on its magnitude. All inputs must be finite and positive. The GUI retains the earlier entry ranges: RBC 1–10, Hb 2–25 g/dL after unit conversion, MCV 30–150, MCH 10–50 and RDW 5–50 in the units above. Thus 89 g/dL is rejected and 89 g/L is explicitly converted to 8.9 g/dL. These are input guardrails, not validated calibration limits or proof of clinical applicability.

The authoritative full-precision parameters, thresholds, input units and performance summaries are in **model.json**. Do not replace them with rounded coefficients from a manuscript or display. The prediction core loads this file, checks its schema, and records its SHA256 in every report. It does not execute expression strings or contact a remote service.

```text
z = -20.895129342678821 + 4.8701293987448278 × RBC - 2.1100679880988844 × Hb - 0.38007464503954635 × MCV + 1.9589210174899925 × MCH + 0.19210134282197958 × RDW; q = 1 / (1 + exp(-z))
q > 0.53214576017225412
DF > 3.8145599999999988
```

Five index votes use their individually configured directions and cutoffs. The binary combined rule is `V >= 2 OR q > student_threshold`. The separately defined ROC ranking score is `S = 1 if V >= 2 else q`. S is not a calibrated individual disease probability, and its AUC is different from the AUC of the binary OR result.

Full-cohort apparent Combined performance (n=152): score AUC 0.927, sensitivity 86.8%, specificity 88.2%. These data were used in development. Internal cross-validation summaries are separately labelled in model.json; neither these results nor age matching establish external validity. Healthy individuals and other causes of anaemia were not evaluated. Clinical assessment, iron studies, haemoglobin analysis and genetic investigations remain necessary when indicated.

## Local records and exports

Saving is explicit and local. Version 2 uses a separate database in the user's application-data directory: `ThalassemiaDifferential/v2/research_records.sqlite3` (under LocalAppData on Windows, Application Support on macOS, and XDG data on Linux). It does not overwrite or migrate a v1 database. The full report snapshot, exact model version/hash, entered Hb unit, normalised inputs, individual rules, logistic probability and combined decision are retained. No research cohort spreadsheets or patient records are included in this repository or release.

CSV and Excel exports preserve user-entered strings as text rather than spreadsheet formulas. JSON preserves the complete machine-readable snapshot. PDF and Excel reports use the same snapshot as the screen and database. Source and Windows executable are separate deliverables.

## Verification

```bash
python -m unittest discover -s tests -v
python thalassemia_differential_gui.py --self-test --output parity.json
python thalassemia_differential_gui.py --smoke-test --output gui-smoke.json
```

The reference CSV contains 12 deliberately constructed synthetic input vectors independently evaluated in R. Tests compare logits, probabilities, all five formula values, votes, Boolean decisions and ranking scores. They also cover strict threshold boundaries, explicit units, invalid inputs, storage/export agreement and an actual Tk GUI. Set `REQUIRE_GUI_TESTS=1` to fail rather than skip when a display/Tk installation is unavailable.

## Windows executable

PyInstaller must run on Windows to produce a Windows executable. The provided spec deliberately rejects macOS/Linux. On Windows x64 with Python 3.11:

```powershell
python -m pip install -r requirements-build.txt
python -m PyInstaller --clean --noconfirm thalassemia_differential_gui.spec
python scripts/verify_windows_executable.py dist/ThalassemiaDifferential-v2.0.0.exe
```

The GitHub Actions workflow runs tests on `windows-latest`, builds the executable, verifies its Windows PE/AMD64 signature, and runs the packaged numerical and GUI smoke checks, including SQLite and all five export formats in both languages. It uploads a versioned artifact with verification reports and checksums. The workflow does not create or modify a public release. A successful native build and its checks are required before distributing an executable; renaming a macOS binary to `.exe` is not a Windows build.

## 中文使用说明

本版为2.0.0研究版本，使用纠正后的数据重新训练最终模型，并同步更新DF和逻辑模型阈值。全部系数和阈值从model.json读取，计算使用完整精度。输入Hb时必须明确选择g/dL或g/L，程序不会根据数值自动猜测单位。请按百分数输入RDW，例如20%。

保留中英文界面、可选患者信息、本地保存及PDF/Excel/CSV/文本导出，并新增完整JSON报告。修改输入后必须重新计算；保存报告包含模型版本、精确阈值和模型校验值。本版使用独立v2数据库，不覆盖旧记录。程序仅供研究，不能替代临床判断及确诊检查。

## Licence and attribution

MIT licence; see LICENSE. Original authors: Yongwei Yue and colleagues. No final journal citation or acceptance is asserted. Please cite the associated manuscript using its current bibliographic details when available.

# Build with Windows CPython. PyInstaller is not a cross-compiler.
from pathlib import Path
import sys

if sys.platform != "win32":
    raise SystemExit("Build this Windows executable on Windows, or use the provided GitHub Actions workflow.")
project = Path(SPECPATH)
sys.path.insert(0, str(project))
from prediction_core import APP_VERSION

a = Analysis(
    [str(project / "thalassemia_differential_gui.py")],
    pathex=[str(project)], binaries=[],
    datas=[(str(project / "model.json"), "."),
           (str(project / "tests" / "synthetic_reference.csv"), "tests"),
           (str(project / "LICENSE"), ".")],
    hiddenimports=["tkinter", "tkinter.ttk", "tkinter.scrolledtext", "sqlite3",
                   "openpyxl", "reportlab.pdfbase.cidfonts", "reportlab.platypus"],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name=f"ThalassemiaDifferential-v{APP_VERSION}", debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False)

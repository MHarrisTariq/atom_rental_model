"""
Build SmartPricing_Lodging_Client.zip for handoff (no node_modules, no dist, no __pycache__).
Run from project root: py -3.12 build_client_zip.py
"""
from __future__ import annotations

import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ZIP_NAME = "SmartPricing_Lodging_Client.zip"

SKIP_DIR_NAMES = {"node_modules", "__pycache__", "dist", ".git"}
SKIP_SUFFIXES = {".pyc", ".pyo"}

# Only these top-level dirs/files go in the zip
INCLUDE_TOP = ("backend", "frontend")
EXTRA_FILES = (
    "requirements_demo.txt",
    "HOW_TO_RUN_SMART_PRICING.txt",
    "run_demo.py",
    "Airbnb_Open_Data.csv",
)

README_CLIENT = """Smart Pricing — Lodging (client package)

CONTENTS
- backend/          Python FastAPI API
- frontend/         React + Vite source (run npm install — node_modules not included)
- Airbnb_Open_Data.csv   Sample data for the API
- requirements_demo.txt, run_demo.py, HOW_TO_RUN_SMART_PRICING.txt

SETUP
1) Python 3.12+ and Node.js 18+ (LTS)
2) py -3.12 -m pip install -r requirements_demo.txt
3) cd frontend && npm install && npm run build && cd ..
4) py -3.12 run_demo.py
5) Open http://127.0.0.1:8000

API docs: http://127.0.0.1:8000/docs
"""


def should_skip(path: Path) -> bool:
    for part in path.parts:
        if part in SKIP_DIR_NAMES:
            return True
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    return False


def main() -> None:
    out = ROOT / ZIP_NAME
    if out.exists():
        out.unlink()

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README_CLIENT.txt", README_CLIENT.encode("utf-8"))

        for name in INCLUDE_TOP:
            base = ROOT / name
            if not base.is_dir():
                raise SystemExit(f"Missing folder: {base}")

            for dirpath, dirnames, filenames in os.walk(base):
                # prune skipped dirs in-place
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
                for fn in filenames:
                    if Path(fn).suffix.lower() in SKIP_SUFFIXES:
                        continue
                    fp = Path(dirpath) / fn
                    if should_skip(fp):
                        continue
                    arc = fp.relative_to(ROOT).as_posix()
                    zf.write(fp, arcname=arc)

        for rel in EXTRA_FILES:
            fp = ROOT / rel
            if fp.is_file():
                zf.write(fp, arcname=rel)

    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"Created: {out}")
    print(f"Size: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()

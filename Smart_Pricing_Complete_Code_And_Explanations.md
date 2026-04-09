# Smart Pricing — Complete source code and explanations
_Generated: 2026-04-09 17:24 UTC_

## Scope

This document embeds **every hand-written project source file** for the Smart Pricing (Lodging) demo: **backend (Python/FastAPI)** and **frontend (React/TypeScript/Vite)**, plus root **requirements** and **utility scripts**.

### Excluded (not application source)

- `node_modules/`, `frontend/dist/`, `__pycache__/`, `.vite/`, `.git/`
- Binaries and datasets: `*.joblib`, `*.zip`, `*.csv`
- Third-party vendored code inside `node_modules` (thousands of files; reinstall via `package-lock.json`)

### Architecture update (enterprise-oriented)

1. **Persistence**: SQLite (`backend/storage.py`) stores kill-switch, regional override, host settings, and audit log (env `SMART_PRICING_DB_PATH`).
2. **Security**: JWT login (`POST /api/auth/login`); admin-only routes use `require_admin` (`backend/auth.py`). Rate limiting via `slowapi` (`backend/rate_limit.py`).
3. **ML**: Trained conversion model (`backend/train_conversion_model.py`) saved as `backend/models/conversion_model.joblib`; inference in `backend/ml_conversion.py`. Simulation uses ML when the file exists, else mock curve.
4. **Decision engine**: `backend/decision_engine.py` grid-searches price to maximize expected revenue using the conversion model.
5. **Observability**: Request IDs + optional `/metrics` (`backend/observability.py`).
6. **Events / features (optional)**: Kafka publisher (`backend/events.py`); Redis feature store scaffold (`backend/feature_store.py`).

### Frontend note

The UI (`frontend/src/api.ts`) uses unauthenticated `fetch` for host settings and admin. If the API returns **401**, add `Authorization: Bearer <token>` from `/api/auth/login` to those calls.


---

## `requirements.txt`

Python dependencies for the upgraded stack: FastAPI, Uvicorn, pandas, scikit-learn, JWT auth (python-jose), rate limiting (slowapi), Prometheus metrics, and python-docx for tooling.

```text
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pandas>=2.0.0
numpy>=2.0.0
scikit-learn>=1.4.0
joblib>=1.3.0
python-jose[cryptography]>=3.3.0
slowapi>=0.1.9
prometheus-fastapi-instrumentator>=7.0.0
python-docx>=1.1.0

```

<!-- end of file: requirements.txt -->

## `requirements_demo.txt`

Minimal dependency list referenced by HOW_TO_RUN and older zip handoffs (FastAPI, Uvicorn, pandas). Prefer requirements.txt for full features.

```text
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pandas>=2.0.0
```

<!-- end of file: requirements_demo.txt -->

## `HOW_TO_RUN_SMART_PRICING.txt`

Human-readable runbook: one-command production flow (build UI, run_demo.py), dev mode with Vite proxy, and data requirement (Airbnb_Open_Data.csv in project root).

```text
Smart Pricing — Lodging demo (from Jira Stories for Smart Pricing)

WHAT YOU GET
- backend/          FastAPI: pricing engine + APIs (GET /api/pricing/{id}, POST /api/simulation/run, admin kill switch)
- frontend/         React (Vite) web UI: Host controls, 60-day calendar, simulation, admin
- run_demo.py       Starts API on http://127.0.0.1:8000 (serves built UI from frontend/dist if present)

ONE-COMMAND (after build)
1) Install Python deps:
   py -3.12 -m pip install -r requirements_demo.txt -q
2) Build frontend once:
   cd frontend
   npm install
   npm run build
   cd ..
3) Run:
   py -3.12 run_demo.py
4) Open browser: http://127.0.0.1:8000
   API docs: http://127.0.0.1:8000/docs

DEV (hot reload UI + API)
Terminal A:
   py -3.12 -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
Terminal B:
   cd frontend
   npm run dev
   Open http://127.0.0.1:5173 (Vite proxies /api to :8000)

DATA REQUIREMENT
- Airbnb_Open_Data.csv must sit in the project root (same folder as backend/ and frontend/).
```

<!-- end of file: HOW_TO_RUN_SMART_PRICING.txt -->

## `run_demo.py`

Entry point to run Uvicorn with backend.main:app from project root; serves built React from frontend/dist when SMART_PRICING_WEB_DIST is set or default path exists.

```python
"""
Run Smart Pricing demo: FastAPI backend (serves built UI from frontend/dist).

Development (two terminals):
  Terminal A: py -3.12 -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
  Terminal B: cd frontend && npm install && npm run dev

Production (one server):
  cd frontend && npm install && npm run build
  py -3.12 run_demo.py
  Open http://127.0.0.1:8000
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    try:
        import uvicorn
    except ImportError:
        print("Install: py -3.12 -m pip install uvicorn[standard] fastapi pandas", file=sys.stderr)
        raise

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
```

<!-- end of file: run_demo.py -->

## `build_client_zip.py`

Packages backend/, frontend source, CSV, and helper files into SmartPricing_Lodging_Client.zip for delivery, excluding node_modules, dist, and __pycache__.

```python
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
```

<!-- end of file: build_client_zip.py -->

## `build_full_code_docx.py`

Earlier doc generator (subset ordering). Superseded by this script for full coverage; kept for history.

```python
"""
Generate Smart_Pricing_Full_Code_Documentation.docx with complete backend + frontend source
and explanations. Excludes node_modules, dist, __pycache__.

Run: py -3.12 build_full_code_docx.py
Requires: pip install python-docx
"""
from __future__ import annotations

import os
from pathlib import Path

from docx import Document
from docx.enum.text import WD_LINE_SPACING
from docx.shared import Pt, RGBColor

ROOT = Path(__file__).resolve().parent

SKIP_DIRS = {"node_modules", "dist", "__pycache__", ".git", ".vite"}
SKIP_FILES = {".DS_Store"}

# Order matters for readability (not alphabetical)
ORDERED = [
    "backend/__init__.py",
    "backend/pricing_engine.py",
    "backend/main.py",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/tsconfig.json",
    "frontend/vite.config.ts",
    "frontend/index.html",
    "frontend/src/vite-env.d.ts",
    "frontend/src/api.ts",
    "frontend/src/main.tsx",
    "frontend/src/styles.css",
    "frontend/src/App.tsx",
]

EXPLAIN: dict[str, str] = {
    "backend/__init__.py": (
        "Marks the `backend` directory as a Python package so imports like `backend.main` work "
        "when you run Uvicorn from the project root."
    ),
    "backend/pricing_engine.py": (
        "Core pricing logic for lodging (nightly rates). Implements the multiplier pipeline: "
        "raw_price = base × season × demand × supply × day-of-week × lead_time × quality × goal × risk, "
        "then clamps to host min/max. Also provides confidence scores, explanation tags, blackout handling, "
        "smoothing vs the previous day, kill-switch behavior, and mock booking probability / expected revenue "
        "for the simulation API."
    ),
    "backend/main.py": (
        "FastAPI application: loads `Airbnb_Open_Data.csv`, exposes REST endpoints for listings, "
        "pricing calendar (`GET /api/pricing/{id}`), saving host settings (`POST /api/host/settings/{id}`), "
        "simulation (`POST /api/simulation/run`), admin status and kill switch. Serves the built React app "
        "from `frontend/dist` when present; otherwise returns a JSON hint at `/`. Can be run with "
        "`python main.py` inside `backend/` (fallback imports) or `uvicorn backend.main:app` from the project root."
    ),
    "frontend/package.json": (
        "NPM project metadata: React 18, Vite 5, TypeScript. Scripts `dev`, `build`, `preview` for local dev and production bundle."
    ),
    "frontend/package-lock.json": (
        "NPM lockfile: pins exact dependency versions for reproducible `npm ci` / `npm install` installs."
    ),
    "frontend/tsconfig.json": (
        "TypeScript compiler options: strict mode, ES2022, JSX react-jsx, bundler module resolution for Vite."
    ),
    "frontend/vite.config.ts": (
        "Vite configuration: React plugin, dev server on port 5173, proxy `/api` to the FastAPI backend on port 8000, "
        "build output to `dist/`."
    ),
    "frontend/index.html": (
        "HTML shell: mounts the React app on `#root`, loads DM Sans font, sets viewport and theme color."
    ),
    "frontend/src/vite-env.d.ts": (
        "TypeScript triple-slash reference so the compiler recognizes Vite-specific types and `import.meta`."
    ),
    "frontend/src/api.ts": (
        "Thin API client: `fetch` wrappers for `/api/listings`, `/api/pricing`, host settings POST, simulation, "
        "admin status, kill switch. Uses same-origin `/api` (or Vite proxy in development)."
    ),
    "frontend/src/main.tsx": (
        "React 18 entry: creates root, renders `<App />` inside `StrictMode`, imports global `styles.css`."
    ),
    "frontend/src/styles.css": (
        "Global UI styling: blue-and-white theme, layout (top bar, cards, grid), form controls, calendar cells, "
        "modal, stats, error banner. CSS variables for colors and shadows."
    ),
    "frontend/src/App.tsx": (
        "Main React UI: tabbed Host / Simulation / Admin. Host tab: listing picker, smart pricing toggles, "
        "min/max/base, preferences, locked/blackout dates, 60-day calendar with modal breakdown. Simulation tab: "
        "custom price vs probability and expected revenue. Admin tab: kill switch and audit list."
    ),
}


def collect_files() -> list[Path]:
    found: dict[str, Path] = {}
    for dirpath, dirnames, filenames in os.walk(ROOT / "backend"):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn in SKIP_FILES or fn.endswith(".pyc"):
                continue
            p = Path(dirpath) / fn
            rel = p.relative_to(ROOT).as_posix()
            found[rel] = p
    for dirpath, dirnames, filenames in os.walk(ROOT / "frontend"):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn in SKIP_FILES:
                continue
            p = Path(dirpath) / fn
            rel = p.relative_to(ROOT).as_posix()
            if "node_modules" in rel or rel.startswith("frontend/dist/"):
                continue
            found[rel] = p

    ordered_paths: list[Path] = []
    for rel in ORDERED:
        if rel in found:
            ordered_paths.append(found.pop(rel))
    # Any extra files not in ORDERED (should be none if list is complete)
    for rel in sorted(found.keys()):
        ordered_paths.append(found[rel])

    return ordered_paths


def add_para(doc: Document, text: str, *, bold: bool = False, size: int = 11) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(size)
    if bold:
        run.bold = True
    run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)


def add_code_block(doc: Document, content: str) -> None:
    """Append full source; one paragraph per line keeps Word stable for huge files."""
    if not content.endswith("\n"):
        content += "\n"
    for line in content.splitlines():
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.space_before = Pt(0)
        run = p.add_run(line)
        run.font.name = "Consolas"
        run._element.rPr.rFonts.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ascii", "Consolas")
        run._element.rPr.rFonts.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}hAnsi", "Consolas")
        run.font.size = Pt(7.5)


def main() -> None:
    out = ROOT / "Smart_Pricing_Full_Code_Documentation.docx"

    doc = Document()
    sect = doc.sections[0]
    sect.left_margin = sect.right_margin = Pt(72)

    title = doc.add_heading("Smart Pricing (Lodging)", 0)
    title.runs[0].font.color.rgb = RGBColor(0x1E, 0x40, 0xAF)

    doc.add_paragraph()
    add_para(
        doc,
        "Complete source code documentation — backend (Python / FastAPI) and frontend (React / TypeScript / Vite). "
        "Every file below is included in full with no omissions. Generated for client delivery.",
        size=11,
    )
    doc.add_paragraph()
    add_para(doc, "Runtime data: the API expects Airbnb_Open_Data.csv in the project root (not included in this code listing).", size=10)

    paths = collect_files()
    doc.add_page_break()

    doc.add_heading("Part A — Backend (Python)", level=1)
    doc.add_paragraph()

    backend_done = False
    for fp in paths:
        rel = fp.relative_to(ROOT).as_posix()
        if rel.startswith("frontend/") and not backend_done:
            doc.add_page_break()
            doc.add_heading("Part B — Frontend (React / Vite)", level=1)
            doc.add_paragraph()
            backend_done = True

        doc.add_heading(rel.replace("/", " → "), level=2)
        expl = EXPLAIN.get(rel, "Source file for the Smart Pricing lodging demo.")
        add_para(doc, expl, size=10)
        doc.add_paragraph()

        text = fp.read_text(encoding="utf-8", errors="replace")
        add_code_block(doc, text)
        endp = doc.add_paragraph()
        er = endp.add_run("— end of file —")
        er.italic = True
        er.font.size = Pt(9)
        er.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
        doc.add_paragraph()

    doc.save(out)
    print(f"Wrote: {out}")
    print(f"Files embedded: {len(paths)}")


if __name__ == "__main__":
    main()
```

<!-- end of file: build_full_code_docx.py -->

## `extract_docx_text.py`

CLI utility: extracts paragraph and table text from a .docx to UTF-8 .txt (uses python-docx).

```python
import argparse
import os
import sys


def _iter_paragraph_text(doc):
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if t:
            yield t


def _iter_table_text(doc):
    for table in doc.tables:
        for row in table.rows:
            cells = []
            for cell in row.cells:
                text = " ".join((cell.text or "").split())
                cells.append(text)
            # Keep table structure readable in txt
            line = "\t".join(cells).strip()
            if line:
                yield line


def extract_docx_to_text(input_path: str) -> str:
    try:
        from docx import Document
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency 'python-docx'. Install it with: python -m pip install python-docx"
        ) from e

    doc = Document(input_path)
    lines = []
    lines.extend(_iter_paragraph_text(doc))

    table_lines = list(_iter_table_text(doc))
    if table_lines:
        if lines:
            lines.append("")
        lines.append("[Tables]")
        lines.extend(table_lines)

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract .docx text to a UTF-8 .txt file.")
    ap.add_argument("input", help="Path to .docx file")
    ap.add_argument(
        "-o",
        "--output",
        help="Path to output .txt (defaults to <input>.txt)",
        default=None,
    )
    args = ap.parse_args()

    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        print(f"Input not found: {input_path}", file=sys.stderr)
        return 2

    out_path = os.path.abspath(args.output) if args.output else (input_path + ".txt")

    try:
        text = extract_docx_to_text(input_path)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

<!-- end of file: extract_docx_text.py -->

## `train_lodging_price_model.py`

Standalone training script for lodging price modeling (if present in repo); may predate conversion model.

```python
"""
Train a first-pass lodging nightly price model on Airbnb_Open_Data.csv.

Goal (client demo):
- Show measurable accuracy (MAE / RMSE / R² / MAPE)
- Produce example predictions
- Save a model artifact for reuse

This script predicts the dataset's `price` column (nightly price) using available listing attributes.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from joblib import dump
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import HistGradientBoostingRegressor


PRICE_RE = re.compile(r"[^\d.\-]+")


def _stable_hash_to_int(s: str) -> int:
    # Deterministic hash for repeatable per-row pseudo-randomness
    h = 2166136261
    for ch in s:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return int(h)


def _to_bool01(x: Any) -> float:
    s = str(x).strip().lower()
    if s in {"true", "t", "1", "yes", "y"}:
        return 1.0
    if s in {"false", "f", "0", "no", "n"}:
        return 0.0
    return float("nan")


def parse_money_to_float(x: Any) -> float:
    if x is None:
        return float("nan")
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    s = str(x).strip()
    if not s:
        return float("nan")
    # remove currency, commas, spaces, etc.
    s = PRICE_RE.sub("", s)
    try:
        return float(s)
    except ValueError:
        return float("nan")


def safe_bool(x: Any) -> Optional[bool]:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    s = str(x).strip().lower()
    if s in {"true", "t", "1", "yes", "y"}:
        return True
    if s in {"false", "f", "0", "no", "n"}:
        return False
    return None


def parse_date_to_ordinal(x: Any) -> float:
    if x is None:
        return float("nan")
    s = str(x).strip()
    if not s:
        return float("nan")
    # Dataset seems like M/D/YYYY
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return float(dt.toordinal())
        except ValueError:
            pass
    return float("nan")


@dataclass
class Metrics:
    mae: float
    rmse: float
    r2: float
    mape: float


@dataclass
class AccuracyLike:
    within_10pct: float
    within_20pct: float
    within_50_abs: float
    within_100_abs: float
    median_abs_error: float


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Metrics:
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    # avoid division by zero
    denom = np.maximum(np.abs(y_true), 1e-6)
    mape = float(np.mean(np.abs((y_true - y_pred) / denom)) * 100.0)
    return Metrics(mae=mae, rmse=rmse, r2=r2, mape=mape)


def compute_accuracy_like(y_true: np.ndarray, y_pred: np.ndarray) -> AccuracyLike:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    abs_err = np.abs(y_true - y_pred)
    pct_err = abs_err / np.maximum(np.abs(y_true), 1e-6)

    return AccuracyLike(
        within_10pct=float(np.mean(pct_err <= 0.10) * 100.0),
        within_20pct=float(np.mean(pct_err <= 0.20) * 100.0),
        within_50_abs=float(np.mean(abs_err <= 50.0) * 100.0),
        within_100_abs=float(np.mean(abs_err <= 100.0) * 100.0),
        median_abs_error=float(np.median(abs_err)),
    )


def baseline_predict_median(y_train: pd.Series, n: int) -> np.ndarray:
    # Simple baseline: always predict the training median price
    return np.full(shape=(n,), fill_value=float(np.median(y_train.to_numpy())), dtype=float)


def build_pipeline(numeric_features: List[str], categorical_features: List[str]) -> Pipeline:
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            # Dense output because HistGradientBoostingRegressor doesn't accept sparse input.
            # min_frequency reduces cardinality explosion for high-cardinality categoricals.
            ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=50, sparse_output=False)),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ],
        remainder="drop",
        sparse_threshold=0.0,
    )

    # Strong baseline for tabular data; fast and works well without heavy tuning.
    model = HistGradientBoostingRegressor(
        loss="squared_error",
        max_depth=6,
        learning_rate=0.08,
        max_iter=400,
        random_state=42,
    )

    return Pipeline(steps=[("preprocess", preprocessor), ("model", model)])


def load_and_prepare(
    csv_path: Path,
    *,
    include_ids: bool,
    include_service_fee: bool,
    add_mock_columns: bool,
    seed: int,
) -> Tuple[pd.DataFrame, pd.Series]:
    df = pd.read_csv(csv_path, low_memory=False)

    # Target
    y = df["price"].map(parse_money_to_float)

    # Basic feature engineering grounded in available columns
    df = df.copy()
    df["service_fee_num"] = df.get("service fee", pd.Series([np.nan] * len(df))).map(parse_money_to_float)
    df["instant_bookable_bool"] = df.get("instant_bookable", pd.Series([None] * len(df))).map(safe_bool)
    df["last_review_ordinal"] = df.get("last review", pd.Series([np.nan] * len(df))).map(parse_date_to_ordinal)

    # Optional: add synthetic hotel-style columns for demos (no direct use of target price).
    if add_mock_columns:
        n = len(df)
        rng = np.random.default_rng(seed)

        review_rate = pd.to_numeric(df.get("review rate number"), errors="coerce")
        reviews_cnt = pd.to_numeric(df.get("number of reviews"), errors="coerce").fillna(0)
        reviews_per_month = pd.to_numeric(df.get("reviews per month"), errors="coerce").fillna(0)
        min_nights = pd.to_numeric(df.get("minimum nights"), errors="coerce").fillna(1)
        availability = pd.to_numeric(df.get("availability 365"), errors="coerce")
        instant_bookable = df.get("instant_bookable", pd.Series([None] * n)).map(_to_bool01)

        room_type = df.get("room type", pd.Series(["Unknown"] * n)).astype(str).fillna("Unknown")
        nb_group = df.get("neighbourhood group", pd.Series(["Unknown"] * n)).astype(str).fillna("Unknown")

        bedroom_base = np.where(room_type.str.contains("entire", case=False), 1.0, 0.0)
        bedrooms = np.clip(np.round(bedroom_base + rng.normal(0.4, 0.6, size=n)), 0, 5).astype(int)
        bathrooms = np.clip(np.round(bedrooms * 0.8 + rng.normal(0.3, 0.5, size=n)), 0, 4).astype(int)
        accommodates = np.clip(bedrooms * 2 + rng.integers(0, 3, size=n) + 1, 1, 10).astype(int)

        quality_proxy = (
            (review_rate.fillna(3.5) / 5.0) * 0.6
            + np.tanh(reviews_per_month / 2.0) * 0.2
            + np.tanh(reviews_cnt / 50.0) * 0.2
        )
        amenities_count = np.clip(
            np.round(10 + 25 * quality_proxy + rng.normal(0, 3, size=n)),
            5,
            60,
        ).astype(int)
        star_rating = np.clip(
            np.round(3.2 + 1.8 * quality_proxy + rng.normal(0, 0.3, size=n), 1),
            1.0,
            5.0,
        )

        market_tier_map: Dict[str, int] = {
            "Manhattan": 3,
            "Brooklyn": 2,
            "Queens": 2,
            "Bronx": 1,
            "Staten Island": 1,
        }
        market_tier = nb_group.map(lambda x: market_tier_map.get(str(x), 2)).astype(int)

        occ_from_avail = 1.0 - (availability.fillna(365) / 365.0)
        occupancy_rate = np.clip(0.25 + 0.60 * occ_from_avail + rng.normal(0, 0.08, size=n), 0.05, 0.98)
        demand_index = (
            0.8
            + 0.25 * (market_tier - 2)
            + 0.10 * np.nan_to_num(instant_bookable, nan=0.0)
            + 0.20 * (occupancy_rate - 0.5)
            + rng.normal(0, 0.10, size=n)
        )
        demand_index = np.clip(demand_index, 0.2, 2.0)

        lead_time_days = np.clip(np.round(rng.gamma(shape=2.0, scale=10.0, size=n)), 0, 180).astype(int)
        length_of_stay = np.clip(
            np.round(rng.gamma(shape=2.0, scale=2.0, size=n) + min_nights / 5.0),
            1,
            30,
        ).astype(int)
        weekend_share = np.clip(0.25 + rng.normal(0, 0.08, size=n), 0.05, 0.60)
        peak_season_share = np.clip(0.20 + 0.10 * (market_tier - 2) + rng.normal(0, 0.06, size=n), 0.05, 0.60)

        df["mock_bedrooms"] = bedrooms
        df["mock_bathrooms"] = bathrooms
        df["mock_accommodates"] = accommodates
        df["mock_amenities_count"] = amenities_count
        df["mock_star_rating"] = star_rating
        df["mock_market_tier"] = market_tier
        df["mock_occupancy_rate"] = occupancy_rate
        df["mock_demand_index"] = demand_index
        df["mock_lead_time_days"] = lead_time_days
        df["mock_length_of_stay"] = length_of_stay
        df["mock_weekend_share"] = weekend_share
        df["mock_peak_season_share"] = peak_season_share
        if "id" in df.columns:
            df["mock_listing_seed"] = df["id"].astype(str).map(_stable_hash_to_int)

    # Drop columns we should not use (leakage / too-free-text / identifiers)
    drop_cols = {
        "price",
        "NAME",
        "house_rules",
        "host name",
        "license",
        # raw last review (we use ordinal instead)
        "last review",
    }
    if not include_ids:
        # identifiers can let the model memorize
        drop_cols |= {"id", "host id"}
    if not include_service_fee:
        # service fee is often derived from price (target leakage risk)
        drop_cols |= {"service fee", "service_fee_num"}
    X = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    # A little cleanup for weird blanks
    X.replace({"": np.nan, " ": np.nan}, inplace=True)

    # Remove rows with missing/invalid target
    mask = (~y.isna()) & (y > 0)
    X = X.loc[mask].reset_index(drop=True)
    y = y.loc[mask].reset_index(drop=True)

    return X, y


def infer_feature_types(X: pd.DataFrame) -> Tuple[List[str], List[str]]:
    # Explicitly treat some known fields as categorical, even if they look numeric-ish.
    force_categorical = {
        "host_identity_verified",
        "neighbourhood group",
        "neighbourhood",
        "country",
        "country code",
        "cancellation_policy",
        "room type",
        "instant_bookable",
        "instant_bookable_bool",
    }

    numeric_features: List[str] = []
    categorical_features: List[str] = []

    for col in X.columns:
        if col in force_categorical:
            categorical_features.append(col)
            continue
        if pd.api.types.is_bool_dtype(X[col]):
            categorical_features.append(col)
            continue
        if pd.api.types.is_numeric_dtype(X[col]):
            numeric_features.append(col)
            continue
        # Try to coerce object columns that are mostly numeric
        if X[col].dtype == "object":
            # If it parses to numeric for most values, keep numeric.
            coerced = pd.to_numeric(X[col], errors="coerce")
            non_na_ratio = float(coerced.notna().mean())
            if non_na_ratio >= 0.80:
                X[col] = coerced
                numeric_features.append(col)
            else:
                categorical_features.append(col)
        else:
            categorical_features.append(col)

    if "last_review_ordinal" in X.columns and "last_review_ordinal" not in numeric_features:
        numeric_features.append("last_review_ordinal")

    return numeric_features, categorical_features


def cross_val_report(pipeline: Pipeline, X: pd.DataFrame, y: pd.Series, k: int) -> Dict[str, Any]:
    kf = KFold(n_splits=k, shuffle=True, random_state=42)
    fold_metrics: List[Metrics] = []
    fold_acc: List[AccuracyLike] = []

    for train_idx, test_idx in kf.split(X):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]
        pipeline.fit(X_tr, y_tr)
        preds = pipeline.predict(X_te)
        fold_metrics.append(compute_metrics(y_te.to_numpy(), preds))
        fold_acc.append(compute_accuracy_like(y_te.to_numpy(), preds))

    return {
        "k": k,
        "folds": [asdict(m) for m in fold_metrics],
        "folds_accuracy_like": [asdict(a) for a in fold_acc],
        "mean": {
            "mae": float(np.mean([m.mae for m in fold_metrics])),
            "rmse": float(np.mean([m.rmse for m in fold_metrics])),
            "r2": float(np.mean([m.r2 for m in fold_metrics])),
            "mape": float(np.mean([m.mape for m in fold_metrics])),
            "within_10pct": float(np.mean([a.within_10pct for a in fold_acc])),
            "within_20pct": float(np.mean([a.within_20pct for a in fold_acc])),
            "within_50_abs": float(np.mean([a.within_50_abs for a in fold_acc])),
            "within_100_abs": float(np.mean([a.within_100_abs for a in fold_acc])),
            "median_abs_error": float(np.mean([a.median_abs_error for a in fold_acc])),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="Airbnb_Open_Data.csv", help="Path to Airbnb CSV")
    ap.add_argument(
        "--outdir",
        default="artifacts_no_leak",
        help="Output directory for model + reports",
    )
    ap.add_argument("--test_size", type=float, default=0.2, help="Holdout split size")
    ap.add_argument("--cv", type=int, default=5, help="K-fold CV folds (0 to disable)")
    ap.add_argument(
        "--include_ids",
        action="store_true",
        help="Include listing/host IDs as features (HIGH leakage risk; can inflate accuracy).",
    )
    ap.add_argument(
        "--include_service_fee",
        action="store_true",
        help="Include service fee features (leakage risk; default: excluded).",
    )
    ap.add_argument("--clip_q_low", type=float, default=0.01, help="Lower quantile clip for target (0 disables)")
    ap.add_argument("--clip_q_high", type=float, default=0.99, help="Upper quantile clip for target (0 disables)")
    ap.add_argument("--log_target", action="store_true", help="Train on log(price) and back-transform predictions")
    ap.add_argument(
        "--add_mock_columns",
        action="store_true",
        help="Add synthetic hotel-style columns for demo (does not use target price directly).",
    )
    ap.add_argument("--seed", type=int, default=42, help="Random seed")
    args = ap.parse_args()

    csv_path = Path(args.csv).resolve()
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    X, y = load_and_prepare(
        csv_path,
        include_ids=bool(args.include_ids),
        include_service_fee=bool(args.include_service_fee),
        add_mock_columns=bool(args.add_mock_columns),
        seed=int(args.seed),
    )

    # Optional target clipping to reduce extreme outliers (more stable client-facing metrics).
    if args.clip_q_low and args.clip_q_high and 0 < args.clip_q_low < args.clip_q_high < 1:
        lo = float(y.quantile(args.clip_q_low))
        hi = float(y.quantile(args.clip_q_high))
        keep = (y >= lo) & (y <= hi)
        X = X.loc[keep].reset_index(drop=True)
        y = y.loc[keep].reset_index(drop=True)
    numeric_features, categorical_features = infer_feature_types(X)
    pipeline = build_pipeline(numeric_features, categorical_features)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.seed
    )

    if args.log_target:
        pipeline.fit(X_train, np.log1p(y_train.to_numpy()))
        preds = np.expm1(pipeline.predict(X_test))
    else:
        pipeline.fit(X_train, y_train)
        preds = pipeline.predict(X_test)
    metrics = compute_metrics(y_test.to_numpy(), preds)
    acc_like = compute_accuracy_like(y_test.to_numpy(), preds)

    # Baseline comparison (helps explain whether model is actually learning)
    baseline_preds = baseline_predict_median(y_train, n=len(y_test))
    baseline_metrics = compute_metrics(y_test.to_numpy(), baseline_preds)
    baseline_acc_like = compute_accuracy_like(y_test.to_numpy(), baseline_preds)

    # Save model
    model_path = outdir / "lodging_price_model.joblib"
    dump(
        {
            "pipeline": pipeline,
            "numeric_features": numeric_features,
            "categorical_features": categorical_features,
            "target": "price",
            "csv": str(csv_path),
            "log_target": bool(args.log_target),
            "clip_q_low": float(args.clip_q_low),
            "clip_q_high": float(args.clip_q_high),
            "include_ids": bool(args.include_ids),
            "include_service_fee": bool(args.include_service_fee),
        },
        model_path,
    )

    # Example predictions (client-friendly)
    sample = X_test.copy().reset_index(drop=True)
    sample_y = y_test.reset_index(drop=True)
    sample["actual_price"] = sample_y
    sample["predicted_price"] = preds
    sample["abs_error"] = np.abs(sample["actual_price"] - sample["predicted_price"])
    example_path = outdir / "example_predictions.csv"
    sample.sort_values("abs_error", ascending=False).head(50).to_csv(example_path, index=False)

    report: Dict[str, Any] = {
        "dataset_rows_used": int(len(X)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "numeric_features": numeric_features,
        "categorical_features": categorical_features,
        "holdout_metrics": asdict(metrics),
        "holdout_accuracy_like": asdict(acc_like),
        "baseline_holdout_metrics": asdict(baseline_metrics),
        "baseline_holdout_accuracy_like": asdict(baseline_acc_like),
        "artifacts": {
            "model": str(model_path),
            "example_predictions": str(example_path),
        },
    }

    if args.cv and args.cv >= 2:
        if args.log_target:
            kf = KFold(n_splits=args.cv, shuffle=True, random_state=42)
            fold_metrics: List[Metrics] = []
            for tr_idx, te_idx in kf.split(X):
                X_tr, X_te = X.iloc[tr_idx], X.iloc[te_idx]
                y_tr, y_te = y.iloc[tr_idx], y.iloc[te_idx]
                pipeline.fit(X_tr, np.log1p(y_tr.to_numpy()))
                pr = np.expm1(pipeline.predict(X_te))
                fold_metrics.append(compute_metrics(y_te.to_numpy(), pr))
            report["cross_validation"] = {
                "k": int(args.cv),
                "folds": [asdict(m) for m in fold_metrics],
                "mean": {
                    "mae": float(np.mean([m.mae for m in fold_metrics])),
                    "rmse": float(np.mean([m.rmse for m in fold_metrics])),
                    "r2": float(np.mean([m.r2 for m in fold_metrics])),
                    "mape": float(np.mean([m.mape for m in fold_metrics])),
                },
            }
        else:
            report["cross_validation"] = cross_val_report(pipeline, X, y, k=args.cv)

    report_path = outdir / "training_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Console summary (copy/paste to client)
    print("\n=== Lodging price model (holdout) ===")
    print(f"Rows used: {report['dataset_rows_used']:,}")
    print(f"MAE : {metrics.mae:,.2f}")
    print(f"RMSE: {metrics.rmse:,.2f}")
    print(f"R²  : {metrics.r2:,.4f}")
    print(f"MAPE: {metrics.mape:,.2f}%")
    print("\n=== Accuracy-like (client-friendly) ===")
    print(f"Within ±10% : {acc_like.within_10pct:,.2f}%")
    print(f"Within ±20% : {acc_like.within_20pct:,.2f}%")
    print(f"Within ±$50 : {acc_like.within_50_abs:,.2f}%")
    print(f"Within ±$100: {acc_like.within_100_abs:,.2f}%")
    print(f"Median |error|: {acc_like.median_abs_error:,.2f}")

    print("\n=== Baseline (predict median) ===")
    print(f"Baseline MAE : {baseline_metrics.mae:,.2f}")
    print(f"Baseline RMSE: {baseline_metrics.rmse:,.2f}")
    print(f"Baseline R²  : {baseline_metrics.r2:,.4f}")
    print(f"Baseline MAPE: {baseline_metrics.mape:,.2f}%")
    print(f"Baseline within ±20%: {baseline_acc_like.within_20pct:,.2f}%")
    print(f"\nSaved model: {model_path}")
    print(f"Saved report: {report_path}")
    print(f"Saved examples: {example_path}")


if __name__ == "__main__":
    main()

```

<!-- end of file: train_lodging_price_model.py -->

## `build_complete_project_documentation.py`

This file: collects all source paths, writes Word + Markdown with explanations and full file bodies.

```python
"""
Generate a single documentation bundle: Word (.docx) + Markdown (.md) containing
every project source file in full, with per-file explanations and an architecture update.

Includes: backend Python, frontend source (no node_modules/dist), root scripts, requirements.
Excludes: node_modules, dist, __pycache__, .git, .vite, binaries (.joblib, .zip), dataset CSV.

Run from project root:
  python build_complete_project_documentation.py

Requires: pip install python-docx
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.enum.text import WD_LINE_SPACING
from docx.shared import Pt, RGBColor

ROOT = Path(__file__).resolve().parent

OUT_DOCX = ROOT / "Smart_Pricing_Complete_Code_And_Explanations.docx"
OUT_MD = ROOT / "Smart_Pricing_Complete_Code_And_Explanations.md"

SKIP_DIRS = {"node_modules", "dist", "__pycache__", ".git", ".vite"}
SKIP_FILES = {".DS_Store"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".joblib", ".zip", ".csv"}
SKIP_EXACT_NAMES = {"Smart_Pricing_Complete_Code_And_Explanations.md"}  # avoid self-embed if re-run

# Preferred reading order; remaining files are appended sorted.
ORDERED: list[str] = [
    "requirements.txt",
    "requirements_demo.txt",
    "HOW_TO_RUN_SMART_PRICING.txt",
    "run_demo.py",
    "build_client_zip.py",
    "build_full_code_docx.py",
    "extract_docx_text.py",
    "train_lodging_price_model.py",
    "build_complete_project_documentation.py",
    "backend/__init__.py",
    "backend/pricing_engine.py",
    "backend/storage.py",
    "backend/auth.py",
    "backend/rate_limit.py",
    "backend/ml_conversion.py",
    "backend/train_conversion_model.py",
    "backend/decision_engine.py",
    "backend/observability.py",
    "backend/events.py",
    "backend/feature_store.py",
    "backend/main.py",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/tsconfig.json",
    "frontend/vite.config.ts",
    "frontend/index.html",
    "frontend/src/vite-env.d.ts",
    "frontend/src/api.ts",
    "frontend/src/main.tsx",
    "frontend/src/styles.css",
    "frontend/src/App.tsx",
]

EXPLAIN: dict[str, str] = {
    "requirements.txt": (
        "Python dependencies for the upgraded stack: FastAPI, Uvicorn, pandas, scikit-learn, "
        "JWT auth (python-jose), rate limiting (slowapi), Prometheus metrics, and python-docx for tooling."
    ),
    "requirements_demo.txt": (
        "Minimal dependency list referenced by HOW_TO_RUN and older zip handoffs (FastAPI, Uvicorn, pandas). "
        "Prefer requirements.txt for full features."
    ),
    "HOW_TO_RUN_SMART_PRICING.txt": (
        "Human-readable runbook: one-command production flow (build UI, run_demo.py), dev mode with Vite proxy, "
        "and data requirement (Airbnb_Open_Data.csv in project root)."
    ),
    "run_demo.py": (
        "Entry point to run Uvicorn with backend.main:app from project root; serves built React from "
        "frontend/dist when SMART_PRICING_WEB_DIST is set or default path exists."
    ),
    "build_client_zip.py": (
        "Packages backend/, frontend source, CSV, and helper files into SmartPricing_Lodging_Client.zip for delivery, "
        "excluding node_modules, dist, and __pycache__."
    ),
    "build_full_code_docx.py": (
        "Earlier doc generator (subset ordering). Superseded by this script for full coverage; kept for history."
    ),
    "extract_docx_text.py": (
        "CLI utility: extracts paragraph and table text from a .docx to UTF-8 .txt (uses python-docx)."
    ),
    "train_lodging_price_model.py": (
        "Standalone training script for lodging price modeling (if present in repo); may predate conversion model."
    ),
    "build_complete_project_documentation.py": (
        "This file: collects all source paths, writes Word + Markdown with explanations and full file bodies."
    ),
    "backend/__init__.py": (
        "Marks backend as a Python package so `import backend.main` and `uvicorn backend.main:app` work."
    ),
    "backend/pricing_engine.py": (
        "Core deterministic pricing: multiplier pipeline (season, demand, supply, DOW, lead time, quality, goal, risk), "
        "clamp to min/max, smoothing, blackout/locked days, kill-switch flattening, confidence and explanation tags, "
        "plus booking_probability_mock and expected_revenue helpers for simulation fallback."
    ),
    "backend/storage.py": (
        "SQLite persistence (WAL): app_state (kill switch, regional override), host_prefs JSON per listing_id, "
        "append-only audit_log. Env SMART_PRICING_DB_PATH overrides default backend/app.db."
    ),
    "backend/auth.py": (
        "JWT helpers: HS256 access tokens with role claim; FastAPI dependencies get_current_role and require_admin; "
        "secret/algorithm from SMART_PRICING_JWT_SECRET and SMART_PRICING_JWT_ALG."
    ),
    "backend/rate_limit.py": (
        "SlowAPI limiter keyed by client IP; default 120/min; used on API routes; exception handler wired in main."
    ),
    "backend/ml_conversion.py": (
        "Loads joblib artifact (model + feature_order); predict_proba(dict) for conversion probability. "
        "Path from SMART_PRICING_CONVERSION_MODEL_PATH or default backend/models/conversion_model.joblib."
    ),
    "backend/train_conversion_model.py": (
        "Trains a scikit-learn LogisticRegression pipeline on a proxy label derived from CSV fields; "
        "writes conversion_model.joblib. Not ground-truth bookings—placeholder for real labeled data."
    ),
    "backend/decision_engine.py": (
        "Decision layer: builds feature dict from ListingSignals + price; grid search to maximize price × conversion "
        "when ML model is loaded; returns action/price/expected_revenue metadata for simulation API."
    ),
    "backend/observability.py": (
        "Logging level from SMART_PRICING_LOG_LEVEL; request middleware adds x-request-id and x-response-time-ms; "
        "optional Prometheus /metrics via prometheus-fastapi-instrumentator when installed."
    ),
    "backend/events.py": (
        "Pluggable event publisher: no-op by default; KafkaPublisher when SMART_PRICING_KAFKA_BROKERS is set "
        "(kafka-python). main.py publishes pricing.viewed, host.settings_saved, simulation.ran, admin.kill_switch."
    ),
    "backend/feature_store.py": (
        "Abstraction for listing features: in-memory stub or RedisFeatureStore when SMART_PRICING_REDIS_HOST (and port) "
        "set—scaffold for future online features."
    ),
    "backend/main.py": (
        "FastAPI app: CORS, rate limits, JWT login POST /api/auth/login, listings, pricing calendar, host settings "
        "(admin JWT), simulation with ML or mock probability + decision_engine block, admin status/kill switch, "
        "SQLite-backed state, optional Kafka events, Prometheus, static mount for frontend/dist."
    ),
    "frontend/package.json": (
        "NPM metadata: React 18, Vite 5, TypeScript; scripts for dev/build/preview."
    ),
    "frontend/package-lock.json": (
        "Exact transitive dependency versions for reproducible npm installs."
    ),
    "frontend/tsconfig.json": (
        "TypeScript: strict, ES2022, JSX react-jsx, bundler resolution for Vite."
    ),
    "frontend/vite.config.ts": (
        "Vite + React plugin; dev server port 5173; proxy /api to 127.0.0.1:8000."
    ),
    "frontend/index.html": (
        "HTML shell: title, viewport, font link, root div for React mount."
    ),
    "frontend/src/vite-env.d.ts": (
        "Vite client types reference for import.meta and env."
    ),
    "frontend/src/api.ts": (
        "Fetch wrappers for /api/listings, pricing, host settings, simulation, admin. Note: backend may require "
        "Bearer token for admin/settings endpoints—extend headers when using secured APIs."
    ),
    "frontend/src/main.tsx": (
        "React 18 createRoot, StrictMode, App + global CSS import."
    ),
    "frontend/src/styles.css": (
        "Global layout, theme variables, calendar grid, forms, modal, responsive tweaks for Smart Pricing UI."
    ),
    "frontend/src/App.tsx": (
        "Main UI: tabs Host / Simulation / Admin; listing picker; host min/max/base/goals; 60-day calendar with modal; "
        "simulation results; admin kill switch and audit (API calls must align with backend auth when enabled)."
    ),
}


def should_skip_file(rel: str, path: Path) -> bool:
    if rel.replace("\\", "/") in SKIP_EXACT_NAMES:
        return True
    low = rel.lower()
    for token in ("/node_modules/", "/dist/", "/.vite/"):
        if token in low.replace("\\", "/"):
            return True
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    return False


def collect_files() -> list[Path]:
    found: dict[str, Path] = {}

    def walk_tree(base: Path, under: str) -> None:
        if not base.exists():
            return
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                if fn in SKIP_FILES:
                    continue
                p = Path(dirpath) / fn
                rel = p.relative_to(ROOT).as_posix()
                if should_skip_file(rel, p):
                    continue
                # Only text-like sources for backend tree
                if under == "backend":
                    if p.suffix.lower() not in {".py"}:
                        continue
                if under == "frontend":
                    rel_norm = rel.replace("\\", "/")
                    if not (
                        rel_norm.startswith("frontend/src/")
                        or rel_norm
                        in {
                            "frontend/package.json",
                            "frontend/package-lock.json",
                            "frontend/tsconfig.json",
                            "frontend/tsconfig.node.json",
                            "frontend/vite.config.ts",
                            "frontend/index.html",
                        }
                    ):
                        continue
                found[rel] = p

    walk_tree(ROOT / "backend", "backend")
    walk_tree(ROOT / "frontend", "frontend")

    # Root scripts and configs
    for name in (
        "requirements.txt",
        "requirements_demo.txt",
        "HOW_TO_RUN_SMART_PRICING.txt",
        "run_demo.py",
        "build_client_zip.py",
        "build_full_code_docx.py",
        "extract_docx_text.py",
        "train_lodging_price_model.py",
        "build_complete_project_documentation.py",
    ):
        p = ROOT / name
        if p.is_file():
            rel = p.relative_to(ROOT).as_posix()
            if not should_skip_file(rel, p):
                found[rel] = p

    ordered_paths: list[Path] = []
    for rel in ORDERED:
        if rel in found:
            ordered_paths.append(found.pop(rel))
    for rel in sorted(found.keys()):
        ordered_paths.append(found[rel])

    return ordered_paths


def add_para(doc: Document, text: str, *, bold: bool = False, size: int = 11) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(size)
    if bold:
        run.bold = True
    run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)


def add_code_block_docx(doc: Document, content: str) -> None:
    if not content.endswith("\n"):
        content += "\n"
    for line in content.splitlines():
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.space_before = Pt(0)
        run = p.add_run(line)
        run.font.name = "Consolas"
        run._element.rPr.rFonts.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ascii", "Consolas")
        run._element.rPr.rFonts.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}hAnsi", "Consolas")
        run.font.size = Pt(7.5)


def write_markdown(paths: list[Path], intro: str) -> None:
    lines: list[str] = []
    lines.append("# Smart Pricing — Complete source code and explanations\n")
    lines.append(f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n\n")
    lines.append(intro)
    lines.append("\n---\n\n")

    for fp in paths:
        rel = fp.relative_to(ROOT).as_posix()
        expl = EXPLAIN.get(rel, f"Project source file: `{rel}`.")
        lines.append(f"## `{rel}`\n\n")
        lines.append(f"{expl}\n\n")
        ext = fp.suffix.lower()
        lang = {".py": "python", ".ts": "typescript", ".tsx": "tsx", ".css": "css", ".json": "json", ".html": "html", ".txt": "text"}.get(ext, "")
        body = fp.read_text(encoding="utf-8", errors="replace")
        fence = lang or "text"
        lines.append(f"```{fence}\n")
        lines.append(body)
        if not body.endswith("\n"):
            lines.append("\n")
        lines.append("```\n\n")
        lines.append(f"<!-- end of file: {rel} -->\n\n")

    OUT_MD.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    paths = collect_files()

    intro = """## Scope

This document embeds **every hand-written project source file** for the Smart Pricing (Lodging) demo: **backend (Python/FastAPI)** and **frontend (React/TypeScript/Vite)**, plus root **requirements** and **utility scripts**.

### Excluded (not application source)

- `node_modules/`, `frontend/dist/`, `__pycache__/`, `.vite/`, `.git/`
- Binaries and datasets: `*.joblib`, `*.zip`, `*.csv`
- Third-party vendored code inside `node_modules` (thousands of files; reinstall via `package-lock.json`)

### Architecture update (enterprise-oriented)

1. **Persistence**: SQLite (`backend/storage.py`) stores kill-switch, regional override, host settings, and audit log (env `SMART_PRICING_DB_PATH`).
2. **Security**: JWT login (`POST /api/auth/login`); admin-only routes use `require_admin` (`backend/auth.py`). Rate limiting via `slowapi` (`backend/rate_limit.py`).
3. **ML**: Trained conversion model (`backend/train_conversion_model.py`) saved as `backend/models/conversion_model.joblib`; inference in `backend/ml_conversion.py`. Simulation uses ML when the file exists, else mock curve.
4. **Decision engine**: `backend/decision_engine.py` grid-searches price to maximize expected revenue using the conversion model.
5. **Observability**: Request IDs + optional `/metrics` (`backend/observability.py`).
6. **Events / features (optional)**: Kafka publisher (`backend/events.py`); Redis feature store scaffold (`backend/feature_store.py`).

### Frontend note

The UI (`frontend/src/api.ts`) uses unauthenticated `fetch` for host settings and admin. If the API returns **401**, add `Authorization: Bearer <token>` from `/api/auth/login` to those calls.

"""

    write_markdown(paths, intro)

    doc = Document()
    sect = doc.sections[0]
    sect.left_margin = sect.right_margin = Pt(72)

    title = doc.add_heading("Smart Pricing (Lodging) — Complete code & explanations", 0)
    title.runs[0].font.color.rgb = RGBColor(0x1E, 0x40, 0xAF)

    doc.add_paragraph()
    add_para(
        doc,
        f"Generated (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}. "
        "Single bundle: full source listings with per-file explanations. "
        f"Total files embedded: {len(paths)}.",
        size=11,
    )
    doc.add_paragraph()
    add_para(
        doc,
        "Excluded from this bundle: node_modules, dist, __pycache__, .vite, .joblib, .zip, .csv. "
        "See also the Markdown twin: Smart_Pricing_Complete_Code_And_Explanations.md",
        size=10,
    )
    doc.add_page_break()

    # Short intro in Word (full detail in MD)
    for block in intro.split("\n"):
        if block.strip():
            add_para(doc, block.strip(), size=10)
    doc.add_page_break()

    def _part(rel: str) -> str:
        if rel.startswith("backend/"):
            return "backend"
        if rel.startswith("frontend/"):
            return "frontend"
        return "root"

    current_part: str | None = None
    for fp in paths:
        rel = fp.relative_to(ROOT).as_posix()
        part = _part(rel)
        if part != current_part:
            if part == "root":
                doc.add_heading("Part A — Project root (requirements & scripts)", level=1)
            elif part == "backend":
                doc.add_page_break()
                doc.add_heading("Part B — Backend (Python / FastAPI)", level=1)
            else:
                doc.add_page_break()
                doc.add_heading("Part C — Frontend (React / Vite / TypeScript)", level=1)
            doc.add_paragraph()
            current_part = part

        doc.add_heading(rel.replace("/", " → "), level=2)
        expl = EXPLAIN.get(rel, f"Project source file: {rel}")
        add_para(doc, expl, size=10)
        doc.add_paragraph()

        text = fp.read_text(encoding="utf-8", errors="replace")
        add_code_block_docx(doc, text)
        endp = doc.add_paragraph()
        er = endp.add_run("— end of file —")
        er.italic = True
        er.font.size = Pt(9)
        er.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
        doc.add_paragraph()

    doc.save(OUT_DOCX)
    print(f"Wrote: {OUT_DOCX}")
    print(f"Wrote: {OUT_MD}")
    print(f"Files embedded: {len(paths)}")


if __name__ == "__main__":
    main()
```

<!-- end of file: build_complete_project_documentation.py -->

## `backend/__init__.py`

Marks backend as a Python package so `import backend.main` and `uvicorn backend.main:app` work.

```python
# Smart Pricing demo backend package
```

<!-- end of file: backend/__init__.py -->

## `backend/pricing_engine.py`

Core deterministic pricing: multiplier pipeline (season, demand, supply, DOW, lead time, quality, goal, risk), clamp to min/max, smoothing, blackout/locked days, kill-switch flattening, confidence and explanation tags, plus booking_probability_mock and expected_revenue helpers for simulation fallback.

```python
"""
Lodging Smart Pricing — core computation (Jira Epic 1 style).

raw_price = base × season × demand × supply × dow × lead_time × quality
final_price = clamp(raw_price, min_price, max_price)

All multipliers are positive; smoothing can be applied per day.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

PRICE_RE = re.compile(r"[^\d.\-]+")


def parse_price(x: Any) -> float:
    if x is None:
        return float("nan")
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s:
        return float("nan")
    s = PRICE_RE.sub("", s)
    try:
        return float(s)
    except ValueError:
        return float("nan")


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


@dataclass
class ListingSignals:
    """Derived from CSV row + optional host settings."""

    listing_id: str
    base_anchor: float
    neighbourhood_group: str
    room_type: str
    lat: float
    long: float
    review_rate: float
    reviews_count: float
    availability_365: float
    instant_bookable: bool


def _quality_multiplier(review_rate: float, reviews_count: float) -> float:
    rr = review_rate if not math.isnan(review_rate) else 3.5
    rc = reviews_count if not math.isnan(reviews_count) else 0.0
    q = 0.85 + 0.03 * (rr - 3.0) + 0.02 * min(rc / 100.0, 1.0)
    return clamp(q, 0.75, 1.25)


def _demand_multiplier(seed: int, day_index: int) -> float:
    # pseudo demand oscillation + mild drift
    t = (seed % 97) / 97.0
    wave = 0.92 + 0.08 * math.sin((day_index + t * 20) / 5.0)
    return clamp(wave, 0.85, 1.15)


def _supply_multiplier(availability_365: float) -> float:
    if math.isnan(availability_365):
        availability_365 = 200.0
    # lower availability (more booked) -> tighter supply -> higher price pressure
    occ_proxy = 1.0 - min(max(availability_365 / 365.0, 0.0), 1.0)
    return clamp(0.92 + 0.20 * occ_proxy, 0.90, 1.18)


def _season_multiplier(d: date) -> float:
    # simple NYC-ish summer peak
    m = d.month
    if m in (6, 7, 8):
        return 1.08
    if m in (11, 12, 1):
        return 0.96
    return 1.0


def _dow_multiplier(d: date) -> float:
    return 1.06 if d.weekday() >= 5 else 1.0


def _lead_time_multiplier(days_ahead: int) -> float:
    # farther out -> slightly lower urgency
    if days_ahead <= 3:
        return 1.05
    if days_ahead <= 14:
        return 1.0
    return 0.97


def confidence_score(
    comps_count: int,
    variance_ratio: float,
) -> float:
    # 0..1 higher is better
    c = 0.55 + 0.25 * min(comps_count / 50.0, 1.0) - 0.15 * min(variance_ratio, 1.0)
    return float(clamp(c, 0.2, 0.95))


def explanation_tags(
    *,
    season_m: float,
    dow_m: float,
    demand_m: float,
    supply_m: float,
) -> List[str]:
    tags: List[str] = []
    if season_m > 1.03:
        tags.append("Seasonal peak")
    if dow_m > 1.02:
        tags.append("Weekend")
    if demand_m > 1.04:
        tags.append("High demand")
    if supply_m > 1.05:
        tags.append("Tight supply")
    if not tags:
        tags.append("Market baseline")
    return tags[:5]


def compute_daily_prices(
    listing: ListingSignals,
    *,
    min_price: float,
    max_price: float,
    user_base: Optional[float],
    pricing_goal: str,
    risk: str,
    start: date,
    days: int,
    locked_dates: Optional[set] = None,
    blackout_dates: Optional[set] = None,
    kill_switch: bool = False,
) -> List[Dict[str, Any]]:
    locked_dates = locked_dates or set()
    blackout_dates = blackout_dates or set()

    base = user_base if user_base and user_base > 0 else listing.base_anchor
    qm = _quality_multiplier(listing.review_rate, listing.reviews_count)
    sm = _supply_multiplier(listing.availability_365)

    goal_adj = {"revenue": 1.03, "occupancy": 0.97, "balanced": 1.0}.get(
        pricing_goal.lower(), 1.0
    )
    risk_adj = {"low": 0.98, "medium": 1.0, "high": 1.04}.get(risk.lower(), 1.0)

    seed = hash(listing.listing_id) & 0xFFFFFFFF

    out: List[Dict[str, Any]] = []
    for i in range(days):
        d = start + timedelta(days=i)
        if d in blackout_dates:
            out.append(
                {
                    "date": d.isoformat(),
                    "recommended_price": None,
                    "confidence": 0.0,
                    "tags": ["Blackout"],
                    "components": {},
                    "blocked": True,
                }
            )
            continue

        dm = _demand_multiplier(seed, i)
        season_m = _season_multiplier(d)
        dow_m = _dow_multiplier(d)
        lt_m = _lead_time_multiplier(i)

        raw = (
            base
            * season_m
            * dm
            * sm
            * dow_m
            * lt_m
            * qm
            * goal_adj
            * risk_adj
        )

        # Smoothing vs previous (simple)
        if out and out[-1].get("recommended_price") is not None and not out[-1].get("blocked"):
            prev = float(out[-1]["recommended_price"])
            raw = prev * 0.35 + raw * 0.65

        final = clamp(raw, min_price, max_price) if not kill_switch else clamp(base, min_price, max_price)

        if d in locked_dates:
            final = clamp(base, min_price, max_price)

        comps_count = 12 + (seed % 20)
        var_ratio = 0.15 + (abs(math.sin(i / 7.0)) * 0.1)
        conf = confidence_score(comps_count, var_ratio)
        tags = explanation_tags(
            season_m=season_m, dow_m=dow_m, demand_m=dm, supply_m=sm
        )

        components = {
            "base": round(base, 2),
            "season": round(season_m, 4),
            "demand": round(dm, 4),
            "supply": round(sm, 4),
            "dow": round(dow_m, 4),
            "lead_time": round(lt_m, 4),
            "quality": round(qm, 4),
            "goal": round(goal_adj, 4),
            "risk": round(risk_adj, 4),
        }

        out.append(
            {
                "date": d.isoformat(),
                "recommended_price": round(final, 2),
                "confidence": round(conf, 3),
                "tags": tags,
                "components": components,
                "blocked": False,
            }
        )

    return out


def booking_probability_mock(
    price: float,
    anchor: float,
    demand_hint: float,
) -> float:
    # smooth logistic-ish curve around anchor
    ratio = price / max(anchor, 1.0)
    p = 0.65 - 0.35 * max(0.0, ratio - 1.0) + 0.05 * (demand_hint - 1.0)
    return float(clamp(p, 0.05, 0.92))


def expected_revenue(price: float, prob: float) -> float:
    return float(price * prob)
```

<!-- end of file: backend/pricing_engine.py -->

## `backend/storage.py`

SQLite persistence (WAL): app_state (kill switch, regional override), host_prefs JSON per listing_id, append-only audit_log. Env SMART_PRICING_DB_PATH overrides default backend/app.db.

```python
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


class Storage:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._tx() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_state (
                    k TEXT PRIMARY KEY,
                    v TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS host_prefs (
                    listing_id TEXT PRIMARY KEY,
                    prefs_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )

            # Defaults
            conn.execute(
                "INSERT OR IGNORE INTO app_state(k, v) VALUES(?, ?)",
                ("kill_switch", json.dumps(False)),
            )
            conn.execute(
                "INSERT OR IGNORE INTO app_state(k, v) VALUES(?, ?)",
                ("regional_override", json.dumps(None)),
            )

    def get_state(self) -> Dict[str, Any]:
        with self._tx() as conn:
            rows = conn.execute("SELECT k, v FROM app_state").fetchall()
        out: Dict[str, Any] = {}
        for r in rows:
            out[str(r["k"])] = json.loads(r["v"])
        return out

    def set_state(self, *, kill_switch: bool, regional_override: Optional[str]) -> None:
        with self._tx() as conn:
            conn.execute(
                "INSERT INTO app_state(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                ("kill_switch", json.dumps(bool(kill_switch))),
            )
            conn.execute(
                "INSERT INTO app_state(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                ("regional_override", json.dumps(regional_override)),
            )

    def append_audit(self, action: str, payload: Dict[str, Any]) -> None:
        with self._tx() as conn:
            conn.execute(
                "INSERT INTO audit_log(ts, action, payload_json) VALUES(?, ?, ?)",
                (_utc_now_iso(), action, json.dumps(payload)),
            )

    def recent_audit(self, limit: int = 20) -> List[Dict[str, Any]]:
        limit = min(max(int(limit), 1), 200)
        with self._tx() as conn:
            rows = conn.execute(
                "SELECT ts, action, payload_json FROM audit_log ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            payload = json.loads(r["payload_json"])
            out.append({"ts": r["ts"], "action": r["action"], **payload})
        out.reverse()
        return out

    def get_host_prefs(self, listing_id: str) -> Optional[Dict[str, Any]]:
        with self._tx() as conn:
            row = conn.execute(
                "SELECT prefs_json FROM host_prefs WHERE listing_id = ?",
                (str(listing_id),),
            ).fetchone()
        if not row:
            return None
        return json.loads(row["prefs_json"])

    def set_host_prefs(self, listing_id: str, prefs: Dict[str, Any]) -> Dict[str, Any]:
        payload = json.dumps(prefs)
        with self._tx() as conn:
            conn.execute(
                """
                INSERT INTO host_prefs(listing_id, prefs_json, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(listing_id) DO UPDATE SET
                  prefs_json=excluded.prefs_json,
                  updated_at=excluded.updated_at
                """,
                (str(listing_id), payload, _utc_now_iso()),
            )
        return prefs


def default_storage(root: Path) -> Storage:
    # Allow override (useful if you want to bind-mount in containers)
    p = os.environ.get("SMART_PRICING_DB_PATH", str(root / "backend" / "app.db"))
    return Storage(Path(p))

```

<!-- end of file: backend/storage.py -->

## `backend/auth.py`

JWT helpers: HS256 access tokens with role claim; FastAPI dependencies get_current_role and require_admin; secret/algorithm from SMART_PRICING_JWT_SECRET and SMART_PRICING_JWT_ALG.

```python
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    from jose import JWTError, jwt
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "Missing dependency 'python-jose'. Install it with: python -m pip install python-jose[cryptography]"
    ) from e


_bearer = HTTPBearer(auto_error=False)


def _secret() -> str:
    return os.environ.get("SMART_PRICING_JWT_SECRET", "dev-secret-change-me")


def _algo() -> str:
    return os.environ.get("SMART_PRICING_JWT_ALG", "HS256")


def create_access_token(*, subject: str, role: str, minutes: int = 60) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(payload, _secret(), algorithm=_algo())


def get_current_role(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> str:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = creds.credentials
    try:
        payload = jwt.decode(token, _secret(), algorithms=[_algo()])
        role = str(payload.get("role") or "")
        if not role:
            raise HTTPException(status_code=401, detail="Invalid token")
        return role
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_admin(role: str = Depends(get_current_role)) -> str:
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return role

```

<!-- end of file: backend/auth.py -->

## `backend/rate_limit.py`

SlowAPI limiter keyed by client IP; default 120/min; used on API routes; exception handler wired in main.

```python
from __future__ import annotations

from fastapi import Request

try:
    from slowapi import Limiter
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "Missing dependency 'slowapi'. Install it with: python -m pip install slowapi"
    ) from e


limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return limiter._rate_limit_exceeded_handler(request, exc)

```

<!-- end of file: backend/rate_limit.py -->

## `backend/ml_conversion.py`

Loads joblib artifact (model + feature_order); predict_proba(dict) for conversion probability. Path from SMART_PRICING_CONVERSION_MODEL_PATH or default backend/models/conversion_model.joblib.

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

try:
    import joblib
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "Missing dependency 'joblib'. Install it with: python -m pip install joblib"
    ) from e


@dataclass
class ConversionModel:
    model_path: Path
    _model: Any = None
    _feature_order: Optional[list[str]] = None

    def load(self) -> None:
        blob = joblib.load(str(self.model_path))
        self._model = blob["model"]
        self._feature_order = list(blob["feature_order"])

    def predict_proba(self, features: Dict[str, float]) -> float:
        if self._model is None:
            self.load()
        assert self._feature_order is not None
        x = np.array([[float(features.get(k, 0.0)) for k in self._feature_order]], dtype=float)
        proba = self._model.predict_proba(x)[0][1]
        return float(proba)


def default_model(root: Path) -> Optional[ConversionModel]:
    p = os.environ.get(
        "SMART_PRICING_CONVERSION_MODEL_PATH",
        str(root / "backend" / "models" / "conversion_model.joblib"),
    )
    path = Path(p)
    if not path.exists():
        return None
    return ConversionModel(model_path=path)

```

<!-- end of file: backend/ml_conversion.py -->

## `backend/train_conversion_model.py`

Trains a scikit-learn LogisticRegression pipeline on a proxy label derived from CSV fields; writes conversion_model.joblib. Not ground-truth bookings—placeholder for real labeled data.

```python
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

try:
    import joblib
except Exception as e:
    raise RuntimeError("Install joblib: python -m pip install joblib") from e

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
except Exception as e:
    raise RuntimeError("Install scikit-learn: python -m pip install scikit-learn") from e


ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "Airbnb_Open_Data.csv"
OUT_PATH = ROOT / "backend" / "models" / "conversion_model.joblib"


def _to_float(s, default=0.0) -> float:
    try:
        x = float(s)
        if np.isnan(x):
            return float(default)
        return float(x)
    except Exception:
        return float(default)


def build_training_frame(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    # This dataset doesn't include true bookings. We train a proxy "conversion" label:
    # available_nights_low (more booked historically) + strong reviews => higher conversion likelihood.
    feature_order = [
        "price",
        "review_rate",
        "reviews_count",
        "availability_365",
        "instant_bookable",
        "room_type_private",
        "room_type_shared",
        "room_type_entire",
    ]

    X = []
    y = []
    for _, r in df.iterrows():
        price = _to_float(r.get("price"), default=np.nan)
        rr = _to_float(r.get("review rate number"), default=3.5)
        rc = _to_float(r.get("number of reviews"), default=0.0)
        av = _to_float(r.get("availability 365"), default=200.0)
        inst = 1.0 if str(r.get("instant_bookable", "")).strip().lower() in ("true", "t", "1", "yes") else 0.0

        rt = str(r.get("room type") or "").lower()
        rt_private = 1.0 if "private" in rt else 0.0
        rt_shared = 1.0 if "shared" in rt else 0.0
        rt_entire = 1.0 if "entire" in rt else 0.0

        # Robust price parse (handle "$123")
        if isinstance(price, float) and np.isnan(price):
            ps = str(r.get("price") or "").replace("$", "").replace(",", "").strip()
            price = _to_float(ps, default=150.0)

        feats = [
            float(price),
            float(rr),
            float(rc),
            float(av),
            float(inst),
            float(rt_private),
            float(rt_shared),
            float(rt_entire),
        ]

        # Proxy conversion label (0/1)
        label = 1.0 if (av < 180 and rr >= 3.6) else 0.0
        X.append(feats)
        y.append(label)

    return np.asarray(X, dtype=float), np.asarray(y, dtype=int), feature_order


def main() -> int:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Missing dataset: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH, low_memory=False).head(15000)
    X, y, feature_order = build_training_frame(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if len(set(y)) > 1 else None
    )

    clf = Pipeline(
        steps=[
            ("scaler", StandardScaler(with_mean=True, with_std=True)),
            ("lr", LogisticRegression(max_iter=500)),
        ]
    )
    clf.fit(X_train, y_train)
    score = clf.score(X_test, y_test)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": clf, "feature_order": feature_order, "test_accuracy": float(score)}, str(OUT_PATH))
    print(f"Saved: {OUT_PATH}")
    print(f"Proxy test accuracy: {score:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

<!-- end of file: backend/train_conversion_model.py -->

## `backend/decision_engine.py`

Decision layer: builds feature dict from ListingSignals + price; grid search to maximize price × conversion when ML model is loaded; returns action/price/expected_revenue metadata for simulation API.

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .pricing_engine import ListingSignals, clamp, expected_revenue


@dataclass
class DecisionResult:
    action: str  # NORMAL | BLOCK
    price: Optional[float]
    conversion: Optional[float]
    expected_revenue: Optional[float]
    model_used: str


def build_features(
    *,
    listing: ListingSignals,
    price: float,
) -> Dict[str, float]:
    rt = (listing.room_type or "").lower()
    return {
        "price": float(price),
        "review_rate": float(listing.review_rate or 0.0),
        "reviews_count": float(listing.reviews_count or 0.0),
        "availability_365": float(listing.availability_365 or 0.0),
        "instant_bookable": 1.0 if bool(listing.instant_bookable) else 0.0,
        "room_type_private": 1.0 if "private" in rt else 0.0,
        "room_type_shared": 1.0 if "shared" in rt else 0.0,
        "room_type_entire": 1.0 if "entire" in rt else 0.0,
    }


def optimize_price_grid(
    *,
    listing: ListingSignals,
    min_price: float,
    max_price: float,
    step: float,
    conversion_model: Any,
) -> DecisionResult:
    best_price: Optional[float] = None
    best_rev: float = -1.0
    best_p: Optional[float] = None

    p = float(min_price)
    while p <= float(max_price) + 1e-9:
        feats = build_features(listing=listing, price=p)
        prob = float(conversion_model.predict_proba(feats))
        rev = expected_revenue(p, prob)
        if rev > best_rev:
            best_rev = rev
            best_price = p
            best_p = prob
        p += float(step)

    return DecisionResult(
        action="NORMAL",
        price=best_price,
        conversion=best_p,
        expected_revenue=best_rev if best_price is not None else None,
        model_used="conversion_model",
    )


def decide_simulation(
    *,
    listing: ListingSignals,
    min_price: float,
    max_price: float,
    conversion_model: Optional[Any],
) -> Optional[DecisionResult]:
    if conversion_model is None:
        return None
    return optimize_price_grid(
        listing=listing,
        min_price=min_price,
        max_price=max_price,
        step=max(5.0, round((max_price - min_price) / 30.0, 2)),
        conversion_model=conversion_model,
    )

```

<!-- end of file: backend/decision_engine.py -->

## `backend/observability.py`

Logging level from SMART_PRICING_LOG_LEVEL; request middleware adds x-request-id and x-response-time-ms; optional Prometheus /metrics via prometheus-fastapi-instrumentator when installed.

```python
from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Callable

from fastapi import Request, Response


def configure_logging() -> None:
    level = os.environ.get("SMART_PRICING_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def request_context_middleware(request: Request, call_next: Callable):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    start = time.perf_counter()
    response: Response = await call_next(request)
    dur_ms = (time.perf_counter() - start) * 1000.0
    response.headers["x-request-id"] = rid
    response.headers["x-response-time-ms"] = f"{dur_ms:.2f}"
    return response


def setup_prometheus(app) -> None:
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
    except Exception:
        return
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

```

<!-- end of file: backend/observability.py -->

## `backend/events.py`

Pluggable event publisher: no-op by default; KafkaPublisher when SMART_PRICING_KAFKA_BROKERS is set (kafka-python). main.py publishes pricing.viewed, host.settings_saved, simulation.ran, admin.kill_switch.

```python
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional


class EventPublisher:
    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        raise NotImplementedError


class NoopPublisher(EventPublisher):
    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        return


class KafkaPublisher(EventPublisher):
    def __init__(self, bootstrap_servers: str):
        try:
            from kafka import KafkaProducer
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "Missing dependency 'kafka-python'. Install it with: python -m pip install kafka-python"
            ) from e

        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        self._producer.send(topic, payload)


def default_publisher() -> EventPublisher:
    brokers = os.environ.get("SMART_PRICING_KAFKA_BROKERS", "").strip()
    if not brokers:
        return NoopPublisher()
    return KafkaPublisher(brokers)

```

<!-- end of file: backend/events.py -->

## `backend/feature_store.py`

Abstraction for listing features: in-memory stub or RedisFeatureStore when SMART_PRICING_REDIS_HOST (and port) set—scaffold for future online features.

```python
from __future__ import annotations

import os
from typing import Any, Dict, Optional


class FeatureStore:
    def get_listing_features(self, listing_id: str) -> Optional[Dict[str, float]]:
        raise NotImplementedError


class InMemoryFeatureStore(FeatureStore):
    def __init__(self):
        self._data: Dict[str, Dict[str, float]] = {}

    def get_listing_features(self, listing_id: str) -> Optional[Dict[str, float]]:
        return self._data.get(str(listing_id))


class RedisFeatureStore(FeatureStore):
    def __init__(self, host: str, port: int):
        try:
            import redis
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "Missing dependency 'redis'. Install it with: python -m pip install redis"
            ) from e
        self._client = redis.Redis(host=host, port=port)

    def get_listing_features(self, listing_id: str) -> Optional[Dict[str, float]]:
        key = f"listing:{listing_id}"
        data = self._client.hgetall(key)
        if not data:
            return None
        out: Dict[str, float] = {}
        for k, v in data.items():
            try:
                out[k.decode("utf-8")] = float(v)
            except Exception:
                continue
        return out


def default_feature_store() -> FeatureStore:
    url = os.environ.get("SMART_PRICING_REDIS_HOST", "").strip()
    if not url:
        return InMemoryFeatureStore()
    port = int(os.environ.get("SMART_PRICING_REDIS_PORT", "6379"))
    return RedisFeatureStore(host=url, port=port)

```

<!-- end of file: backend/feature_store.py -->

## `backend/main.py`

FastAPI app: CORS, rate limits, JWT login POST /api/auth/login, listings, pricing calendar, host settings (admin JWT), simulation with ML or mock probability + decision_engine block, admin status/kill switch, SQLite-backed state, optional Kafka events, Prometheus, static mount for frontend/dist.

```python
"""
Smart Pricing demo API — aligns with Jira stories (lodging, not cars).

GET  /api/listings
GET  /api/pricing/{listing_id}
POST /api/simulation/run
GET  /api/admin/status
POST /api/admin/kill-switch
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    from .events import default_publisher
except ImportError:
    from events import default_publisher

try:
    from .observability import configure_logging, request_context_middleware, setup_prometheus
except ImportError:
    from observability import configure_logging, request_context_middleware, setup_prometheus

try:
    from .rate_limit import limiter, rate_limit_exceeded_handler
except ImportError:
    from rate_limit import limiter, rate_limit_exceeded_handler

try:
    from slowapi.errors import RateLimitExceeded
except ImportError:
    RateLimitExceeded = Exception  # type: ignore

try:
    from .auth import create_access_token, require_admin
except ImportError:
    from auth import create_access_token, require_admin

try:
    from .decision_engine import decide_simulation
except ImportError:
    from decision_engine import decide_simulation

try:
    from .pricing_engine import (
        ListingSignals,
        booking_probability_mock,
        compute_daily_prices,
        expected_revenue,
        parse_price,
    )
except ImportError:
    # Running as `python main.py` from the backend/ folder (not a package).
    from pricing_engine import (
        ListingSignals,
        booking_probability_mock,
        compute_daily_prices,
        expected_revenue,
        parse_price,
    )

try:
    from .storage import default_storage
except ImportError:
    from storage import default_storage

try:
    from .ml_conversion import default_model
except ImportError:
    from ml_conversion import default_model

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "Airbnb_Open_Data.csv"
_storage = default_storage(ROOT)
_conversion_model = default_model(ROOT)
_events = default_publisher()
configure_logging()

app = FastAPI(title="Smart Pricing (Lodging) Demo", version="1.0.0")
app.state.limiter = limiter
if RateLimitExceeded is not Exception:
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.middleware("http")(request_context_middleware)
setup_prometheus(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _log(action: str, payload: Dict[str, Any]) -> None:
    _storage.append_audit(action, payload)


def load_df() -> pd.DataFrame:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Missing dataset: {CSV_PATH}")
    return pd.read_csv(CSV_PATH, low_memory=False)


_df: Optional[pd.DataFrame] = None


def get_df() -> pd.DataFrame:
    global _df
    if _df is None:
        _df = load_df()
    return _df


def row_to_listing(row: pd.Series) -> ListingSignals:
    lid = str(int(row["id"])) if not pd.isna(row.get("id")) else "0"
    p = parse_price(row.get("price"))
    rr = float(pd.to_numeric(row.get("review rate number"), errors="coerce") or 3.5)
    rc = float(pd.to_numeric(row.get("number of reviews"), errors="coerce") or 0)
    av = float(pd.to_numeric(row.get("availability 365"), errors="coerce") or 200)
    lat = float(pd.to_numeric(row.get("lat"), errors="coerce") or 0)
    lon = float(pd.to_numeric(row.get("long"), errors="coerce") or 0)
    inst = str(row.get("instant_bookable", "")).strip().lower() in ("true", "t", "1", "yes")
    return ListingSignals(
        listing_id=lid,
        base_anchor=p if not (p is None or (isinstance(p, float) and (p != p))) and p > 0 else 150.0,
        neighbourhood_group=str(row.get("neighbourhood group") or ""),
        room_type=str(row.get("room type") or ""),
        lat=lat,
        long=lon,
        review_rate=rr,
        reviews_count=rc,
        availability_365=av,
        instant_bookable=inst,
    )


class PricingRequestQuery(BaseModel):
    days: int = Field(60, ge=7, le=90)
    from_date: Optional[str] = None


class HostSettingsBody(BaseModel):
    smart_pricing_enabled: bool = False
    min_price: float = Field(..., gt=0)
    max_price: float = Field(..., gt=0)
    base_price: Optional[float] = None
    pricing_goal: str = "balanced"  # revenue | occupancy | balanced
    risk_tolerance: str = "medium"  # low | medium | high
    update_frequency: str = "daily"
    discount_floor_protection: bool = True
    locked_dates: List[str] = []
    blackout_dates: List[str] = []


class SimulationBody(BaseModel):
    listing_id: str
    custom_price: float = Field(..., gt=0)


class KillSwitchBody(BaseModel):
    enabled: bool
    region: Optional[str] = None


class LoginBody(BaseModel):
    username: str
    password: str


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login")
@limiter.limit("10/minute")
def login(request: Request, body: LoginBody) -> Dict[str, Any]:
    # Demo-only auth. Override via env vars for local testing without code changes.
    admin_user = os.environ.get("SMART_PRICING_ADMIN_USER", "admin")
    admin_pass = os.environ.get("SMART_PRICING_ADMIN_PASS", "admin")
    if body.username == admin_user and body.password == admin_pass:
        token = create_access_token(subject=body.username, role="admin", minutes=12 * 60)
        return {"access_token": token, "token_type": "bearer", "role": "admin"}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/api/listings")
@limiter.limit("60/minute")
def listings(request: Request, limit: int = 80) -> Dict[str, Any]:
    df = get_df().head(min(max(limit, 1), 500))
    items = []
    for _, row in df.iterrows():
        items.append(
            {
                "id": str(int(row["id"])),
                "name": str(row.get("NAME") or "")[:80],
                "neighbourhood": str(row.get("neighbourhood") or ""),
                "neighbourhood_group": str(row.get("neighbourhood group") or ""),
                "room_type": str(row.get("room type") or ""),
                "price": parse_price(row.get("price")),
            }
        )
    return {"listings": items}


@app.get("/api/pricing/{listing_id}")
@limiter.limit("60/minute")
def get_pricing(
    request: Request,
    listing_id: str,
    days: int = 60,
    from_date: Optional[str] = None,
) -> Dict[str, Any]:
    df = get_df()
    hit = df[df["id"].astype(str) == str(listing_id)]
    if hit.empty:
        raise HTTPException(status_code=404, detail="Listing not found")
    row = hit.iloc[0]
    listing = row_to_listing(row)

    prefs = _storage.get_host_prefs(listing_id) or {}
    if not prefs:
        p = listing.base_anchor
        prefs = {
            "smart_pricing_enabled": True,
            "min_price": max(20.0, round(p * 0.6, 2)),
            "max_price": round(p * 1.5, 2),
            "base_price": round(p, 2),
            "pricing_goal": "balanced",
            "risk_tolerance": "medium",
            "update_frequency": "daily",
            "discount_floor_protection": True,
            "locked_dates": [],
            "blackout_dates": [],
        }

    state = _storage.get_state()
    start = date.today()
    if from_date:
        try:
            start = date.fromisoformat(from_date[:10])
        except ValueError:
            pass

    min_p = float(prefs["min_price"])
    max_p = float(prefs["max_price"])
    base = prefs.get("base_price")
    goal = str(prefs.get("pricing_goal", "balanced"))
    risk = str(prefs.get("risk_tolerance", "medium"))
    locked: Set[date] = set()
    black: Set[date] = set()
    for s in prefs.get("locked_dates") or []:
        try:
            locked.add(date.fromisoformat(str(s)[:10]))
        except ValueError:
            pass
    for s in prefs.get("blackout_dates") or []:
        try:
            black.add(date.fromisoformat(str(s)[:10]))
        except ValueError:
            pass

    calendar = compute_daily_prices(
        listing,
        min_price=min_p,
        max_price=max_p,
        user_base=float(base) if base else None,
        pricing_goal=goal,
        risk=risk,
        start=start,
        days=min(max(days, 7), 90),
        locked_dates=locked,
        blackout_dates=black,
        kill_switch=bool(state.get("kill_switch")),
    )

    suggested_try = round((min_p + max_p) / 2, 2)
    _events.publish("pricing.viewed", {"listing_id": listing_id})

    return {
        "listing": {
            "id": listing.listing_id,
            "name": str(row.get("NAME") or "")[:120],
            "neighbourhood_group": listing.neighbourhood_group,
            "room_type": listing.room_type,
        },
        "settings": prefs,
        "suggested_try_price": suggested_try,
        "kill_switch_active": bool(state.get("kill_switch")),
        "calendar": calendar,
    }


@app.post("/api/host/settings/{listing_id}")
@limiter.limit("30/minute")
def save_host_settings(
    request: Request, listing_id: str, body: HostSettingsBody, _: str = require_admin
) -> Dict[str, Any]:
    if body.max_price <= body.min_price:
        raise HTTPException(status_code=400, detail="max_price must be greater than min_price")
    if body.smart_pricing_enabled and body.min_price <= 0:
        raise HTTPException(status_code=400, detail="min/max required when Smart Pricing is on")

    prefs = {
        "smart_pricing_enabled": body.smart_pricing_enabled,
        "min_price": body.min_price,
        "max_price": body.max_price,
        "base_price": body.base_price,
        "pricing_goal": body.pricing_goal,
        "risk_tolerance": body.risk_tolerance,
        "update_frequency": body.update_frequency,
        "discount_floor_protection": body.discount_floor_protection,
        "locked_dates": body.locked_dates,
        "blackout_dates": body.blackout_dates,
    }
    _storage.set_host_prefs(listing_id, prefs)
    _log("host_settings_saved", {"listing_id": listing_id})
    _events.publish("host.settings_saved", {"listing_id": listing_id})
    return {"ok": True, "settings": prefs}


@app.post("/api/simulation/run")
@limiter.limit("60/minute")
def simulation_run(request: Request, body: SimulationBody) -> Dict[str, Any]:
    df = get_df()
    hit = df[df["id"].astype(str) == str(body.listing_id)]
    if hit.empty:
        raise HTTPException(status_code=404, detail="Listing not found")
    row = hit.iloc[0]
    listing = row_to_listing(row)
    demand = 1.02

    model_result = decide_simulation(
        listing=listing,
        min_price=max(20.0, listing.base_anchor * 0.6),
        max_price=listing.base_anchor * 1.5,
        conversion_model=_conversion_model,
    )

    if _conversion_model is not None:
        # Use real model when present.
        feats = {
            "price": float(body.custom_price),
            "review_rate": float(listing.review_rate or 0.0),
            "reviews_count": float(listing.reviews_count or 0.0),
            "availability_365": float(listing.availability_365 or 0.0),
            "instant_bookable": 1.0 if bool(listing.instant_bookable) else 0.0,
            "room_type_private": 1.0 if "private" in (listing.room_type or "").lower() else 0.0,
            "room_type_shared": 1.0 if "shared" in (listing.room_type or "").lower() else 0.0,
            "room_type_entire": 1.0 if "entire" in (listing.room_type or "").lower() else 0.0,
        }
        prob = float(_conversion_model.predict_proba(feats))
    else:
        prob = booking_probability_mock(body.custom_price, listing.base_anchor, demand)

    er = expected_revenue(body.custom_price, prob)
    _events.publish("simulation.ran", {"listing_id": body.listing_id, "price": body.custom_price})
    alts = sorted(
        [
            round(body.custom_price * 0.95, 2),
            body.custom_price,
            round(body.custom_price * 1.05, 2),
        ]
    )
    top3 = []
    for pr in alts:
        if _conversion_model is not None:
            feats = {
                "price": float(pr),
                "review_rate": float(listing.review_rate or 0.0),
                "reviews_count": float(listing.reviews_count or 0.0),
                "availability_365": float(listing.availability_365 or 0.0),
                "instant_bookable": 1.0 if bool(listing.instant_bookable) else 0.0,
                "room_type_private": 1.0 if "private" in (listing.room_type or "").lower() else 0.0,
                "room_type_shared": 1.0 if "shared" in (listing.room_type or "").lower() else 0.0,
                "room_type_entire": 1.0 if "entire" in (listing.room_type or "").lower() else 0.0,
            }
            p = float(_conversion_model.predict_proba(feats))
        else:
            p = booking_probability_mock(pr, listing.base_anchor, demand)
        top3.append(
            {"price": pr, "booking_probability": round(p, 4), "expected_revenue": round(expected_revenue(pr, p), 2)}
        )
    top3.sort(key=lambda x: x["expected_revenue"], reverse=True)
    return {
        "listing_id": body.listing_id,
        "custom_price": body.custom_price,
        "booking_probability": round(prob, 4),
        "expected_revenue": round(er, 2),
        "top_alternatives": top3[:3],
        "decision_engine": None
        if model_result is None
        else {
            "action": model_result.action,
            "recommended_price": None if model_result.price is None else round(model_result.price, 2),
            "conversion": None if model_result.conversion is None else round(model_result.conversion, 4),
            "expected_revenue": None
            if model_result.expected_revenue is None
            else round(model_result.expected_revenue, 2),
            "model_used": model_result.model_used,
        },
    }


@app.get("/api/admin/status")
@limiter.limit("30/minute")
def admin_status(request: Request, _: str = require_admin) -> Dict[str, Any]:
    df = get_df()
    state = _storage.get_state()
    return {
        "kill_switch": bool(state.get("kill_switch")),
        "regional_override": state.get("regional_override"),
        "listings_loaded": int(len(df)),
        "recent_audit": _storage.recent_audit(20),
    }


@app.post("/api/admin/kill-switch")
@limiter.limit("30/minute")
def kill_switch(request: Request, body: KillSwitchBody, _: str = require_admin) -> Dict[str, Any]:
    _storage.set_state(kill_switch=bool(body.enabled), regional_override=body.region)
    _log("kill_switch", {"enabled": body.enabled, "region": body.region})
    _events.publish("admin.kill_switch", {"enabled": body.enabled, "region": body.region})
    state = _storage.get_state()
    return {"ok": True, "kill_switch": bool(state.get("kill_switch"))}


# --- Static frontend (production): set SMART_PRICING_WEB_DIST to built Vite folder ---
_dist = os.environ.get("SMART_PRICING_WEB_DIST", str(ROOT / "frontend" / "dist"))
_static_path = Path(_dist)
if _static_path.exists():
    app.mount("/", StaticFiles(directory=str(_static_path), html=True), name="static")
else:

    @app.get("/")
    def root() -> Dict[str, Any]:
        return {
            "name": "Smart Pricing API (lodging demo)",
            "docs": "/docs",
            "hint": "Build UI: cd frontend && npm install && npm run build — then open http://127.0.0.1:8000 again. "
            "Or dev: cd frontend && npm run dev (proxies /api to :8000).",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
```

<!-- end of file: backend/main.py -->

## `frontend/package.json`

NPM metadata: React 18, Vite 5, TypeScript; scripts for dev/build/preview.

```json
{
  "name": "smart-pricing-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.6.3",
    "vite": "^5.4.11"
  }
}
```

<!-- end of file: frontend/package.json -->

## `frontend/package-lock.json`

Exact transitive dependency versions for reproducible npm installs.

```json
{
  "name": "smart-pricing-frontend",
  "version": "1.0.0",
  "lockfileVersion": 3,
  "requires": true,
  "packages": {
    "": {
      "name": "smart-pricing-frontend",
      "version": "1.0.0",
      "dependencies": {
        "react": "^18.3.1",
        "react-dom": "^18.3.1"
      },
      "devDependencies": {
        "@types/react": "^18.3.12",
        "@types/react-dom": "^18.3.1",
        "@vitejs/plugin-react": "^4.3.4",
        "typescript": "^5.6.3",
        "vite": "^5.4.11"
      }
    },
    "node_modules/@babel/code-frame": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/code-frame/-/code-frame-7.29.0.tgz",
      "integrity": "sha512-9NhCeYjq9+3uxgdtp20LSiJXJvN0FeCtNGpJxuMFZ1Kv3cWUNb6DOhJwUvcVCzKGR66cw4njwM6hrJLqgOwbcw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-validator-identifier": "^7.28.5",
        "js-tokens": "^4.0.0",
        "picocolors": "^1.1.1"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/compat-data": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/compat-data/-/compat-data-7.29.0.tgz",
      "integrity": "sha512-T1NCJqT/j9+cn8fvkt7jtwbLBfLC/1y1c7NtCeXFRgzGTsafi68MRv8yzkYSapBnFA6L3U2VSc02ciDzoAJhJg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/core": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/core/-/core-7.29.0.tgz",
      "integrity": "sha512-CGOfOJqWjg2qW/Mb6zNsDm+u5vFQ8DxXfbM09z69p5Z6+mE1ikP2jUXw+j42Pf1XTYED2Rni5f95npYeuwMDQA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/code-frame": "^7.29.0",
        "@babel/generator": "^7.29.0",
        "@babel/helper-compilation-targets": "^7.28.6",
        "@babel/helper-module-transforms": "^7.28.6",
        "@babel/helpers": "^7.28.6",
        "@babel/parser": "^7.29.0",
        "@babel/template": "^7.28.6",
        "@babel/traverse": "^7.29.0",
        "@babel/types": "^7.29.0",
        "@jridgewell/remapping": "^2.3.5",
        "convert-source-map": "^2.0.0",
        "debug": "^4.1.0",
        "gensync": "^1.0.0-beta.2",
        "json5": "^2.2.3",
        "semver": "^6.3.1"
      },
      "engines": {
        "node": ">=6.9.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/babel"
      }
    },
    "node_modules/@babel/generator": {
      "version": "7.29.1",
      "resolved": "https://registry.npmjs.org/@babel/generator/-/generator-7.29.1.tgz",
      "integrity": "sha512-qsaF+9Qcm2Qv8SRIMMscAvG4O3lJ0F1GuMo5HR/Bp02LopNgnZBC/EkbevHFeGs4ls/oPz9v+Bsmzbkbe+0dUw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/parser": "^7.29.0",
        "@babel/types": "^7.29.0",
        "@jridgewell/gen-mapping": "^0.3.12",
        "@jridgewell/trace-mapping": "^0.3.28",
        "jsesc": "^3.0.2"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-compilation-targets": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/helper-compilation-targets/-/helper-compilation-targets-7.28.6.tgz",
      "integrity": "sha512-JYtls3hqi15fcx5GaSNL7SCTJ2MNmjrkHXg4FSpOA/grxK8KwyZ5bubHsCq8FXCkua6xhuaaBit+3b7+VZRfcA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/compat-data": "^7.28.6",
        "@babel/helper-validator-option": "^7.27.1",
        "browserslist": "^4.24.0",
        "lru-cache": "^5.1.1",
        "semver": "^6.3.1"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-globals": {
      "version": "7.28.0",
      "resolved": "https://registry.npmjs.org/@babel/helper-globals/-/helper-globals-7.28.0.tgz",
      "integrity": "sha512-+W6cISkXFa1jXsDEdYA8HeevQT/FULhxzR99pxphltZcVaugps53THCeiWA8SguxxpSp3gKPiuYfSWopkLQ4hw==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-module-imports": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/helper-module-imports/-/helper-module-imports-7.28.6.tgz",
      "integrity": "sha512-l5XkZK7r7wa9LucGw9LwZyyCUscb4x37JWTPz7swwFE/0FMQAGpiWUZn8u9DzkSBWEcK25jmvubfpw2dnAMdbw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/traverse": "^7.28.6",
        "@babel/types": "^7.28.6"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-module-transforms": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/helper-module-transforms/-/helper-module-transforms-7.28.6.tgz",
      "integrity": "sha512-67oXFAYr2cDLDVGLXTEABjdBJZ6drElUSI7WKp70NrpyISso3plG9SAGEF6y7zbha/wOzUByWWTJvEDVNIUGcA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-module-imports": "^7.28.6",
        "@babel/helper-validator-identifier": "^7.28.5",
        "@babel/traverse": "^7.28.6"
      },
      "engines": {
        "node": ">=6.9.0"
      },
      "peerDependencies": {
        "@babel/core": "^7.0.0"
      }
    },
    "node_modules/@babel/helper-plugin-utils": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/helper-plugin-utils/-/helper-plugin-utils-7.28.6.tgz",
      "integrity": "sha512-S9gzZ/bz83GRysI7gAD4wPT/AI3uCnY+9xn+Mx/KPs2JwHJIz1W8PZkg2cqyt3RNOBM8ejcXhV6y8Og7ly/Dug==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-string-parser": {
      "version": "7.27.1",
      "resolved": "https://registry.npmjs.org/@babel/helper-string-parser/-/helper-string-parser-7.27.1.tgz",
      "integrity": "sha512-qMlSxKbpRlAridDExk92nSobyDdpPijUq2DW6oDnUqd0iOGxmQjyqhMIihI9+zv4LPyZdRje2cavWPbCbWm3eA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-validator-identifier": {
      "version": "7.28.5",
      "resolved": "https://registry.npmjs.org/@babel/helper-validator-identifier/-/helper-validator-identifier-7.28.5.tgz",
      "integrity": "sha512-qSs4ifwzKJSV39ucNjsvc6WVHs6b7S03sOh2OcHF9UHfVPqWWALUsNUVzhSBiItjRZoLHx7nIarVjqKVusUZ1Q==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-validator-option": {
      "version": "7.27.1",
      "resolved": "https://registry.npmjs.org/@babel/helper-validator-option/-/helper-validator-option-7.27.1.tgz",
      "integrity": "sha512-YvjJow9FxbhFFKDSuFnVCe2WxXk1zWc22fFePVNEaWJEu8IrZVlda6N0uHwzZrUM1il7NC9Mlp4MaJYbYd9JSg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helpers": {
      "version": "7.29.2",
      "resolved": "https://registry.npmjs.org/@babel/helpers/-/helpers-7.29.2.tgz",
      "integrity": "sha512-HoGuUs4sCZNezVEKdVcwqmZN8GoHirLUcLaYVNBK2J0DadGtdcqgr3BCbvH8+XUo4NGjNl3VOtSjEKNzqfFgKw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/template": "^7.28.6",
        "@babel/types": "^7.29.0"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/parser": {
      "version": "7.29.2",
      "resolved": "https://registry.npmjs.org/@babel/parser/-/parser-7.29.2.tgz",
      "integrity": "sha512-4GgRzy/+fsBa72/RZVJmGKPmZu9Byn8o4MoLpmNe1m8ZfYnz5emHLQz3U4gLud6Zwl0RZIcgiLD7Uq7ySFuDLA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/types": "^7.29.0"
      },
      "bin": {
        "parser": "bin/babel-parser.js"
      },
      "engines": {
        "node": ">=6.0.0"
      }
    },
    "node_modules/@babel/plugin-transform-react-jsx-self": {
      "version": "7.27.1",
      "resolved": "https://registry.npmjs.org/@babel/plugin-transform-react-jsx-self/-/plugin-transform-react-jsx-self-7.27.1.tgz",
      "integrity": "sha512-6UzkCs+ejGdZ5mFFC/OCUrv028ab2fp1znZmCZjAOBKiBK2jXD1O+BPSfX8X2qjJ75fZBMSnQn3Rq2mrBJK2mw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-plugin-utils": "^7.27.1"
      },
      "engines": {
        "node": ">=6.9.0"
      },
      "peerDependencies": {
        "@babel/core": "^7.0.0-0"
      }
    },
    "node_modules/@babel/plugin-transform-react-jsx-source": {
      "version": "7.27.1",
      "resolved": "https://registry.npmjs.org/@babel/plugin-transform-react-jsx-source/-/plugin-transform-react-jsx-source-7.27.1.tgz",
      "integrity": "sha512-zbwoTsBruTeKB9hSq73ha66iFeJHuaFkUbwvqElnygoNbj/jHRsSeokowZFN3CZ64IvEqcmmkVe89OPXc7ldAw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-plugin-utils": "^7.27.1"
      },
      "engines": {
        "node": ">=6.9.0"
      },
      "peerDependencies": {
        "@babel/core": "^7.0.0-0"
      }
    },
    "node_modules/@babel/template": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/template/-/template-7.28.6.tgz",
      "integrity": "sha512-YA6Ma2KsCdGb+WC6UpBVFJGXL58MDA6oyONbjyF/+5sBgxY/dwkhLogbMT2GXXyU84/IhRw/2D1Os1B/giz+BQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/code-frame": "^7.28.6",
        "@babel/parser": "^7.28.6",
        "@babel/types": "^7.28.6"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/traverse": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/traverse/-/traverse-7.29.0.tgz",
      "integrity": "sha512-4HPiQr0X7+waHfyXPZpWPfWL/J7dcN1mx9gL6WdQVMbPnF3+ZhSMs8tCxN7oHddJE9fhNE7+lxdnlyemKfJRuA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/code-frame": "^7.29.0",
        "@babel/generator": "^7.29.0",
        "@babel/helper-globals": "^7.28.0",
        "@babel/parser": "^7.29.0",
        "@babel/template": "^7.28.6",
        "@babel/types": "^7.29.0",
        "debug": "^4.3.1"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/types": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/types/-/types-7.29.0.tgz",
      "integrity": "sha512-LwdZHpScM4Qz8Xw2iKSzS+cfglZzJGvofQICy7W7v4caru4EaAmyUuO6BGrbyQ2mYV11W0U8j5mBhd14dd3B0A==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-string-parser": "^7.27.1",
        "@babel/helper-validator-identifier": "^7.28.5"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@esbuild/aix-ppc64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/aix-ppc64/-/aix-ppc64-0.21.5.tgz",
      "integrity": "sha512-1SDgH6ZSPTlggy1yI6+Dbkiz8xzpHJEVAlF/AM1tHPLsf5STom9rwtjE4hKAF20FfXXNTFqEYXyJNWh1GiZedQ==",
      "cpu": [
        "ppc64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "aix"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/android-arm": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/android-arm/-/android-arm-0.21.5.tgz",
      "integrity": "sha512-vCPvzSjpPHEi1siZdlvAlsPxXl7WbOVUBBAowWug4rJHb68Ox8KualB+1ocNvT5fjv6wpkX6o/iEpbDrf68zcg==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "android"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/android-arm64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/android-arm64/-/android-arm64-0.21.5.tgz",
      "integrity": "sha512-c0uX9VAUBQ7dTDCjq+wdyGLowMdtR/GoC2U5IYk/7D1H1JYC0qseD7+11iMP2mRLN9RcCMRcjC4YMclCzGwS/A==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "android"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/android-x64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/android-x64/-/android-x64-0.21.5.tgz",
      "integrity": "sha512-D7aPRUUNHRBwHxzxRvp856rjUHRFW1SdQATKXH2hqA0kAZb1hKmi02OpYRacl0TxIGz/ZmXWlbZgjwWYaCakTA==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "android"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/darwin-arm64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/darwin-arm64/-/darwin-arm64-0.21.5.tgz",
      "integrity": "sha512-DwqXqZyuk5AiWWf3UfLiRDJ5EDd49zg6O9wclZ7kUMv2WRFr4HKjXp/5t8JZ11QbQfUS6/cRCKGwYhtNAY88kQ==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/darwin-x64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/darwin-x64/-/darwin-x64-0.21.5.tgz",
      "integrity": "sha512-se/JjF8NlmKVG4kNIuyWMV/22ZaerB+qaSi5MdrXtd6R08kvs2qCN4C09miupktDitvh8jRFflwGFBQcxZRjbw==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/freebsd-arm64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/freebsd-arm64/-/freebsd-arm64-0.21.5.tgz",
      "integrity": "sha512-5JcRxxRDUJLX8JXp/wcBCy3pENnCgBR9bN6JsY4OmhfUtIHe3ZW0mawA7+RDAcMLrMIZaf03NlQiX9DGyB8h4g==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "freebsd"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/freebsd-x64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/freebsd-x64/-/freebsd-x64-0.21.5.tgz",
      "integrity": "sha512-J95kNBj1zkbMXtHVH29bBriQygMXqoVQOQYA+ISs0/2l3T9/kj42ow2mpqerRBxDJnmkUDCaQT/dfNXWX/ZZCQ==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "freebsd"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-arm": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-arm/-/linux-arm-0.21.5.tgz",
      "integrity": "sha512-bPb5AHZtbeNGjCKVZ9UGqGwo8EUu4cLq68E95A53KlxAPRmUyYv2D6F0uUI65XisGOL1hBP5mTronbgo+0bFcA==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-arm64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-arm64/-/linux-arm64-0.21.5.tgz",
      "integrity": "sha512-ibKvmyYzKsBeX8d8I7MH/TMfWDXBF3db4qM6sy+7re0YXya+K1cem3on9XgdT2EQGMu4hQyZhan7TeQ8XkGp4Q==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-ia32": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-ia32/-/linux-ia32-0.21.5.tgz",
      "integrity": "sha512-YvjXDqLRqPDl2dvRODYmmhz4rPeVKYvppfGYKSNGdyZkA01046pLWyRKKI3ax8fbJoK5QbxblURkwK/MWY18Tg==",
      "cpu": [
        "ia32"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-loong64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-loong64/-/linux-loong64-0.21.5.tgz",
      "integrity": "sha512-uHf1BmMG8qEvzdrzAqg2SIG/02+4/DHB6a9Kbya0XDvwDEKCoC8ZRWI5JJvNdUjtciBGFQ5PuBlpEOXQj+JQSg==",
      "cpu": [
        "loong64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-mips64el": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-mips64el/-/linux-mips64el-0.21.5.tgz",
      "integrity": "sha512-IajOmO+KJK23bj52dFSNCMsz1QP1DqM6cwLUv3W1QwyxkyIWecfafnI555fvSGqEKwjMXVLokcV5ygHW5b3Jbg==",
      "cpu": [
        "mips64el"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-ppc64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-ppc64/-/linux-ppc64-0.21.5.tgz",
      "integrity": "sha512-1hHV/Z4OEfMwpLO8rp7CvlhBDnjsC3CttJXIhBi+5Aj5r+MBvy4egg7wCbe//hSsT+RvDAG7s81tAvpL2XAE4w==",
      "cpu": [
        "ppc64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-riscv64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-riscv64/-/linux-riscv64-0.21.5.tgz",
      "integrity": "sha512-2HdXDMd9GMgTGrPWnJzP2ALSokE/0O5HhTUvWIbD3YdjME8JwvSCnNGBnTThKGEB91OZhzrJ4qIIxk/SBmyDDA==",
      "cpu": [
        "riscv64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-s390x": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-s390x/-/linux-s390x-0.21.5.tgz",
      "integrity": "sha512-zus5sxzqBJD3eXxwvjN1yQkRepANgxE9lgOW2qLnmr8ikMTphkjgXu1HR01K4FJg8h1kEEDAqDcZQtbrRnB41A==",
      "cpu": [
        "s390x"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-x64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-x64/-/linux-x64-0.21.5.tgz",
      "integrity": "sha512-1rYdTpyv03iycF1+BhzrzQJCdOuAOtaqHTWJZCWvijKD2N5Xu0TtVC8/+1faWqcP9iBCWOmjmhoH94dH82BxPQ==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/netbsd-x64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/netbsd-x64/-/netbsd-x64-0.21.5.tgz",
      "integrity": "sha512-Woi2MXzXjMULccIwMnLciyZH4nCIMpWQAs049KEeMvOcNADVxo0UBIQPfSmxB3CWKedngg7sWZdLvLczpe0tLg==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "netbsd"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/openbsd-x64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/openbsd-x64/-/openbsd-x64-0.21.5.tgz",
      "integrity": "sha512-HLNNw99xsvx12lFBUwoT8EVCsSvRNDVxNpjZ7bPn947b8gJPzeHWyNVhFsaerc0n3TsbOINvRP2byTZ5LKezow==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "openbsd"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/sunos-x64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/sunos-x64/-/sunos-x64-0.21.5.tgz",
      "integrity": "sha512-6+gjmFpfy0BHU5Tpptkuh8+uw3mnrvgs+dSPQXQOv3ekbordwnzTVEb4qnIvQcYXq6gzkyTnoZ9dZG+D4garKg==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "sunos"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/win32-arm64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/win32-arm64/-/win32-arm64-0.21.5.tgz",
      "integrity": "sha512-Z0gOTd75VvXqyq7nsl93zwahcTROgqvuAcYDUr+vOv8uHhNSKROyU961kgtCD1e95IqPKSQKH7tBTslnS3tA8A==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/win32-ia32": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/win32-ia32/-/win32-ia32-0.21.5.tgz",
      "integrity": "sha512-SWXFF1CL2RVNMaVs+BBClwtfZSvDgtL//G/smwAc5oVK/UPu2Gu9tIaRgFmYFFKrmg3SyAjSrElf0TiJ1v8fYA==",
      "cpu": [
        "ia32"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/win32-x64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/win32-x64/-/win32-x64-0.21.5.tgz",
      "integrity": "sha512-tQd/1efJuzPC6rCFwEvLtci/xNFcTZknmXs98FYDfGE4wP9ClFV98nyKrzJKVPMhdDnjzLhdUyMX4PsQAPjwIw==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@jridgewell/gen-mapping": {
      "version": "0.3.13",
      "resolved": "https://registry.npmjs.org/@jridgewell/gen-mapping/-/gen-mapping-0.3.13.tgz",
      "integrity": "sha512-2kkt/7niJ6MgEPxF0bYdQ6etZaA+fQvDcLKckhy1yIQOzaoKjBBjSj63/aLVjYE3qhRt5dvM+uUyfCg6UKCBbA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@jridgewell/sourcemap-codec": "^1.5.0",
        "@jridgewell/trace-mapping": "^0.3.24"
      }
    },
    "node_modules/@jridgewell/remapping": {
      "version": "2.3.5",
      "resolved": "https://registry.npmjs.org/@jridgewell/remapping/-/remapping-2.3.5.tgz",
      "integrity": "sha512-LI9u/+laYG4Ds1TDKSJW2YPrIlcVYOwi2fUC6xB43lueCjgxV4lffOCZCtYFiH6TNOX+tQKXx97T4IKHbhyHEQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@jridgewell/gen-mapping": "^0.3.5",
        "@jridgewell/trace-mapping": "^0.3.24"
      }
    },
    "node_modules/@jridgewell/resolve-uri": {
      "version": "3.1.2",
      "resolved": "https://registry.npmjs.org/@jridgewell/resolve-uri/-/resolve-uri-3.1.2.tgz",
      "integrity": "sha512-bRISgCIjP20/tbWSPWMEi54QVPRZExkuD9lJL+UIxUKtwVJA8wW1Trb1jMs1RFXo1CBTNZ/5hpC9QvmKWdopKw==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.0.0"
      }
    },
    "node_modules/@jridgewell/sourcemap-codec": {
      "version": "1.5.5",
      "resolved": "https://registry.npmjs.org/@jridgewell/sourcemap-codec/-/sourcemap-codec-1.5.5.tgz",
      "integrity": "sha512-cYQ9310grqxueWbl+WuIUIaiUaDcj7WOq5fVhEljNVgRfOUhY9fy2zTvfoqWsnebh8Sl70VScFbICvJnLKB0Og==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@jridgewell/trace-mapping": {
      "version": "0.3.31",
      "resolved": "https://registry.npmjs.org/@jridgewell/trace-mapping/-/trace-mapping-0.3.31.tgz",
      "integrity": "sha512-zzNR+SdQSDJzc8joaeP8QQoCQr8NuYx2dIIytl1QeBEZHJ9uW6hebsrYgbz8hJwUQao3TWCMtmfV8Nu1twOLAw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@jridgewell/resolve-uri": "^3.1.0",
        "@jridgewell/sourcemap-codec": "^1.4.14"
      }
    },
    "node_modules/@rolldown/pluginutils": {
      "version": "1.0.0-beta.27",
      "resolved": "https://registry.npmjs.org/@rolldown/pluginutils/-/pluginutils-1.0.0-beta.27.tgz",
      "integrity": "sha512-+d0F4MKMCbeVUJwG96uQ4SgAznZNSq93I3V+9NHA4OpvqG8mRCpGdKmK8l/dl02h2CCDHwW2FqilnTyDcAnqjA==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@rollup/rollup-android-arm-eabi": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-android-arm-eabi/-/rollup-android-arm-eabi-4.60.1.tgz",
      "integrity": "sha512-d6FinEBLdIiK+1uACUttJKfgZREXrF0Qc2SmLII7W2AD8FfiZ9Wjd+rD/iRuf5s5dWrr1GgwXCvPqOuDquOowA==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "android"
      ]
    },
    "node_modules/@rollup/rollup-android-arm64": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-android-arm64/-/rollup-android-arm64-4.60.1.tgz",
      "integrity": "sha512-YjG/EwIDvvYI1YvYbHvDz/BYHtkY4ygUIXHnTdLhG+hKIQFBiosfWiACWortsKPKU/+dUwQQCKQM3qrDe8c9BA==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "android"
      ]
    },
    "node_modules/@rollup/rollup-darwin-arm64": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-darwin-arm64/-/rollup-darwin-arm64-4.60.1.tgz",
      "integrity": "sha512-mjCpF7GmkRtSJwon+Rq1N8+pI+8l7w5g9Z3vWj4T7abguC4Czwi3Yu/pFaLvA3TTeMVjnu3ctigusqWUfjZzvw==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ]
    },
    "node_modules/@rollup/rollup-darwin-x64": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-darwin-x64/-/rollup-darwin-x64-4.60.1.tgz",
      "integrity": "sha512-haZ7hJ1JT4e9hqkoT9R/19XW2QKqjfJVv+i5AGg57S+nLk9lQnJ1F/eZloRO3o9Scy9CM3wQ9l+dkXtcBgN5Ew==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ]
    },
    "node_modules/@rollup/rollup-freebsd-arm64": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-freebsd-arm64/-/rollup-freebsd-arm64-4.60.1.tgz",
      "integrity": "sha512-czw90wpQq3ZsAVBlinZjAYTKduOjTywlG7fEeWKUA7oCmpA8xdTkxZZlwNJKWqILlq0wehoZcJYfBvOyhPTQ6w==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "freebsd"
      ]
    },
    "node_modules/@rollup/rollup-freebsd-x64": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-freebsd-x64/-/rollup-freebsd-x64-4.60.1.tgz",
      "integrity": "sha512-KVB2rqsxTHuBtfOeySEyzEOB7ltlB/ux38iu2rBQzkjbwRVlkhAGIEDiiYnO2kFOkJp+Z7pUXKyrRRFuFUKt+g==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "freebsd"
      ]
    },
    "node_modules/@rollup/rollup-linux-arm-gnueabihf": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-arm-gnueabihf/-/rollup-linux-arm-gnueabihf-4.60.1.tgz",
      "integrity": "sha512-L+34Qqil+v5uC0zEubW7uByo78WOCIrBvci69E7sFASRl0X7b/MB6Cqd1lky/CtcSVTydWa2WZwFuWexjS5o6g==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-arm-musleabihf": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-arm-musleabihf/-/rollup-linux-arm-musleabihf-4.60.1.tgz",
      "integrity": "sha512-n83O8rt4v34hgFzlkb1ycniJh7IR5RCIqt6mz1VRJD6pmhRi0CXdmfnLu9dIUS6buzh60IvACM842Ffb3xd6Gg==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-arm64-gnu": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-arm64-gnu/-/rollup-linux-arm64-gnu-4.60.1.tgz",
      "integrity": "sha512-Nql7sTeAzhTAja3QXeAI48+/+GjBJ+QmAH13snn0AJSNL50JsDqotyudHyMbO2RbJkskbMbFJfIJKWA6R1LCJQ==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-arm64-musl": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-arm64-musl/-/rollup-linux-arm64-musl-4.60.1.tgz",
      "integrity": "sha512-+pUymDhd0ys9GcKZPPWlFiZ67sTWV5UU6zOJat02M1+PiuSGDziyRuI/pPue3hoUwm2uGfxdL+trT6Z9rxnlMA==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-loong64-gnu": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-loong64-gnu/-/rollup-linux-loong64-gnu-4.60.1.tgz",
      "integrity": "sha512-VSvgvQeIcsEvY4bKDHEDWcpW4Yw7BtlKG1GUT4FzBUlEKQK0rWHYBqQt6Fm2taXS+1bXvJT6kICu5ZwqKCnvlQ==",
      "cpu": [
        "loong64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-loong64-musl": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-loong64-musl/-/rollup-linux-loong64-musl-4.60.1.tgz",
      "integrity": "sha512-4LqhUomJqwe641gsPp6xLfhqWMbQV04KtPp7/dIp0nzPxAkNY1AbwL5W0MQpcalLYk07vaW9Kp1PBhdpZYYcEw==",
      "cpu": [
        "loong64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-ppc64-gnu": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-ppc64-gnu/-/rollup-linux-ppc64-gnu-4.60.1.tgz",
      "integrity": "sha512-tLQQ9aPvkBxOc/EUT6j3pyeMD6Hb8QF2BTBnCQWP/uu1lhc9AIrIjKnLYMEroIz/JvtGYgI9dF3AxHZNaEH0rw==",
      "cpu": [
        "ppc64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-ppc64-musl": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-ppc64-musl/-/rollup-linux-ppc64-musl-4.60.1.tgz",
      "integrity": "sha512-RMxFhJwc9fSXP6PqmAz4cbv3kAyvD1etJFjTx4ONqFP9DkTkXsAMU4v3Vyc5BgzC+anz7nS/9tp4obsKfqkDHg==",
      "cpu": [
        "ppc64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-riscv64-gnu": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-riscv64-gnu/-/rollup-linux-riscv64-gnu-4.60.1.tgz",
      "integrity": "sha512-QKgFl+Yc1eEk6MmOBfRHYF6lTxiiiV3/z/BRrbSiW2I7AFTXoBFvdMEyglohPj//2mZS4hDOqeB0H1ACh3sBbg==",
      "cpu": [
        "riscv64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-riscv64-musl": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-riscv64-musl/-/rollup-linux-riscv64-musl-4.60.1.tgz",
      "integrity": "sha512-RAjXjP/8c6ZtzatZcA1RaQr6O1TRhzC+adn8YZDnChliZHviqIjmvFwHcxi4JKPSDAt6Uhf/7vqcBzQJy0PDJg==",
      "cpu": [
        "riscv64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-s390x-gnu": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-s390x-gnu/-/rollup-linux-s390x-gnu-4.60.1.tgz",
      "integrity": "sha512-wcuocpaOlaL1COBYiA89O6yfjlp3RwKDeTIA0hM7OpmhR1Bjo9j31G1uQVpDlTvwxGn2nQs65fBFL5UFd76FcQ==",
      "cpu": [
        "s390x"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-x64-gnu": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-x64-gnu/-/rollup-linux-x64-gnu-4.60.1.tgz",
      "integrity": "sha512-77PpsFQUCOiZR9+LQEFg9GClyfkNXj1MP6wRnzYs0EeWbPcHs02AXu4xuUbM1zhwn3wqaizle3AEYg5aeoohhg==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-x64-musl": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-x64-musl/-/rollup-linux-x64-musl-4.60.1.tgz",
      "integrity": "sha512-5cIATbk5vynAjqqmyBjlciMJl1+R/CwX9oLk/EyiFXDWd95KpHdrOJT//rnUl4cUcskrd0jCCw3wpZnhIHdD9w==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-openbsd-x64": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-openbsd-x64/-/rollup-openbsd-x64-4.60.1.tgz",
      "integrity": "sha512-cl0w09WsCi17mcmWqqglez9Gk8isgeWvoUZ3WiJFYSR3zjBQc2J5/ihSjpl+VLjPqjQ/1hJRcqBfLjssREQILw==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "openbsd"
      ]
    },
    "node_modules/@rollup/rollup-openharmony-arm64": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-openharmony-arm64/-/rollup-openharmony-arm64-4.60.1.tgz",
      "integrity": "sha512-4Cv23ZrONRbNtbZa37mLSueXUCtN7MXccChtKpUnQNgF010rjrjfHx3QxkS2PI7LqGT5xXyYs1a7LbzAwT0iCA==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "openharmony"
      ]
    },
    "node_modules/@rollup/rollup-win32-arm64-msvc": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-arm64-msvc/-/rollup-win32-arm64-msvc-4.60.1.tgz",
      "integrity": "sha512-i1okWYkA4FJICtr7KpYzFpRTHgy5jdDbZiWfvny21iIKky5YExiDXP+zbXzm3dUcFpkEeYNHgQ5fuG236JPq0g==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@rollup/rollup-win32-ia32-msvc": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-ia32-msvc/-/rollup-win32-ia32-msvc-4.60.1.tgz",
      "integrity": "sha512-u09m3CuwLzShA0EYKMNiFgcjjzwqtUMLmuCJLeZWjjOYA3IT2Di09KaxGBTP9xVztWyIWjVdsB2E9goMjZvTQg==",
      "cpu": [
        "ia32"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@rollup/rollup-win32-x64-gnu": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-x64-gnu/-/rollup-win32-x64-gnu-4.60.1.tgz",
      "integrity": "sha512-k+600V9Zl1CM7eZxJgMyTUzmrmhB/0XZnF4pRypKAlAgxmedUA+1v9R+XOFv56W4SlHEzfeMtzujLJD22Uz5zg==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@rollup/rollup-win32-x64-msvc": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-x64-msvc/-/rollup-win32-x64-msvc-4.60.1.tgz",
      "integrity": "sha512-lWMnixq/QzxyhTV6NjQJ4SFo1J6PvOX8vUx5Wb4bBPsEb+8xZ89Bz6kOXpfXj9ak9AHTQVQzlgzBEc1SyM27xQ==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@types/babel__core": {
      "version": "7.20.5",
      "resolved": "https://registry.npmjs.org/@types/babel__core/-/babel__core-7.20.5.tgz",
      "integrity": "sha512-qoQprZvz5wQFJwMDqeseRXWv3rqMvhgpbXFfVyWhbx9X47POIA6i/+dXefEmZKoAgOaTdaIgNSMqMIU61yRyzA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/parser": "^7.20.7",
        "@babel/types": "^7.20.7",
        "@types/babel__generator": "*",
        "@types/babel__template": "*",
        "@types/babel__traverse": "*"
      }
    },
    "node_modules/@types/babel__generator": {
      "version": "7.27.0",
      "resolved": "https://registry.npmjs.org/@types/babel__generator/-/babel__generator-7.27.0.tgz",
      "integrity": "sha512-ufFd2Xi92OAVPYsy+P4n7/U7e68fex0+Ee8gSG9KX7eo084CWiQ4sdxktvdl0bOPupXtVJPY19zk6EwWqUQ8lg==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/types": "^7.0.0"
      }
    },
    "node_modules/@types/babel__template": {
      "version": "7.4.4",
      "resolved": "https://registry.npmjs.org/@types/babel__template/-/babel__template-7.4.4.tgz",
      "integrity": "sha512-h/NUaSyG5EyxBIp8YRxo4RMe2/qQgvyowRwVMzhYhBCONbW8PUsg4lkFMrhgZhUe5z3L3MiLDuvyJ/CaPa2A8A==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/parser": "^7.1.0",
        "@babel/types": "^7.0.0"
      }
    },
    "node_modules/@types/babel__traverse": {
      "version": "7.28.0",
      "resolved": "https://registry.npmjs.org/@types/babel__traverse/-/babel__traverse-7.28.0.tgz",
      "integrity": "sha512-8PvcXf70gTDZBgt9ptxJ8elBeBjcLOAcOtoO/mPJjtji1+CdGbHgm77om1GrsPxsiE+uXIpNSK64UYaIwQXd4Q==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/types": "^7.28.2"
      }
    },
    "node_modules/@types/estree": {
      "version": "1.0.8",
      "resolved": "https://registry.npmjs.org/@types/estree/-/estree-1.0.8.tgz",
      "integrity": "sha512-dWHzHa2WqEXI/O1E9OjrocMTKJl2mSrEolh1Iomrv6U+JuNwaHXsXx9bLu5gG7BUWFIN0skIQJQ/L1rIex4X6w==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@types/prop-types": {
      "version": "15.7.15",
      "resolved": "https://registry.npmjs.org/@types/prop-types/-/prop-types-15.7.15.tgz",
      "integrity": "sha512-F6bEyamV9jKGAFBEmlQnesRPGOQqS2+Uwi0Em15xenOxHaf2hv6L8YCVn3rPdPJOiJfPiCnLIRyvwVaqMY3MIw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@types/react": {
      "version": "18.3.28",
      "resolved": "https://registry.npmjs.org/@types/react/-/react-18.3.28.tgz",
      "integrity": "sha512-z9VXpC7MWrhfWipitjNdgCauoMLRdIILQsAEV+ZesIzBq/oUlxk0m3ApZuMFCXdnS4U7KrI+l3WRUEGQ8K1QKw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@types/prop-types": "*",
        "csstype": "^3.2.2"
      }
    },
    "node_modules/@types/react-dom": {
      "version": "18.3.7",
      "resolved": "https://registry.npmjs.org/@types/react-dom/-/react-dom-18.3.7.tgz",
      "integrity": "sha512-MEe3UeoENYVFXzoXEWsvcpg6ZvlrFNlOQ7EOsvhI3CfAXwzPfO8Qwuxd40nepsYKqyyVQnTdEfv68q91yLcKrQ==",
      "dev": true,
      "license": "MIT",
      "peerDependencies": {
        "@types/react": "^18.0.0"
      }
    },
    "node_modules/@vitejs/plugin-react": {
      "version": "4.7.0",
      "resolved": "https://registry.npmjs.org/@vitejs/plugin-react/-/plugin-react-4.7.0.tgz",
      "integrity": "sha512-gUu9hwfWvvEDBBmgtAowQCojwZmJ5mcLn3aufeCsitijs3+f2NsrPtlAWIR6OPiqljl96GVCUbLe0HyqIpVaoA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/core": "^7.28.0",
        "@babel/plugin-transform-react-jsx-self": "^7.27.1",
        "@babel/plugin-transform-react-jsx-source": "^7.27.1",
        "@rolldown/pluginutils": "1.0.0-beta.27",
        "@types/babel__core": "^7.20.5",
        "react-refresh": "^0.17.0"
      },
      "engines": {
        "node": "^14.18.0 || >=16.0.0"
      },
      "peerDependencies": {
        "vite": "^4.2.0 || ^5.0.0 || ^6.0.0 || ^7.0.0"
      }
    },
    "node_modules/baseline-browser-mapping": {
      "version": "2.10.16",
      "resolved": "https://registry.npmjs.org/baseline-browser-mapping/-/baseline-browser-mapping-2.10.16.tgz",
      "integrity": "sha512-Lyf3aK28zpsD1yQMiiHD4RvVb6UdMoo8xzG2XzFIfR9luPzOpcBlAsT/qfB1XWS1bxWT+UtE4WmQgsp297FYOA==",
      "dev": true,
      "license": "Apache-2.0",
      "bin": {
        "baseline-browser-mapping": "dist/cli.cjs"
      },
      "engines": {
        "node": ">=6.0.0"
      }
    },
    "node_modules/browserslist": {
      "version": "4.28.2",
      "resolved": "https://registry.npmjs.org/browserslist/-/browserslist-4.28.2.tgz",
      "integrity": "sha512-48xSriZYYg+8qXna9kwqjIVzuQxi+KYWp2+5nCYnYKPTr0LvD89Jqk2Or5ogxz0NUMfIjhh2lIUX/LyX9B4oIg==",
      "dev": true,
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/browserslist"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/browserslist"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "dependencies": {
        "baseline-browser-mapping": "^2.10.12",
        "caniuse-lite": "^1.0.30001782",
        "electron-to-chromium": "^1.5.328",
        "node-releases": "^2.0.36",
        "update-browserslist-db": "^1.2.3"
      },
      "bin": {
        "browserslist": "cli.js"
      },
      "engines": {
        "node": "^6 || ^7 || ^8 || ^9 || ^10 || ^11 || ^12 || >=13.7"
      }
    },
    "node_modules/caniuse-lite": {
      "version": "1.0.30001787",
      "resolved": "https://registry.npmjs.org/caniuse-lite/-/caniuse-lite-1.0.30001787.tgz",
      "integrity": "sha512-mNcrMN9KeI68u7muanUpEejSLghOKlVhRqS/Za2IeyGllJ9I9otGpR9g3nsw7n4W378TE/LyIteA0+/FOZm4Kg==",
      "dev": true,
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/browserslist"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/caniuse-lite"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "CC-BY-4.0"
    },
    "node_modules/convert-source-map": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/convert-source-map/-/convert-source-map-2.0.0.tgz",
      "integrity": "sha512-Kvp459HrV2FEJ1CAsi1Ku+MY3kasH19TFykTz2xWmMeq6bk2NU3XXvfJ+Q61m0xktWwt+1HSYf3JZsTms3aRJg==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/csstype": {
      "version": "3.2.3",
      "resolved": "https://registry.npmjs.org/csstype/-/csstype-3.2.3.tgz",
      "integrity": "sha512-z1HGKcYy2xA8AGQfwrn0PAy+PB7X/GSj3UVJW9qKyn43xWa+gl5nXmU4qqLMRzWVLFC8KusUX8T/0kCiOYpAIQ==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/debug": {
      "version": "4.4.3",
      "resolved": "https://registry.npmjs.org/debug/-/debug-4.4.3.tgz",
      "integrity": "sha512-RGwwWnwQvkVfavKVt22FGLw+xYSdzARwm0ru6DhTVA3umU5hZc28V3kO4stgYryrTlLpuvgI9GiijltAjNbcqA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "ms": "^2.1.3"
      },
      "engines": {
        "node": ">=6.0"
      },
      "peerDependenciesMeta": {
        "supports-color": {
          "optional": true
        }
      }
    },
    "node_modules/electron-to-chromium": {
      "version": "1.5.334",
      "resolved": "https://registry.npmjs.org/electron-to-chromium/-/electron-to-chromium-1.5.334.tgz",
      "integrity": "sha512-mgjZAz7Jyx1SRCwEpy9wefDS7GvNPazLthHg8eQMJ76wBdGQQDW33TCrUTvQ4wzpmOrv2zrFoD3oNufMdyMpog==",
      "dev": true,
      "license": "ISC"
    },
    "node_modules/esbuild": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/esbuild/-/esbuild-0.21.5.tgz",
      "integrity": "sha512-mg3OPMV4hXywwpoDxu3Qda5xCKQi+vCTZq8S9J/EpkhB2HzKXq4SNFZE3+NK93JYxc8VMSep+lOUSC/RVKaBqw==",
      "dev": true,
      "hasInstallScript": true,
      "license": "MIT",
      "bin": {
        "esbuild": "bin/esbuild"
      },
      "engines": {
        "node": ">=12"
      },
      "optionalDependencies": {
        "@esbuild/aix-ppc64": "0.21.5",
        "@esbuild/android-arm": "0.21.5",
        "@esbuild/android-arm64": "0.21.5",
        "@esbuild/android-x64": "0.21.5",
        "@esbuild/darwin-arm64": "0.21.5",
        "@esbuild/darwin-x64": "0.21.5",
        "@esbuild/freebsd-arm64": "0.21.5",
        "@esbuild/freebsd-x64": "0.21.5",
        "@esbuild/linux-arm": "0.21.5",
        "@esbuild/linux-arm64": "0.21.5",
        "@esbuild/linux-ia32": "0.21.5",
        "@esbuild/linux-loong64": "0.21.5",
        "@esbuild/linux-mips64el": "0.21.5",
        "@esbuild/linux-ppc64": "0.21.5",
        "@esbuild/linux-riscv64": "0.21.5",
        "@esbuild/linux-s390x": "0.21.5",
        "@esbuild/linux-x64": "0.21.5",
        "@esbuild/netbsd-x64": "0.21.5",
        "@esbuild/openbsd-x64": "0.21.5",
        "@esbuild/sunos-x64": "0.21.5",
        "@esbuild/win32-arm64": "0.21.5",
        "@esbuild/win32-ia32": "0.21.5",
        "@esbuild/win32-x64": "0.21.5"
      }
    },
    "node_modules/escalade": {
      "version": "3.2.0",
      "resolved": "https://registry.npmjs.org/escalade/-/escalade-3.2.0.tgz",
      "integrity": "sha512-WUj2qlxaQtO4g6Pq5c29GTcWGDyd8itL8zTlipgECz3JesAiiOKotd8JU6otB3PACgG6xkJUyVhboMS+bje/jA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/fsevents": {
      "version": "2.3.3",
      "resolved": "https://registry.npmjs.org/fsevents/-/fsevents-2.3.3.tgz",
      "integrity": "sha512-5xoDfX+fL7faATnagmWPpbFtwh/R77WmMMqqHGS65C3vvB0YHrgF+B1YmZ3441tMj5n63k0212XNoJwzlhffQw==",
      "dev": true,
      "hasInstallScript": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ],
      "engines": {
        "node": "^8.16.0 || ^10.6.0 || >=11.0.0"
      }
    },
    "node_modules/gensync": {
      "version": "1.0.0-beta.2",
      "resolved": "https://registry.npmjs.org/gensync/-/gensync-1.0.0-beta.2.tgz",
      "integrity": "sha512-3hN7NaskYvMDLQY55gnW3NQ+mesEAepTqlg+VEbj7zzqEMBVNhzcGYYeqFo/TlYz6eQiFcp1HcsCZO+nGgS8zg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/js-tokens": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/js-tokens/-/js-tokens-4.0.0.tgz",
      "integrity": "sha512-RdJUflcE3cUzKiMqQgsCu06FPu9UdIJO0beYbPhHN4k6apgJtifcoCtT9bcxOpYBtpD2kCM6Sbzg4CausW/PKQ==",
      "license": "MIT"
    },
    "node_modules/jsesc": {
      "version": "3.1.0",
      "resolved": "https://registry.npmjs.org/jsesc/-/jsesc-3.1.0.tgz",
      "integrity": "sha512-/sM3dO2FOzXjKQhJuo0Q173wf2KOo8t4I8vHy6lF9poUp7bKT0/NHE8fPX23PwfhnykfqnC2xRxOnVw5XuGIaA==",
      "dev": true,
      "license": "MIT",
      "bin": {
        "jsesc": "bin/jsesc"
      },
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/json5": {
      "version": "2.2.3",
      "resolved": "https://registry.npmjs.org/json5/-/json5-2.2.3.tgz",
      "integrity": "sha512-XmOWe7eyHYH14cLdVPoyg+GOH3rYX++KpzrylJwSW98t3Nk+U8XOl8FWKOgwtzdb8lXGf6zYwDUzeHMWfxasyg==",
      "dev": true,
      "license": "MIT",
      "bin": {
        "json5": "lib/cli.js"
      },
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/loose-envify": {
      "version": "1.4.0",
      "resolved": "https://registry.npmjs.org/loose-envify/-/loose-envify-1.4.0.tgz",
      "integrity": "sha512-lyuxPGr/Wfhrlem2CL/UcnUc1zcqKAImBDzukY7Y5F/yQiNdko6+fRLevlw1HgMySw7f611UIY408EtxRSoK3Q==",
      "license": "MIT",
      "dependencies": {
        "js-tokens": "^3.0.0 || ^4.0.0"
      },
      "bin": {
        "loose-envify": "cli.js"
      }
    },
    "node_modules/lru-cache": {
      "version": "5.1.1",
      "resolved": "https://registry.npmjs.org/lru-cache/-/lru-cache-5.1.1.tgz",
      "integrity": "sha512-KpNARQA3Iwv+jTA0utUVVbrh+Jlrr1Fv0e56GGzAFOXN7dk/FviaDW8LHmK52DlcH4WP2n6gI8vN1aesBFgo9w==",
      "dev": true,
      "license": "ISC",
      "dependencies": {
        "yallist": "^3.0.2"
      }
    },
    "node_modules/ms": {
      "version": "2.1.3",
      "resolved": "https://registry.npmjs.org/ms/-/ms-2.1.3.tgz",
      "integrity": "sha512-6FlzubTLZG3J2a/NVCAleEhjzq5oxgHyaCU9yYXvcLsvoVaHJq/s5xXI6/XXP6tz7R9xAOtHnSO/tXtF3WRTlA==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/nanoid": {
      "version": "3.3.11",
      "resolved": "https://registry.npmjs.org/nanoid/-/nanoid-3.3.11.tgz",
      "integrity": "sha512-N8SpfPUnUp1bK+PMYW8qSWdl9U+wwNWI4QKxOYDy9JAro3WMX7p2OeVRF9v+347pnakNevPmiHhNmZ2HbFA76w==",
      "dev": true,
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "bin": {
        "nanoid": "bin/nanoid.cjs"
      },
      "engines": {
        "node": "^10 || ^12 || ^13.7 || ^14 || >=15.0.1"
      }
    },
    "node_modules/node-releases": {
      "version": "2.0.37",
      "resolved": "https://registry.npmjs.org/node-releases/-/node-releases-2.0.37.tgz",
      "integrity": "sha512-1h5gKZCF+pO/o3Iqt5Jp7wc9rH3eJJ0+nh/CIoiRwjRxde/hAHyLPXYN4V3CqKAbiZPSeJFSWHmJsbkicta0Eg==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/picocolors": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/picocolors/-/picocolors-1.1.1.tgz",
      "integrity": "sha512-xceH2snhtb5M9liqDsmEw56le376mTZkEX/jEb/RxNFyegNul7eNslCXP9FDj/Lcu0X8KEyMceP2ntpaHrDEVA==",
      "dev": true,
      "license": "ISC"
    },
    "node_modules/postcss": {
      "version": "8.5.9",
      "resolved": "https://registry.npmjs.org/postcss/-/postcss-8.5.9.tgz",
      "integrity": "sha512-7a70Nsot+EMX9fFU3064K/kdHWZqGVY+BADLyXc8Dfv+mTLLVl6JzJpPaCZ2kQL9gIJvKXSLMHhqdRRjwQeFtw==",
      "dev": true,
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/postcss/"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/postcss"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "dependencies": {
        "nanoid": "^3.3.11",
        "picocolors": "^1.1.1",
        "source-map-js": "^1.2.1"
      },
      "engines": {
        "node": "^10 || ^12 || >=14"
      }
    },
    "node_modules/react": {
      "version": "18.3.1",
      "resolved": "https://registry.npmjs.org/react/-/react-18.3.1.tgz",
      "integrity": "sha512-wS+hAgJShR0KhEvPJArfuPVN1+Hz1t0Y6n5jLrGQbkb4urgPE/0Rve+1kMB1v/oWgHgm4WIcV+i7F2pTVj+2iQ==",
      "license": "MIT",
      "dependencies": {
        "loose-envify": "^1.1.0"
      },
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/react-dom": {
      "version": "18.3.1",
      "resolved": "https://registry.npmjs.org/react-dom/-/react-dom-18.3.1.tgz",
      "integrity": "sha512-5m4nQKp+rZRb09LNH59GM4BxTh9251/ylbKIbpe7TpGxfJ+9kv6BLkLBXIjjspbgbnIBNqlI23tRnTWT0snUIw==",
      "license": "MIT",
      "dependencies": {
        "loose-envify": "^1.1.0",
        "scheduler": "^0.23.2"
      },
      "peerDependencies": {
        "react": "^18.3.1"
      }
    },
    "node_modules/react-refresh": {
      "version": "0.17.0",
      "resolved": "https://registry.npmjs.org/react-refresh/-/react-refresh-0.17.0.tgz",
      "integrity": "sha512-z6F7K9bV85EfseRCp2bzrpyQ0Gkw1uLoCel9XBVWPg/TjRj94SkJzUTGfOa4bs7iJvBWtQG0Wq7wnI0syw3EBQ==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/rollup": {
      "version": "4.60.1",
      "resolved": "https://registry.npmjs.org/rollup/-/rollup-4.60.1.tgz",
      "integrity": "sha512-VmtB2rFU/GroZ4oL8+ZqXgSA38O6GR8KSIvWmEFv63pQ0G6KaBH9s07PO8XTXP4vI+3UJUEypOfjkGfmSBBR0w==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@types/estree": "1.0.8"
      },
      "bin": {
        "rollup": "dist/bin/rollup"
      },
      "engines": {
        "node": ">=18.0.0",
        "npm": ">=8.0.0"
      },
      "optionalDependencies": {
        "@rollup/rollup-android-arm-eabi": "4.60.1",
        "@rollup/rollup-android-arm64": "4.60.1",
        "@rollup/rollup-darwin-arm64": "4.60.1",
        "@rollup/rollup-darwin-x64": "4.60.1",
        "@rollup/rollup-freebsd-arm64": "4.60.1",
        "@rollup/rollup-freebsd-x64": "4.60.1",
        "@rollup/rollup-linux-arm-gnueabihf": "4.60.1",
        "@rollup/rollup-linux-arm-musleabihf": "4.60.1",
        "@rollup/rollup-linux-arm64-gnu": "4.60.1",
        "@rollup/rollup-linux-arm64-musl": "4.60.1",
        "@rollup/rollup-linux-loong64-gnu": "4.60.1",
        "@rollup/rollup-linux-loong64-musl": "4.60.1",
        "@rollup/rollup-linux-ppc64-gnu": "4.60.1",
        "@rollup/rollup-linux-ppc64-musl": "4.60.1",
        "@rollup/rollup-linux-riscv64-gnu": "4.60.1",
        "@rollup/rollup-linux-riscv64-musl": "4.60.1",
        "@rollup/rollup-linux-s390x-gnu": "4.60.1",
        "@rollup/rollup-linux-x64-gnu": "4.60.1",
        "@rollup/rollup-linux-x64-musl": "4.60.1",
        "@rollup/rollup-openbsd-x64": "4.60.1",
        "@rollup/rollup-openharmony-arm64": "4.60.1",
        "@rollup/rollup-win32-arm64-msvc": "4.60.1",
        "@rollup/rollup-win32-ia32-msvc": "4.60.1",
        "@rollup/rollup-win32-x64-gnu": "4.60.1",
        "@rollup/rollup-win32-x64-msvc": "4.60.1",
        "fsevents": "~2.3.2"
      }
    },
    "node_modules/scheduler": {
      "version": "0.23.2",
      "resolved": "https://registry.npmjs.org/scheduler/-/scheduler-0.23.2.tgz",
      "integrity": "sha512-UOShsPwz7NrMUqhR6t0hWjFduvOzbtv7toDH1/hIrfRNIDBnnBWd0CwJTGvTpngVlmwGCdP9/Zl/tVrDqcuYzQ==",
      "license": "MIT",
      "dependencies": {
        "loose-envify": "^1.1.0"
      }
    },
    "node_modules/semver": {
      "version": "6.3.1",
      "resolved": "https://registry.npmjs.org/semver/-/semver-6.3.1.tgz",
      "integrity": "sha512-BR7VvDCVHO+q2xBEWskxS6DJE1qRnb7DxzUrogb71CWoSficBxYsiAGd+Kl0mmq/MprG9yArRkyrQxTO6XjMzA==",
      "dev": true,
      "license": "ISC",
      "bin": {
        "semver": "bin/semver.js"
      }
    },
    "node_modules/source-map-js": {
      "version": "1.2.1",
      "resolved": "https://registry.npmjs.org/source-map-js/-/source-map-js-1.2.1.tgz",
      "integrity": "sha512-UXWMKhLOwVKb728IUtQPXxfYU+usdybtUrK/8uGE8CQMvrhOpwvzDBwj0QhSL7MQc7vIsISBG8VQ8+IDQxpfQA==",
      "dev": true,
      "license": "BSD-3-Clause",
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/typescript": {
      "version": "5.9.3",
      "resolved": "https://registry.npmjs.org/typescript/-/typescript-5.9.3.tgz",
      "integrity": "sha512-jl1vZzPDinLr9eUt3J/t7V6FgNEw9QjvBPdysz9KfQDD41fQrC2Y4vKQdiaUpFT4bXlb1RHhLpp8wtm6M5TgSw==",
      "dev": true,
      "license": "Apache-2.0",
      "bin": {
        "tsc": "bin/tsc",
        "tsserver": "bin/tsserver"
      },
      "engines": {
        "node": ">=14.17"
      }
    },
    "node_modules/update-browserslist-db": {
      "version": "1.2.3",
      "resolved": "https://registry.npmjs.org/update-browserslist-db/-/update-browserslist-db-1.2.3.tgz",
      "integrity": "sha512-Js0m9cx+qOgDxo0eMiFGEueWztz+d4+M3rGlmKPT+T4IS/jP4ylw3Nwpu6cpTTP8R1MAC1kF4VbdLt3ARf209w==",
      "dev": true,
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/browserslist"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/browserslist"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "dependencies": {
        "escalade": "^3.2.0",
        "picocolors": "^1.1.1"
      },
      "bin": {
        "update-browserslist-db": "cli.js"
      },
      "peerDependencies": {
        "browserslist": ">= 4.21.0"
      }
    },
    "node_modules/vite": {
      "version": "5.4.21",
      "resolved": "https://registry.npmjs.org/vite/-/vite-5.4.21.tgz",
      "integrity": "sha512-o5a9xKjbtuhY6Bi5S3+HvbRERmouabWbyUcpXXUA1u+GNUKoROi9byOJ8M0nHbHYHkYICiMlqxkg1KkYmm25Sw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "esbuild": "^0.21.3",
        "postcss": "^8.4.43",
        "rollup": "^4.20.0"
      },
      "bin": {
        "vite": "bin/vite.js"
      },
      "engines": {
        "node": "^18.0.0 || >=20.0.0"
      },
      "funding": {
        "url": "https://github.com/vitejs/vite?sponsor=1"
      },
      "optionalDependencies": {
        "fsevents": "~2.3.3"
      },
      "peerDependencies": {
        "@types/node": "^18.0.0 || >=20.0.0",
        "less": "*",
        "lightningcss": "^1.21.0",
        "sass": "*",
        "sass-embedded": "*",
        "stylus": "*",
        "sugarss": "*",
        "terser": "^5.4.0"
      },
      "peerDependenciesMeta": {
        "@types/node": {
          "optional": true
        },
        "less": {
          "optional": true
        },
        "lightningcss": {
          "optional": true
        },
        "sass": {
          "optional": true
        },
        "sass-embedded": {
          "optional": true
        },
        "stylus": {
          "optional": true
        },
        "sugarss": {
          "optional": true
        },
        "terser": {
          "optional": true
        }
      }
    },
    "node_modules/yallist": {
      "version": "3.1.1",
      "resolved": "https://registry.npmjs.org/yallist/-/yallist-3.1.1.tgz",
      "integrity": "sha512-a4UGQaWPH59mOXUYnAG2ewncQS4i4F43Tv3JoAM+s2VDAmS9NsK8GpDMLrCHPksFT7h3K6TOoUNn2pb7RoXx4g==",
      "dev": true,
      "license": "ISC"
    }
  }
}
```

<!-- end of file: frontend/package-lock.json -->

## `frontend/tsconfig.json`

TypeScript: strict, ES2022, JSX react-jsx, bundler resolution for Vite.

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

<!-- end of file: frontend/tsconfig.json -->

## `frontend/vite.config.ts`

Vite + React plugin; dev server port 5173; proxy /api to 127.0.0.1:8000.

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
  build: {
    outDir: "dist",
    emptyDirOutDir: true,
  },
});
```

<!-- end of file: frontend/vite.config.ts -->

## `frontend/index.html`

HTML shell: title, viewport, font link, root div for React mount.

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="theme-color" content="#2563eb" />
    <title>Smart Pricing — Lodging</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

<!-- end of file: frontend/index.html -->

## `frontend/src/vite-env.d.ts`

Vite client types reference for import.meta and env.

```typescript
/// <reference types="vite/client" />
```

<!-- end of file: frontend/src/vite-env.d.ts -->

## `frontend/src/api.ts`

Fetch wrappers for /api/listings, pricing, host settings, simulation, admin. Note: backend may require Bearer token for admin/settings endpoints—extend headers when using secured APIs.

```typescript
const API = "";

export type ListingSummary = {
  id: string;
  name: string;
  neighbourhood: string;
  neighbourhood_group: string;
  room_type: string;
  price: number;
};

export type CalendarDay = {
  date: string;
  recommended_price: number | null;
  confidence: number;
  tags: string[];
  components: Record<string, number>;
  blocked?: boolean;
};

export async function fetchListings(): Promise<ListingSummary[]> {
  const r = await fetch(`${API}/api/listings`);
  if (!r.ok) throw new Error(await r.text());
  const j = await r.json();
  return j.listings as ListingSummary[];
}

export async function fetchPricing(listingId: string, days = 60): Promise<{
  listing: { id: string; name: string; neighbourhood_group: string; room_type: string };
  settings: Record<string, unknown>;
  suggested_try_price: number;
  kill_switch_active: boolean;
  calendar: CalendarDay[];
}> {
  const r = await fetch(`${API}/api/pricing/${listingId}?days=${days}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function saveHostSettings(
  listingId: string,
  body: Record<string, unknown>
): Promise<void> {
  const r = await fetch(`${API}/api/host/settings/${listingId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
}

export async function runSimulation(
  listingId: string,
  customPrice: number
): Promise<{
  booking_probability: number;
  expected_revenue: number;
  top_alternatives: { price: number; booking_probability: number; expected_revenue: number }[];
}> {
  const r = await fetch(`${API}/api/simulation/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ listing_id: listingId, custom_price: customPrice }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchAdmin(): Promise<{
  kill_switch: boolean;
  listings_loaded: number;
  recent_audit: { ts: string; action: string }[];
}> {
  const r = await fetch(`${API}/api/admin/status`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function setKillSwitch(enabled: boolean, region?: string): Promise<void> {
  const r = await fetch(`${API}/api/admin/kill-switch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled, region: region || null }),
  });
  if (!r.ok) throw new Error(await r.text());
}
```

<!-- end of file: frontend/src/api.ts -->

## `frontend/src/main.tsx`

React 18 createRoot, StrictMode, App + global CSS import.

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

<!-- end of file: frontend/src/main.tsx -->

## `frontend/src/styles.css`

Global layout, theme variables, calendar grid, forms, modal, responsive tweaks for Smart Pricing UI.

```css
:root {
  /* Blue & white theme */
  --bg: #f0f6fc;
  --bg-elevated: #ffffff;
  --bg-subtle: #e8f1fb;
  --border: #c7d8ec;
  --border-strong: #94b8e8;
  --text: #0f172a;
  --muted: #64748b;
  --blue-50: #eff6ff;
  --blue-100: #dbeafe;
  --blue-200: #bfdbfe;
  --blue-500: #3b82f6;
  --blue-600: #2563eb;
  --blue-700: #1d4ed8;
  --blue-800: #1e40af;
  --accent: var(--blue-600);
  --accent-soft: linear-gradient(135deg, #2563eb 0%, #3b82f6 50%, #60a5fa 100%);
  --danger: #dc2626;
  --ok: #16a34a;
  --warn-bg: #fff7ed;
  --warn-border: #fed7aa;
  --warn-text: #c2410c;
  --radius: 14px;
  --shadow: 0 4px 24px rgba(37, 99, 235, 0.08), 0 1px 3px rgba(15, 23, 42, 0.06);
  --shadow-card: 0 1px 0 rgba(255, 255, 255, 0.8) inset, var(--shadow);
  --font: "DM Sans", system-ui, -apple-system, sans-serif;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  font-family: var(--font);
  color: var(--text);
  background-color: var(--bg);
  background-image:
    radial-gradient(ellipse 900px 420px at 50% -20%, rgba(191, 219, 254, 0.65) 0%, transparent 55%),
    radial-gradient(ellipse 600px 300px at 100% 50%, rgba(219, 234, 254, 0.5) 0%, transparent 45%),
    linear-gradient(180deg, #f8fafc 0%, var(--bg) 40%, #eef4fb 100%);
}

a {
  color: var(--blue-700);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

.app-shell {
  max-width: 1180px;
  margin: 0 auto;
  padding: 28px 20px 56px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 28px;
  padding: 20px 22px;
  background: var(--bg-elevated);
  border-radius: var(--radius);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
}

.brand {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.brand h1 {
  margin: 0;
  font-size: 1.4rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--blue-800);
}

.brand span {
  color: var(--muted);
  font-size: 0.9rem;
  font-weight: 500;
}

.tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tabs button {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  color: var(--muted);
  padding: 10px 18px;
  border-radius: 999px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.88rem;
  transition: color 0.15s ease, border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
}

.tabs button:hover {
  border-color: var(--blue-200);
  color: var(--blue-700);
  background: var(--blue-50);
}

.tabs button.active {
  background: var(--accent-soft);
  border-color: transparent;
  color: #ffffff;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
}

.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
}

@media (min-width: 960px) {
  .grid.host {
    grid-template-columns: 380px 1fr;
    align-items: start;
  }
}

.card {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 22px 22px;
  box-shadow: var(--shadow-card);
}

.card h2 {
  margin: 0 0 14px;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--blue-800);
}

label {
  display: block;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--muted);
  font-weight: 600;
  margin-bottom: 7px;
}

input,
select,
textarea {
  width: 100%;
  padding: 11px 14px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: #ffffff;
  color: var(--text);
  font: inherit;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

input:hover,
select:hover,
textarea:hover {
  border-color: var(--blue-200);
}

input:focus,
select:focus,
textarea:focus {
  outline: none;
  border-color: var(--blue-500);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

textarea {
  min-height: 76px;
  resize: vertical;
}

.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}

.switch-row:last-child {
  border-bottom: none;
}

.switch-row strong {
  color: var(--text);
  font-weight: 600;
}

.switch {
  width: 50px;
  height: 28px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: #e2e8f0;
  position: relative;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.18s ease, border-color 0.18s ease;
}

.switch.on {
  background: var(--blue-600);
  border-color: var(--blue-600);
}

.switch::after {
  content: "";
  position: absolute;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #ffffff;
  top: 2px;
  left: 3px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.2);
  transition: transform 0.18s ease;
}

.switch.on::after {
  transform: translateX(22px);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 11px 18px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--blue-800);
  font-weight: 600;
  cursor: pointer;
  font: inherit;
  transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}

.btn:hover:not(:disabled) {
  background: var(--blue-50);
  border-color: var(--blue-200);
}

.btn.primary {
  background: var(--accent-soft);
  border-color: transparent;
  color: #ffffff;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.35);
}

.btn.primary:hover:not(:disabled) {
  filter: brightness(1.03);
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.hint {
  font-size: 0.86rem;
  color: var(--muted);
  margin-top: 8px;
  line-height: 1.45;
}

.badge {
  display: inline-block;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 600;
  background: var(--blue-50);
  border: 1px solid var(--blue-200);
  color: var(--blue-800);
}

.badge.warn {
  background: var(--warn-bg);
  border-color: var(--warn-border);
  color: var(--warn-text);
}

.calendar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 8px;
}

.dow {
  font-size: 0.72rem;
  color: var(--muted);
  font-weight: 600;
  text-align: center;
  padding: 6px 0;
}

.day-cell {
  min-height: 76px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: #ffffff;
  padding: 7px 9px;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.12s ease;
  text-align: left;
  font: inherit;
  color: inherit;
}

.day-cell:hover:not(:disabled):not(.blackout) {
  border-color: var(--blue-500);
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.12);
  transform: translateY(-1px);
}

.day-cell:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.day-cell.blackout {
  background: var(--bg-subtle);
  cursor: default;
}

.day-num {
  font-size: 0.72rem;
  color: var(--muted);
  font-weight: 600;
}

.day-price {
  font-weight: 700;
  font-size: 0.95rem;
  margin-top: 4px;
  color: var(--blue-800);
}

.day-meta {
  font-size: 0.66rem;
  color: var(--muted);
  margin-top: 4px;
  line-height: 1.25;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 50;
}

.modal {
  width: min(520px, 100%);
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 22px 24px;
  max-height: 90vh;
  overflow: auto;
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.12);
}

.modal h3 {
  margin: 0 0 10px;
  color: var(--blue-800);
}

.modal h4 {
  color: var(--blue-800);
}

.kv {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px 16px;
  font-size: 0.9rem;
}

.kv div:nth-child(odd) {
  color: var(--muted);
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 14px;
}

.stat {
  padding: 16px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: linear-gradient(180deg, #ffffff 0%, var(--blue-50) 100%);
}

.stat .v {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--blue-800);
}

.stat .k {
  color: var(--muted);
  font-size: 0.82rem;
  margin-top: 6px;
  font-weight: 500;
}

.err {
  color: var(--danger);
  font-size: 0.9rem;
  margin-top: 10px;
  padding: 12px 14px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 10px;
}

/* Tables in simulation */
.card table {
  border-collapse: collapse;
  width: 100%;
}

.card thead tr {
  border-bottom: 1px solid var(--border);
}

.card td,
.card th {
  padding: 10px 8px;
}

.card tbody tr:hover {
  background: var(--blue-50);
}
```

<!-- end of file: frontend/src/styles.css -->

## `frontend/src/App.tsx`

Main UI: tabs Host / Simulation / Admin; listing picker; host min/max/base/goals; 60-day calendar with modal; simulation results; admin kill switch and audit (API calls must align with backend auth when enabled).

```tsx
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CalendarDay,
  fetchAdmin,
  fetchListings,
  fetchPricing,
  ListingSummary,
  runSimulation,
  saveHostSettings,
  setKillSwitch,
} from "./api";

type Tab = "host" | "sim" | "admin";

function formatMoney(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

export default function App() {
  const [tab, setTab] = useState<Tab>("host");
  const [listings, setListings] = useState<ListingSummary[]>([]);
  const [listingId, setListingId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [smartOn, setSmartOn] = useState(true);
  const [minP, setMinP] = useState<number>(80);
  const [maxP, setMaxP] = useState<number>(400);
  const [baseP, setBaseP] = useState<number | "">("");
  const [goal, setGoal] = useState("balanced");
  const [risk, setRisk] = useState("medium");
  const [freq, setFreq] = useState("daily");
  const [discountFloor, setDiscountFloor] = useState(true);
  const [lockedDates, setLockedDates] = useState("");
  const [blackoutDates, setBlackoutDates] = useState("");

  const [suggested, setSuggested] = useState<number | null>(null);
  const [killActive, setKillActive] = useState(false);
  const [calendar, setCalendar] = useState<CalendarDay[]>([]);
  const [listingName, setListingName] = useState("");

  const [modalDay, setModalDay] = useState<CalendarDay | null>(null);

  const [simPrice, setSimPrice] = useState<number>(200);
  const [simResult, setSimResult] = useState<{
    booking_probability: number;
    expected_revenue: number;
    top_alternatives: { price: number; booking_probability: number; expected_revenue: number }[];
  } | null>(null);

  const [admin, setAdmin] = useState<{
    kill_switch: boolean;
    listings_loaded: number;
    recent_audit: { ts: string; action: string }[];
  } | null>(null);

  const loadListings = useCallback(async () => {
    setErr(null);
    const items = await fetchListings();
    setListings(items);
    setListingId((prev) => prev || (items.length ? items[0].id : ""));
  }, []);

  const loadPricing = useCallback(async () => {
    if (!listingId) return;
    setLoading(true);
    setErr(null);
    try {
      const d = await fetchPricing(listingId, 60);
      setListingName(d.listing.name);
      setSuggested(d.suggested_try_price);
      setKillActive(d.kill_switch_active);
      setCalendar(d.calendar);
      const s = d.settings as Record<string, unknown>;
      setSmartOn(Boolean(s.smart_pricing_enabled ?? true));
      setMinP(Number(s.min_price ?? 80));
      setMaxP(Number(s.max_price ?? 400));
      setBaseP(s.base_price != null ? Number(s.base_price) : "");
      setGoal(String(s.pricing_goal ?? "balanced"));
      setRisk(String(s.risk_tolerance ?? "medium"));
      setFreq(String(s.update_frequency ?? "daily"));
      setDiscountFloor(Boolean(s.discount_floor_protection ?? true));
      setLockedDates(Array.isArray(s.locked_dates) ? (s.locked_dates as string[]).join(", ") : "");
      setBlackoutDates(Array.isArray(s.blackout_dates) ? (s.blackout_dates as string[]).join(", ") : "");
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }, [listingId]);

  useEffect(() => {
    loadListings().catch((e) => setErr(String(e)));
  }, []);

  useEffect(() => {
    if (listingId) loadPricing().catch((e) => setErr(String(e)));
  }, [listingId, loadPricing]);

  const parseDateList = (s: string) =>
    s
      .split(/[,;\s]+/)
      .map((x) => x.trim())
      .filter(Boolean);

  const onSaveSettings = async () => {
    if (!listingId) return;
    if (smartOn && maxP <= minP) {
      setErr("Max price must be greater than min price.");
      return;
    }
    setErr(null);
    setLoading(true);
    try {
      await saveHostSettings(listingId, {
        smart_pricing_enabled: smartOn,
        min_price: minP,
        max_price: maxP,
        base_price: baseP === "" ? null : baseP,
        pricing_goal: goal,
        risk_tolerance: risk,
        update_frequency: freq,
        discount_floor_protection: discountFloor,
        locked_dates: parseDateList(lockedDates),
        blackout_dates: parseDateList(blackoutDates),
      });
      await loadPricing();
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  };

  const onSim = async () => {
    if (!listingId) return;
    setErr(null);
    setLoading(true);
    try {
      const r = await runSimulation(listingId, simPrice);
      setSimResult(r);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  };

  const onLoadAdmin = async () => {
    setErr(null);
    try {
      const a = await fetchAdmin();
      setAdmin(a);
    } catch (e) {
      setErr(String(e));
    }
  };

  useEffect(() => {
    if (tab === "admin") onLoadAdmin().catch((e) => setErr(String(e)));
  }, [tab]);

  const weekRows = useMemo(() => {
    const rows: CalendarDay[][] = [];
    if (!calendar.length) return rows;
    let row: CalendarDay[] = [];
    const first = new Date(calendar[0].date + "T12:00:00");
    const pad = first.getDay();
    for (let i = 0; i < pad; i++) row.push({ date: "", recommended_price: null, confidence: 0, tags: [], components: {}, blocked: true } as CalendarDay);
    calendar.forEach((d) => {
      row.push(d);
      if (row.length === 7) {
        rows.push(row);
        row = [];
      }
    });
    if (row.length) {
      while (row.length < 7) row.push({ date: "", recommended_price: null, confidence: 0, tags: [], components: {}, blocked: true } as CalendarDay);
      rows.push(row);
    }
    return rows;
  }, [calendar]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <h1>Smart Pricing</h1>
          <span>Lodging nightly rates · guardrails · explainability</span>
        </div>
        <nav className="tabs" aria-label="Primary">
          <button type="button" className={tab === "host" ? "active" : ""} onClick={() => setTab("host")}>
            Host
          </button>
          <button type="button" className={tab === "sim" ? "active" : ""} onClick={() => setTab("sim")}>
            Simulation
          </button>
          <button type="button" className={tab === "admin" ? "active" : ""} onClick={() => setTab("admin")}>
            Admin
          </button>
        </nav>
      </header>

      {err && <div className="err">{err}</div>}

      {tab === "host" && (
        <div className="grid host">
          <div className="card">
            <h2>Listing</h2>
            <label htmlFor="listing">Select listing</label>
            <select
              id="listing"
              value={listingId}
              onChange={(e) => setListingId(e.target.value)}
              disabled={loading}
            >
              {listings.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name.slice(0, 50)} — {l.neighbourhood}
                </option>
              ))}
            </select>
            <p className="hint">{listingName}</p>

            <div className="switch-row" style={{ marginTop: 16 }}>
              <div>
                <strong>Smart Pricing</strong>
                <div className="hint">Requires min/max when enabled</div>
              </div>
              <button
                type="button"
                className={`switch ${smartOn ? "on" : ""}`}
                aria-pressed={smartOn}
                onClick={() => setSmartOn(!smartOn)}
              />
            </div>

            <div className="row2" style={{ marginTop: 12 }}>
              <div>
                <label>Min price</label>
                <input type="number" value={minP} onChange={(e) => setMinP(Number(e.target.value))} disabled={!smartOn} />
              </div>
              <div>
                <label>Max price</label>
                <input type="number" value={maxP} onChange={(e) => setMaxP(Number(e.target.value))} disabled={!smartOn} />
              </div>
            </div>

            <div style={{ marginTop: 12 }}>
              <label>Base price (optional anchor)</label>
              <input
                type="number"
                value={baseP === "" ? "" : baseP}
                placeholder="e.g. 250"
                onChange={(e) => setBaseP(e.target.value === "" ? "" : Number(e.target.value))}
              />
            </div>

            {suggested != null && (
              <p className="hint">
                Suggested try: <strong>{formatMoney(suggested)}</strong>
              </p>
            )}

            {killActive && <span className="badge warn">Kill switch active — prices frozen</span>}

            <h2 style={{ marginTop: 20 }}>Preferences</h2>
            <div className="row2">
              <div>
                <label>Pricing goal</label>
                <select value={goal} onChange={(e) => setGoal(e.target.value)}>
                  <option value="revenue">Revenue</option>
                  <option value="occupancy">Occupancy</option>
                  <option value="balanced">Balanced</option>
                </select>
              </div>
              <div>
                <label>Risk tolerance</label>
                <select value={risk} onChange={(e) => setRisk(e.target.value)}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
            </div>
            <div style={{ marginTop: 12 }}>
              <label>Update frequency</label>
              <select value={freq} onChange={(e) => setFreq(e.target.value)}>
                <option value="hourly">Hourly</option>
                <option value="daily">Daily</option>
                <option value="event_driven">Event-driven</option>
              </select>
            </div>

            <div className="switch-row">
              <div>
                <strong>Discount floor protection</strong>
                <div className="hint">Prevent promos below min unless allowed</div>
              </div>
              <button
                type="button"
                className={`switch ${discountFloor ? "on" : ""}`}
                aria-pressed={discountFloor}
                onClick={() => setDiscountFloor(!discountFloor)}
              />
            </div>

            <div style={{ marginTop: 12 }}>
              <label>Locked dates (YYYY-MM-DD, comma-separated)</label>
              <textarea value={lockedDates} onChange={(e) => setLockedDates(e.target.value)} placeholder="2026-04-01, 2026-04-02" />
            </div>
            <div style={{ marginTop: 12 }}>
              <label>Blackout dates</label>
              <textarea value={blackoutDates} onChange={(e) => setBlackoutDates(e.target.value)} placeholder="2026-12-24" />
            </div>

            <button type="button" className="btn primary" style={{ marginTop: 16, width: "100%" }} onClick={onSaveSettings} disabled={loading || (smartOn && maxP <= minP)}>
              Save & refresh preview
            </button>
          </div>

          <div className="card">
            <div className="calendar-head">
              <h2 style={{ margin: 0 }}>Price preview (60 days)</h2>
              <span className="badge">Click a day for breakdown</span>
            </div>
            <div className="calendar-grid" style={{ marginBottom: 8 }}>
              {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
                <div key={d} className="dow">
                  {d}
                </div>
              ))}
            </div>
            {weekRows.map((wr, ri) => (
              <div key={ri} className="calendar-grid" style={{ marginBottom: 6 }}>
                {wr.map((cell, ci) => {
                  if (!cell.date) return <div key={ci} className="day-cell" style={{ visibility: "hidden" }} />;
                  const blocked = cell.blocked;
                  const d = new Date(cell.date + "T12:00:00");
                  return (
                    <button
                      type="button"
                      key={cell.date}
                      className={`day-cell ${blocked ? "blackout" : ""}`}
                      onClick={() => !blocked && cell.recommended_price != null && setModalDay(cell)}
                      disabled={blocked || cell.recommended_price == null}
                    >
                      <div className="day-num">{d.getDate()}</div>
                      {blocked ? (
                        <div className="day-price" style={{ fontSize: "0.8rem" }}>
                          —
                        </div>
                      ) : (
                        <>
                          <div className="day-price">{formatMoney(cell.recommended_price!)}</div>
                          <div className="day-meta">{(cell.confidence * 100).toFixed(0)}% conf</div>
                          <div className="day-meta">{cell.tags.slice(0, 2).join(" · ")}</div>
                        </>
                      )}
                    </button>
                  );
                })}
              </div>
            ))}
            {!calendar.length && <p className="hint">Loading calendar…</p>}
          </div>
        </div>
      )}

      {tab === "sim" && (
        <div className="card" style={{ maxWidth: 640 }}>
          <h2>Simulation (Jira Epic 5)</h2>
          <p className="hint">POST /api/simulation/run — custom price vs booking probability & expected revenue</p>
          <div className="row2">
            <div>
              <label>Listing</label>
              <select value={listingId} onChange={(e) => setListingId(e.target.value)}>
                {listings.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.id}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label>Custom price ($)</label>
              <input type="number" value={simPrice} onChange={(e) => setSimPrice(Number(e.target.value))} />
            </div>
          </div>
          <button type="button" className="btn primary" style={{ marginTop: 14 }} onClick={onSim} disabled={loading || !listingId}>
            Run simulation
          </button>
          {simResult && (
            <div style={{ marginTop: 20 }}>
              <div className="stat-grid">
                <div className="stat">
                  <div className="v">{(simResult.booking_probability * 100).toFixed(1)}%</div>
                  <div className="k">Booking probability</div>
                </div>
                <div className="stat">
                  <div className="v">{formatMoney(simResult.expected_revenue)}</div>
                  <div className="k">Expected revenue</div>
                </div>
              </div>
              <h3 style={{ marginTop: 20, fontSize: "1rem" }}>Top alternatives</h3>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
                <thead>
                  <tr style={{ color: "var(--muted)", textAlign: "left" }}>
                    <th style={{ padding: "8px 0" }}>Price</th>
                    <th>P( book )</th>
                    <th>E[ revenue ]</th>
                  </tr>
                </thead>
                <tbody>
                  {simResult.top_alternatives.map((a) => (
                    <tr key={a.price}>
                      <td style={{ padding: "6px 0" }}>{formatMoney(a.price)}</td>
                      <td>{(a.booking_probability * 100).toFixed(1)}%</td>
                      <td>{formatMoney(a.expected_revenue)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === "admin" && (
        <div className="grid">
          <div className="card">
            <h2>Admin & observability (Epic 7)</h2>
            <p className="hint">Kill switch + audit trail (demo)</p>
            <div className="stat-grid" style={{ marginTop: 12 }}>
              <div className="stat">
                <div className="v">{admin?.listings_loaded ?? "—"}</div>
                <div className="k">Listings in dataset</div>
              </div>
              <div className="stat">
                <div className="v">{admin?.kill_switch ? "ON" : "OFF"}</div>
                <div className="k">Kill switch</div>
              </div>
            </div>
            <div style={{ marginTop: 16, display: "flex", gap: 12, flexWrap: "wrap" }}>
              <button
                type="button"
                className="btn"
                onClick={async () => {
                  await setKillSwitch(true);
                  await onLoadAdmin();
                  await loadPricing();
                }}
              >
                Enable kill switch
              </button>
              <button
                type="button"
                className="btn primary"
                onClick={async () => {
                  await setKillSwitch(false);
                  await onLoadAdmin();
                  await loadPricing();
                }}
              >
                Disable kill switch
              </button>
            </div>
          </div>
          <div className="card">
            <h2>Recent audit</h2>
            <ul style={{ margin: 0, paddingLeft: 18, color: "var(--muted)", fontSize: "0.9rem" }}>
              {(admin?.recent_audit ?? []).slice().reverse().map((a, i) => (
                <li key={i} style={{ marginBottom: 6 }}>
                  {a.ts} — {a.action}
                </li>
              ))}
            </ul>
            {!admin?.recent_audit?.length && <p className="hint">No events yet</p>}
          </div>
        </div>
      )}

      {modalDay && (
        <div className="modal-backdrop" role="dialog" aria-modal onClick={() => setModalDay(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{modalDay.date}</h3>
            <p>
              <strong>{modalDay.recommended_price != null ? formatMoney(modalDay.recommended_price) : "—"}</strong> · Confidence{" "}
              {(modalDay.confidence * 100).toFixed(0)}%
            </p>
            <p className="hint">Tags: {modalDay.tags.join(", ")}</p>
            <h4 style={{ margin: "16px 0 8px" }}>Price components</h4>
            <div className="kv">
              {Object.entries(modalDay.components).map(([k, v]) => (
                <div key={k}>
                  <div>{k}</div>
                  <div>{typeof v === "number" ? v.toFixed(4) : String(v)}</div>
                </div>
              ))}
            </div>
            <button type="button" className="btn" style={{ marginTop: 16 }} onClick={() => setModalDay(null)}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
```

<!-- end of file: frontend/src/App.tsx -->


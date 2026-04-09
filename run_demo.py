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

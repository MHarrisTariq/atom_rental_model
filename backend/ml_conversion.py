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


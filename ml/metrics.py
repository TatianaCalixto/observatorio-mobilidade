"""Métricas de avaliação compartilhadas (MAE / RMSE)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error


def avaliar(y_true: Sequence[float], y_pred: Sequence[float]) -> dict[str, float]:
    """Retorna MAE e RMSE como floats."""
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
    }

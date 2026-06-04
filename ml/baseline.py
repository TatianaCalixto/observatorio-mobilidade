"""Baseline honesto: prevê a demanda pela média histórica da linha.

Referência simples e reprodutível para comparar com o modelo principal (XGBoost). Não usa
clima — por isso o modelo principal deve superá-lo ao capturar o efeito do clima.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from ml.features import TARGET


class MediaPorLinhaBaseline:
    """Prediz, para cada linha, a média do alvo observada no treino (fallback: média global)."""

    def __init__(self) -> None:
        self.media_por_linha: dict[str, float] = {}
        self.media_global: float = 0.0

    def fit(self, treino: pl.DataFrame) -> MediaPorLinhaBaseline:
        self.media_global = float(treino[TARGET].mean())
        agg = treino.group_by("route_id").agg(pl.col(TARGET).mean().alias("media"))
        self.media_por_linha = dict(
            zip(agg["route_id"].to_list(), agg["media"].to_list(), strict=True)
        )
        return self

    def predict(self, df: pl.DataFrame) -> np.ndarray:
        return np.array(
            [self.media_por_linha.get(r, self.media_global) for r in df["route_id"].to_list()],
            dtype=float,
        )

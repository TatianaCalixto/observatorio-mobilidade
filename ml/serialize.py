"""Serialização do modelo selecionado (XGBoost) para consumo pelo app.

Salva um artefato joblib com o modelo, a ordem das features (pré-processamento) e
metadados (versão, métricas da validação temporal, data, seed). O metadado
``target_is_simulated=True`` sinaliza que o alvo é SIMULADO (DEC-007) — o app deve
exibir isso.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import joblib
import numpy as np
import polars as pl

from ml.features import FEATURE_COLUMNS, SEED_PADRAO, TARGET, build_dataset, temporal_split
from ml.metrics import avaliar
from ml.train import XGB_PARAMS

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "ml" / "artifacts" / "modelo_demanda.joblib"
ARTIFACT_VERSION = "1.0"


def treinar_modelo_final(
    con: duckdb.DuckDBPyConnection, *, seed: int = SEED_PADRAO
) -> tuple[Any, dict[str, float]]:
    """Treina o XGBoost no treino e avalia na validação temporal. Retorna (modelo, métricas)."""
    from xgboost import XGBRegressor

    df = build_dataset(con, seed=seed)
    treino, validacao = temporal_split(df)
    modelo = XGBRegressor(random_state=seed, **XGB_PARAMS)
    modelo.fit(treino.select(FEATURE_COLUMNS).to_numpy(), treino[TARGET].to_numpy())
    metricas = avaliar(
        validacao[TARGET].to_numpy(), modelo.predict(validacao.select(FEATURE_COLUMNS).to_numpy())
    )
    return modelo, metricas


def salvar_modelo(
    modelo: Any,
    metricas: dict[str, float],
    caminho: str | Path = DEFAULT_MODEL_PATH,
    *,
    seed: int = SEED_PADRAO,
) -> Path:
    """Persiste o artefato (modelo + features + metadados) em joblib."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    artefato = {
        "model": modelo,
        "feature_columns": FEATURE_COLUMNS,
        "target": TARGET,
        "metadata": {
            "version": ARTIFACT_VERSION,
            "model_type": "xgboost",
            "trained_at": datetime.now(UTC).strftime("%Y-%m-%d"),
            "metrics": metricas,
            "seed": seed,
            "target_is_simulated": True,
        },
    }
    joblib.dump(artefato, caminho)
    return caminho


def carregar_modelo(caminho: str | Path = DEFAULT_MODEL_PATH) -> dict[str, Any]:
    """Carrega o artefato joblib (modelo + features + metadados)."""
    return joblib.load(caminho)


def prever(artefato: dict[str, Any], features: pl.DataFrame | dict[str, float]) -> np.ndarray:
    """Prevê a demanda a partir do artefato e de features (DataFrame ou dict de 1 amostra)."""
    cols = artefato["feature_columns"]
    if isinstance(features, dict):
        x = np.array([[float(features[c]) for c in cols]], dtype=float)
    else:
        x = features.select(cols).to_numpy()
    return artefato["model"].predict(x)


def main() -> None:
    from ingestion.config import load_settings
    from ml.train import treinar

    settings = load_settings()
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    try:
        treinar(con)  # registra runs no MLflow (baseline + xgboost)
        modelo, metricas = treinar_modelo_final(con)
    finally:
        con.close()
    caminho = salvar_modelo(modelo, metricas)
    print(f"Modelo salvo em {caminho} | métricas: {metricas}")


if __name__ == "__main__":
    main()

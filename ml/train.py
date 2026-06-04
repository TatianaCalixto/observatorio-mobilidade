"""Pipeline de treino: baseline × XGBoost com tracking no MLflow e seleção do melhor.

Cada execução registra dois runs no MLflow (tracking local em ``mlruns/`` por padrão):
o baseline e o XGBoost, ambos avaliados no mesmo split temporal. O melhor (menor RMSE na
validação) é identificado. Determinístico por seed.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import duckdb

# MLflow 3.x colocou o file store (mlruns/) em modo de manutenção; opt-in explícito
# para mantê-lo como tracking local conforme o escopo do projeto.
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

from ml.baseline import MediaPorLinhaBaseline
from ml.features import FEATURE_COLUMNS, SEED_PADRAO, TARGET, build_dataset, temporal_split
from ml.metrics import avaliar

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACKING_URI = (PROJECT_ROOT / "mlruns").as_uri()
EXPERIMENT_NAME = "observatorio_mobilidade"

#: Hiperparâmetros do XGBoost (fixos para reprodutibilidade).
XGB_PARAMS = {
    "n_estimators": 200,
    "max_depth": 6,
    "learning_rate": 0.1,
    "subsample": 0.9,
    "n_jobs": 2,
}


def treinar(
    con: duckdb.DuckDBPyConnection,
    *,
    seed: int = SEED_PADRAO,
    tracking_uri: str | None = None,
    experiment_name: str = EXPERIMENT_NAME,
) -> dict:
    """Treina baseline e XGBoost, registra no MLflow e retorna métricas + o melhor.

    Returns:
        ``{"baseline": {...}, "xgboost": {...}, "melhor": "xgboost"|"baseline"}``.
    """
    import mlflow
    from xgboost import XGBRegressor

    mlflow.set_tracking_uri(tracking_uri or DEFAULT_TRACKING_URI)
    mlflow.set_experiment(experiment_name)

    df = build_dataset(con, seed=seed)
    treino, validacao = temporal_split(df)
    x_treino = treino.select(FEATURE_COLUMNS).to_numpy()
    y_treino = treino[TARGET].to_numpy()
    x_valid = validacao.select(FEATURE_COLUMNS).to_numpy()
    y_valid = validacao[TARGET].to_numpy()

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    resultados: dict = {}

    # --- Baseline ---
    with mlflow.start_run(run_name=f"baseline-{stamp}") as run:
        base = MediaPorLinhaBaseline().fit(treino)
        metricas = avaliar(y_valid, base.predict(validacao))
        mlflow.log_param("model", "baseline_media_por_linha")
        mlflow.log_param("seed", seed)
        mlflow.log_param("n_treino", treino.height)
        mlflow.log_param("n_validacao", validacao.height)
        mlflow.log_metrics(metricas)
        resultados["baseline"] = {**metricas, "run_id": run.info.run_id}

    # --- XGBoost ---
    with mlflow.start_run(run_name=f"xgboost-{stamp}") as run:
        modelo = XGBRegressor(random_state=seed, **XGB_PARAMS)
        modelo.fit(x_treino, y_treino)
        metricas = avaliar(y_valid, modelo.predict(x_valid))
        mlflow.log_param("model", "xgboost")
        mlflow.log_param("seed", seed)
        mlflow.log_params(XGB_PARAMS)
        mlflow.log_metrics(metricas)
        importancias = dict(zip(FEATURE_COLUMNS, modelo.feature_importances_.tolist(), strict=True))
        mlflow.log_dict(importancias, "feature_importances.json")
        mlflow.xgboost.log_model(modelo, name="model")
        resultados["xgboost"] = {**metricas, "run_id": run.info.run_id}

    resultados["melhor"] = (
        "xgboost" if resultados["xgboost"]["rmse"] <= resultados["baseline"]["rmse"] else "baseline"
    )
    return resultados


def main() -> None:
    from ingestion.config import load_settings

    settings = load_settings()
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    try:
        resultados = treinar(con)
    finally:
        con.close()
    print("Resultados (validação temporal):")
    for nome in ("baseline", "xgboost"):
        m = resultados[nome]
        print(f"  {nome:>8}: MAE={m['mae']:.2f} RMSE={m['rmse']:.2f}")
    print(f"  Melhor: {resultados['melhor']}")


if __name__ == "__main__":
    main()

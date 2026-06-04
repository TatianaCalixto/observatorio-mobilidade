"""Testes do pipeline de treino (ml.train): tracking MLflow + comparação baseline×XGBoost."""

from pathlib import Path

from mlflow.tracking import MlflowClient

from ml.train import EXPERIMENT_NAME, treinar


def test_treino_registra_runs_no_mlflow(ml_con, tmp_path: Path):
    uri = (tmp_path / "mlruns").as_uri()
    treinar(ml_con, tracking_uri=uri)

    client = MlflowClient(tracking_uri=uri)
    exp = client.get_experiment_by_name(EXPERIMENT_NAME)
    assert exp is not None
    runs = client.search_runs([exp.experiment_id])
    assert len(runs) >= 2  # baseline + xgboost
    for run in runs:
        assert "mae" in run.data.metrics
        assert "rmse" in run.data.metrics


def test_pipeline_produz_metricas_e_comparacao(ml_con, tmp_path: Path):
    uri = (tmp_path / "mlruns").as_uri()
    resultados = treinar(ml_con, tracking_uri=uri)

    assert set(resultados) >= {"baseline", "xgboost", "melhor"}
    for nome in ("baseline", "xgboost"):
        assert resultados[nome]["mae"] > 0
        assert resultados[nome]["rmse"] > 0
    # XGBoost usa o clima; deve superar o baseline (média por linha) na fixture.
    assert resultados["xgboost"]["rmse"] <= resultados["baseline"]["rmse"]
    assert resultados["melhor"] == "xgboost"

"""Testes do baseline (ml.baseline) na validação temporal."""

from ml.baseline import MediaPorLinhaBaseline
from ml.features import TARGET, build_dataset, temporal_split
from ml.metrics import avaliar


def _metricas_baseline(con):
    df = build_dataset(con, seed=42)
    treino, validacao = temporal_split(df)
    base = MediaPorLinhaBaseline().fit(treino)
    pred = base.predict(validacao)
    return avaliar(validacao[TARGET].to_numpy(), pred), df


def test_baseline_metricas_em_faixa(ml_con):
    metricas, df = _metricas_baseline(ml_con)
    assert metricas["mae"] > 0
    assert metricas["rmse"] >= metricas["mae"]  # RMSE >= MAE sempre
    # Sanidade: erro bem abaixo do nível médio do alvo.
    assert metricas["mae"] < float(df[TARGET].mean())


def test_baseline_reprodutivel(ml_con):
    primeira, _ = _metricas_baseline(ml_con)
    segunda, _ = _metricas_baseline(ml_con)
    assert primeira == segunda

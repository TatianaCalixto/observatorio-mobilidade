"""Testes da serialização do modelo (ml.serialize)."""

from pathlib import Path

from ml.features import FEATURE_COLUMNS, TARGET, build_dataset, temporal_split
from ml.metrics import avaliar
from ml.serialize import carregar_modelo, prever, salvar_modelo, treinar_modelo_final


def test_serializa_recarrega_e_preve_estavel(ml_con, tmp_path: Path):
    modelo, metricas = treinar_modelo_final(ml_con)
    caminho = salvar_modelo(modelo, metricas, tmp_path / "modelo.joblib")
    assert caminho.exists()

    artefato = carregar_modelo(caminho)
    assert artefato["feature_columns"] == FEATURE_COLUMNS
    assert artefato["target"] == TARGET
    assert artefato["metadata"]["target_is_simulated"] is True
    assert artefato["metadata"]["metrics"] == metricas

    amostra = dict.fromkeys(FEATURE_COLUMNS, 1.0)
    amostra["n_viagens"] = 100.0
    p1 = prever(artefato, amostra)[0]
    p2 = prever(carregar_modelo(caminho), amostra)[0]
    assert p1 == p2  # estável entre recargas
    assert p1 > 0


def test_modelo_carregado_reproduz_metrica(ml_con, tmp_path: Path):
    modelo, metricas = treinar_modelo_final(ml_con)
    caminho = salvar_modelo(modelo, metricas, tmp_path / "modelo.joblib")
    artefato = carregar_modelo(caminho)

    _, validacao = temporal_split(build_dataset(ml_con, seed=42))
    recalc = avaliar(validacao[TARGET].to_numpy(), prever(artefato, validacao))
    assert abs(recalc["mae"] - metricas["mae"]) < 1e-6
    assert abs(recalc["rmse"] - metricas["rmse"]) < 1e-6

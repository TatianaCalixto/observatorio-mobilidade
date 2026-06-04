"""Testes da seção de previsões do app (S06-T04)."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.predict import carregar_artefato, montar_features, prever_demanda
from ml.serialize import salvar_modelo, treinar_modelo_final


def test_prever_demanda_com_artefato_de_fixture(ml_con, tmp_path: Path):
    modelo, metricas = treinar_modelo_final(ml_con)
    caminho = salvar_modelo(modelo, metricas, tmp_path / "modelo.joblib")

    artefato = carregar_artefato(caminho)
    features = montar_features(
        n_viagens=100, iso_dia_semana=3, mes=6, precipitacao=10, temperatura=18, choveu=True
    )
    valor = prever_demanda(artefato, features)
    assert isinstance(valor, float)
    assert valor > 0


def test_montar_features_deriva_fim_de_semana_e_choveu():
    fds = montar_features(
        n_viagens=50, iso_dia_semana=7, mes=6, precipitacao=0, temperatura=25, choveu=False
    )
    assert fds["fim_de_semana"] == 1
    assert fds["choveu"] == 0

    util = montar_features(
        n_viagens=50, iso_dia_semana=3, mes=6, precipitacao=5, temperatura=25, choveu=True
    )
    assert util["fim_de_semana"] == 0
    assert util["choveu"] == 1


def test_pagina_previsoes_renderiza_sem_excecao():
    # Com ou sem artefato (CI não tem), a página trata e não lança exceção.
    at = AppTest.from_file("app/main.py", default_timeout=60).run()
    at.sidebar.radio[0].set_value("Previsões").run()
    assert at.exception == []

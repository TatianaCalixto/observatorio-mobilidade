"""Testes da preparação da camada do mapa (S06-T03)."""

from streamlit.testing.v1 import AppTest

from app.mapa import preparar_paradas


def test_preparar_paradas_descarta_sem_coordenada(app_con):
    df = preparar_paradas(app_con)
    assert set(df.columns) >= {
        "stop_id",
        "stop_name",
        "stop_lat",
        "stop_lon",
        "n_passagens",
        "intensidade",
    }
    # A parada S3 (sem coordenada) é descartada -> sem erro.
    assert df.height == 2
    assert "S3" not in df["stop_id"].to_list()
    assert df["stop_lat"].null_count() == 0
    assert df["stop_lon"].null_count() == 0


def test_preparar_paradas_intensidade_normalizada(app_con):
    df = preparar_paradas(app_con)
    s1 = df.filter(df["stop_id"] == "S1")
    assert s1["n_passagens"].item() == 2  # S1 aparece em 2 stop_times
    assert s1["intensidade"].item() == 1.0  # mais movimentada -> 1.0
    assert df["intensidade"].min() >= 0.0
    assert df["intensidade"].max() == 1.0


def test_pagina_mapa_renderiza_sem_excecao():
    at = AppTest.from_file("app/main.py", default_timeout=60).run()
    at.sidebar.radio[0].set_value("Mapa da Rede").run()
    assert at.exception == []

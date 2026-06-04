"""Testes da preparação da camada do mapa (S06-T03 / S10-T01)."""

import polars as pl
from streamlit.testing.v1 import AppTest

from app.mapa import adicionar_cores, cor_viridis, preparar_heatmap, preparar_paradas


def test_preparar_heatmap_coordenadas_e_peso(app_con):
    paradas = preparar_paradas(app_con)
    hm = preparar_heatmap(paradas)
    assert hm.columns == ["stop_lon", "stop_lat", "peso"]
    assert hm["peso"].dtype == pl.Float64
    assert hm["peso"].sum() == float(paradas["n_passagens"].sum())


def test_cor_viridis_faixas_esperadas():
    assert cor_viridis(0.0) == [68, 1, 84]  # roxo escuro (baixo)
    assert cor_viridis(1.0) == [253, 231, 37]  # amarelo (alto)
    assert cor_viridis(0.5) == [38, 130, 142]  # teal (âncora central)
    assert cor_viridis(0.25) == [62, 73, 137]
    # fora de [0,1] é fixado (clamp)
    assert cor_viridis(-3) == [68, 1, 84]
    assert cor_viridis(9) == [253, 231, 37]


def test_adicionar_cores_rgb(app_con):
    df = adicionar_cores(preparar_paradas(app_con))
    assert {"r", "g", "b"} <= set(df.columns)
    assert df["r"].dtype == pl.Int64
    # a parada mais movimentada (intensidade 1.0) -> amarelo Viridis
    topo = df.sort("intensidade", descending=True).row(0, named=True)
    assert [topo["r"], topo["g"], topo["b"]] == [253, 231, 37]


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


def test_pagina_mapa_modo_calor_renderiza():
    at = AppTest.from_file("app/main.py", default_timeout=60).run()
    at.sidebar.radio[0].set_value("Mapa da Rede").run()
    viz = next(r for r in at.radio if r.label == "Visualização")
    viz.set_value("Mapa de calor").run()
    assert at.exception == []

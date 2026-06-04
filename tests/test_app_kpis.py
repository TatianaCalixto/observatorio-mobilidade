"""Testes das funções de agregação que alimentam o dashboard de KPIs (S06-T02)."""

from datetime import date

from streamlit.testing.v1 import AppTest

from analysis.queries import agregado_clima, linhas_pior_headway, sazonalidade_dia_semana
from app import data as appdata


def test_pagina_kpis_renderiza_sem_excecao():
    at = AppTest.from_file("app/main.py", default_timeout=60).run()
    at.sidebar.radio[0].set_value("KPIs & Análises").run()
    assert at.exception == []


def test_listar_linhas(app_con):
    df = appdata.listar_linhas(app_con)
    assert df.columns == ["route_id", "route_short_name"]
    assert df.height == 3


def test_oferta_diaria_linha(app_con):
    df = appdata.oferta_diaria_linha(app_con, "R1")
    assert df.columns == ["data", "n_viagens", "headway_med_min"]
    assert df.height > 0
    assert df["n_viagens"].min() > 0


def test_oferta_diaria_linha_periodo_vazio(app_con):
    df = appdata.oferta_diaria_linha(app_con, "R1", date(2030, 1, 1), date(2030, 1, 2))
    assert df.height == 0
    assert "n_viagens" in df.columns


def test_funcoes_dos_graficos_entrada_saida(app_con):
    saz = sazonalidade_dia_semana(app_con)
    assert "media_viagens_dia" in saz.columns
    assert saz.height == 7  # cobre todos os dias da semana

    clima = agregado_clima(app_con)
    assert "oferta_media" in clima.columns
    assert clima.height >= 1

    gargalos = linhas_pior_headway(app_con, n=5)
    assert "headway_med_min" in gargalos.columns
    assert 1 <= gargalos.height <= 3  # 3 linhas no fixture

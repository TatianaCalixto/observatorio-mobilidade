"""Smoke tests do app Streamlit (S06-T01): boot sem exceção + funções de dados."""

from datetime import date

import polars as pl
from streamlit.testing.v1 import AppTest

from app import data as appdata
from app.main import PAGINAS

APP = "app/main.py"


def test_app_sobe_sem_excecao():
    # Sobe o app (sem browser). Mesmo sem o DuckDB pronto, deve tratar o erro e não quebrar.
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert at.exception == []
    assert len(at.sidebar) > 0  # navegação renderizada


def test_preparar_tabela_gargalos_colunas(app_con):
    from analysis.queries import linhas_pior_headway

    tab = appdata.preparar_tabela_gargalos(linhas_pior_headway(app_con, n=5))
    assert tab.columns == ["Linha", "Headway (min)", "Viagens/dia"]
    assert tab.height >= 1


def test_variacao_metrica_periodo_atual_vs_anterior():
    rec, delta = appdata.variacao_metrica([10, 10, 20, 20])
    assert rec == 20.0 and delta == 10.0  # subiu
    _, delta_queda = appdata.variacao_metrica([20, 20, 10, 10])
    assert delta_queda == -10.0  # caiu
    assert appdata.variacao_metrica([5]) == (5.0, 0.0)  # série curta → delta 0
    assert appdata.variacao_metrica([]) == (0.0, 0.0)


def test_paginas_definidas():
    assert PAGINAS[0] == "Visão Geral"
    assert "Previsões" in PAGINAS


def test_kpis_gerais_retorna_dict(app_con):
    kpis = appdata.kpis_gerais(app_con)
    assert kpis["n_linhas"] == 3
    assert kpis["n_paradas"] == 3
    assert kpis["oferta_util"] is not None
    assert kpis["headway_med_min"] is not None


def test_oferta_diaria_retorna_dataframe(app_con):
    df = appdata.oferta_diaria(app_con)
    assert isinstance(df, pl.DataFrame)
    assert df.height > 0
    assert "total_viagens" in df.columns


def test_oferta_diaria_periodo_vazio_nao_quebra(app_con):
    df = appdata.oferta_diaria(app_con, date(2030, 1, 1), date(2030, 1, 2))
    assert df.height == 0
    assert "total_viagens" in df.columns

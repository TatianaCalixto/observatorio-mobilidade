"""Teste do agregado climático (analysis.queries) com fixture sem chuva vs com chuva."""

import duckdb
import pytest

from analysis.queries import agregado_clima, correlacao_clima_oferta


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    c.execute(
        "create table mart_oferta_diaria (data date, ano integer, mes integer, "
        "iso_dia_semana integer, dia_semana varchar, fim_de_semana boolean, "
        "total_viagens double, n_linhas_ativas integer, headway_med_min double, "
        "precipitacao_total_mm double, temperatura_media_c double, choveu boolean)"
    )
    # 2 dias sem chuva (oferta 100) e 2 dias com chuva (oferta 80).
    c.execute(
        "insert into mart_oferta_diaria values "
        "('2025-06-02',2025,6,1,'Monday',false,100,10,15, 0.0,18,false), "
        "('2025-06-03',2025,6,2,'Tuesday',false,100,10,15, 0.0,19,false), "
        "('2025-06-04',2025,6,3,'Wednesday',false,80,10,18, 12.0,16,true), "
        "('2025-06-05',2025,6,4,'Thursday',false,80,10,18, 5.0,17,true)"
    )
    yield c
    c.close()


def test_agregado_clima_sem_vs_com_chuva(con):
    df = agregado_clima(con)
    assert df.columns == ["condicao", "n_dias", "oferta_media", "headway_med_min"]
    assert df.height == 2
    com = df.filter(df["condicao"] == "com chuva")
    sem = df.filter(df["condicao"] == "sem chuva")
    assert com["n_dias"].item() == 2
    assert sem["n_dias"].item() == 2
    assert sem["oferta_media"].item() == 100.0
    assert com["oferta_media"].item() == 80.0


def test_correlacao_clima_oferta_schema(con):
    df = correlacao_clima_oferta(con)
    assert df.columns == ["corr_precip_oferta", "corr_temp_oferta"]
    assert df.height == 1
    # Correlação precip x oferta deve ser negativa na fixture (chuva -> oferta menor).
    assert df["corr_precip_oferta"].item() < 0

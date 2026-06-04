"""Teste de integração das consultas analíticas (analysis.queries) com DuckDB controlado."""

from datetime import date

import duckdb
import pytest

from analysis.queries import (
    linhas_maior_oferta,
    linhas_pior_headway,
    sazonalidade_dia_semana,
    sazonalidade_mes,
)


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    c.execute(
        "create table dim_linha (route_id varchar, route_short_name varchar, "
        "route_long_name varchar, route_type integer, modo varchar)"
    )
    c.execute(
        "insert into dim_linha values "
        "('R1','R1','Linha 1',3,'Ônibus'), ('R2','R2','Linha 2',3,'Ônibus')"
    )
    c.execute(
        "create table dim_tempo (data date, ano integer, mes integer, dia integer, "
        "iso_dia_semana integer, dia_semana varchar, nome_mes varchar, fim_de_semana boolean)"
    )
    c.execute(
        "insert into dim_tempo values "
        "('2025-06-02',2025,6,2,1,'Monday','June',false), "
        "('2025-06-07',2025,6,7,6,'Saturday','June',true)"
    )
    c.execute(
        "create table fct_viagens_dia (viagem_dia_sk varchar, route_id varchar, data date, "
        "iso_dia_semana integer, n_viagens double, headway_med_min double, "
        "paradas_por_viagem_med double, n_padroes integer)"
    )
    c.execute(
        "insert into fct_viagens_dia values "
        "('R1|2025-06-02','R1','2025-06-02',1,100,10,5,1), "
        "('R2|2025-06-02','R2','2025-06-02',1,50,20,5,1), "
        "('R1|2025-06-07','R1','2025-06-07',6,80,12,5,1)"
    )
    yield c
    c.close()


def test_linhas_maior_oferta_schema_e_ordem(con):
    df = linhas_maior_oferta(con, n=10)
    assert df.columns == ["route_id", "route_short_name", "media_viagens_dia", "headway_med_min"]
    # R1 média (100+80)/2 = 90 > R2 (50) -> R1 primeiro.
    assert df["route_id"].to_list() == ["R1", "R2"]
    assert df["media_viagens_dia"][0] == 90.0


def test_linhas_pior_headway_identifica_gargalo(con):
    df = linhas_pior_headway(con, n=10)
    assert df.columns == ["route_id", "route_short_name", "headway_med_min", "media_viagens_dia"]
    # R2 headway 20 > R1 (11) -> R2 é o pior (gargalo de regularidade).
    assert df["route_id"][0] == "R2"


def test_sazonalidade_dia_semana(con):
    df = sazonalidade_dia_semana(con)
    assert df.columns == ["iso_dia_semana", "dia_semana", "media_viagens_dia"]
    linha_seg = df.filter(df["iso_dia_semana"] == 1)
    linha_sab = df.filter(df["iso_dia_semana"] == 6)
    assert linha_seg["media_viagens_dia"].item() == 150.0  # 100 + 50 em 1 segunda
    assert linha_sab["media_viagens_dia"].item() == 80.0


def test_sazonalidade_mes_schema(con):
    df = sazonalidade_mes(con)
    assert df.columns == ["ano", "mes", "media_viagens_dia"]
    assert df.height == 1  # tudo em junho/2025


def test_periodo_vazio_nao_quebra(con):
    # Período sem dados -> resultado vazio, sem erro.
    vazio = sazonalidade_dia_semana(con, date(2030, 1, 1), date(2030, 1, 2))
    assert vazio.height == 0
    assert vazio.columns == ["iso_dia_semana", "dia_semana", "media_viagens_dia"]
    vazio_mes = sazonalidade_mes(con, date(2030, 1, 1), date(2030, 1, 2))
    assert vazio_mes.height == 0

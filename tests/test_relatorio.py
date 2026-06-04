"""Reprodutibilidade do relatório de insights (analysis.gerar_relatorio)."""

import duckdb
import pytest

from analysis.gerar_relatorio import coletar_numeros, render_markdown


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    c.execute(
        "create table dim_linha (route_id varchar, route_short_name varchar, "
        "route_long_name varchar, route_type integer, modo varchar)"
    )
    c.execute(
        "insert into dim_linha values ('R1','R1','L1',3,'Ônibus'), ('R2','R2','L2',3,'Ônibus')"
    )
    c.execute(
        "create table dim_parada (stop_id varchar, stop_name varchar, "
        "stop_lat double, stop_lon double)"
    )
    c.execute("insert into dim_parada values ('S1','P1',-23,-46), ('S2','P2',-23,-46)")
    c.execute(
        "create table dim_tempo (data date, ano integer, mes integer, dia integer, "
        "iso_dia_semana integer, dia_semana varchar, nome_mes varchar, fim_de_semana boolean)"
    )
    c.execute(
        "insert into dim_tempo values "
        "('2025-06-02',2025,6,2,1,'Monday','June',false), "
        "('2025-06-07',2025,6,7,6,'Saturday','June',true), "
        "('2025-06-08',2025,6,8,7,'Sunday','June',true)"
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
        "('R1|2025-06-07','R1','2025-06-07',6,80,10,5,1), "
        "('R1|2025-06-08','R1','2025-06-08',7,70,10,5,1)"
    )
    c.execute(
        "create table mart_oferta_diaria (data date, ano integer, mes integer, "
        "iso_dia_semana integer, dia_semana varchar, fim_de_semana boolean, "
        "total_viagens double, n_linhas_ativas integer, headway_med_min double, "
        "precipitacao_total_mm double, temperatura_media_c double, choveu boolean)"
    )
    c.execute(
        "insert into mart_oferta_diaria values "
        "('2025-06-02',2025,6,1,'Monday',false,150,2,15,0,18,false), "
        "('2025-06-07',2025,6,6,'Saturday',true,80,1,10,10,17,true), "
        "('2025-06-08',2025,6,7,'Sunday',true,70,1,10,0,19,false)"
    )
    yield c
    c.close()


def test_coletar_numeros_reproduzivel(con):
    primeira = coletar_numeros(con)
    segunda = coletar_numeros(con)
    assert primeira == segunda  # re-rodar gera os mesmos números
    assert primeira["oferta_util"] == 150.0
    assert primeira["n_linhas"] == 2
    assert primeira["periodo"] == ("2025-06-02", "2025-06-08")


def test_render_responde_pergunta_de_negocio(con):
    md = render_markdown(coletar_numeros(con))
    assert "Pergunta de negócio" in md
    assert "Resposta à pergunta de negócio" in md
    assert "oferta_dia_semana.png" in md
    assert "Gargalos" in md

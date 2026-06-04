"""Testes do dataset de ML (ml.features): shape, vazamento temporal, determinismo."""

from datetime import date

import duckdb
import pytest

from ml.features import (
    DATA_CORTE,
    FEATURE_COLUMNS,
    TARGET,
    build_dataset,
    temporal_split,
)


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    c.execute(
        "create table dim_tempo (data date, ano integer, mes integer, dia integer, "
        "iso_dia_semana integer, dia_semana varchar, nome_mes varchar, fim_de_semana boolean)"
    )
    c.execute(
        "insert into dim_tempo values "
        "('2025-12-01',2025,12,1,1,'Monday','December',false), "
        "('2026-04-01',2026,4,1,3,'Wednesday','April',false)"
    )
    c.execute(
        "create table dim_clima (data date, estacao varchar, precipitacao_total_mm double, "
        "temperatura_media_c double, temperatura_min_c double, temperatura_max_c double, "
        "choveu boolean)"
    )
    c.execute(
        "insert into dim_clima values "
        "('2025-12-01','A701',0.0,25.0,20,30,false), "
        "('2026-04-01','A701',10.0,18.0,15,22,true)"
    )
    c.execute(
        "create table fct_viagens_dia (viagem_dia_sk varchar, route_id varchar, data date, "
        "iso_dia_semana integer, n_viagens double, headway_med_min double, "
        "paradas_por_viagem_med double, n_padroes integer)"
    )
    c.execute(
        "insert into fct_viagens_dia values "
        "('R1|2025-12-01','R1','2025-12-01',1,100,10,5,1), "
        "('R2|2025-12-01','R2','2025-12-01',1,50,20,5,1), "
        "('R1|2026-04-01','R1','2026-04-01',3,100,10,5,1)"
    )
    yield c
    c.close()


def test_dataset_shape_e_colunas(con):
    df = build_dataset(con)
    assert df.height == 3
    for col in [*FEATURE_COLUMNS, TARGET, "route_id", "data"]:
        assert col in df.columns
    assert df[TARGET].min() >= 0  # demanda não-negativa


def test_sem_vazamento_temporal(con):
    df = build_dataset(con)
    treino, validacao = temporal_split(df, DATA_CORTE)
    # Corte respeitado: treino estritamente antes; validação a partir do corte.
    assert treino["data"].max() < DATA_CORTE
    assert validacao["data"].min() >= DATA_CORTE
    # Conjuntos disjuntos e completos.
    assert treino.height + validacao.height == df.height
    assert set(treino["data"].to_list()).isdisjoint(validacao["data"].to_list())


def test_determinismo_com_seed(con):
    a = build_dataset(con, seed=42)
    b = build_dataset(con, seed=42)
    assert a[TARGET].to_list() == b[TARGET].to_list()
    # Seed diferente muda o alvo.
    c = build_dataset(con, seed=7)
    assert a[TARGET].to_list() != c[TARGET].to_list()


def test_clima_modula_o_alvo(con):
    # Sem ruído (mesmo seed/ordem), o dia chuvoso deve elevar a demanda relativa à oferta.
    df = build_dataset(con, seed=42).sort("route_id", "data")
    seco = df.filter((df["route_id"] == "R1") & (df["data"] == date(2025, 12, 1)))
    chuva = df.filter((df["route_id"] == "R1") & (df["data"] == date(2026, 4, 1)))
    # Mesma oferta (100), mas dia com chuva tem fator de demanda maior.
    assert chuva[TARGET].item() > seco[TARGET].item()

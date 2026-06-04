"""Configuração compartilhada da suíte de testes.

A raiz do repositório é exposta para imports via ``pythonpath = ["."]`` no
``pyproject.toml`` ([tool.pytest.ini_options]). Fixtures comuns vão aqui.
"""

from datetime import date, timedelta
from pathlib import Path

import duckdb
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Caminho absoluto da raiz do projeto."""
    return PROJECT_ROOT


def _criar_marts_temporais(c: duckdb.DuckDBPyConnection) -> None:
    """Cria e popula dim_tempo, dim_clima e fct_viagens_dia (~6 meses × 3 linhas)."""
    c.execute(
        "create table dim_tempo (data date, ano integer, mes integer, dia integer, "
        "iso_dia_semana integer, dia_semana varchar, nome_mes varchar, fim_de_semana boolean)"
    )
    c.execute(
        "create table dim_clima (data date, estacao varchar, precipitacao_total_mm double, "
        "temperatura_media_c double, temperatura_min_c double, temperatura_max_c double, "
        "choveu boolean)"
    )
    c.execute(
        "create table fct_viagens_dia (viagem_dia_sk varchar, route_id varchar, data date, "
        "iso_dia_semana integer, n_viagens double, headway_med_min double, "
        "paradas_por_viagem_med double, n_padroes integer)"
    )

    tempo, clima, fct = [], [], []
    d0 = date(2025, 11, 1)
    for i in range(180):
        d = d0 + timedelta(days=i)
        iso = d.isoweekday()
        fds = iso >= 6
        precip = float((i % 7) * 2)
        temp = 18.0 + (i % 10)
        tempo.append((d, d.year, d.month, d.day, iso, d.strftime("%A"), d.strftime("%B"), fds))
        clima.append((d, "A701", precip, temp, temp - 3, temp + 3, precip > 0))
        for route, base in (("R1", 100), ("R2", 50), ("R3", 200)):
            nv = float(base - (10 if fds else 0))
            fct.append((f"{route}|{d}", route, d, iso, nv, 10.0, 5.0, 1))

    c.executemany("insert into dim_tempo values (?,?,?,?,?,?,?,?)", tempo)
    c.executemany("insert into dim_clima values (?,?,?,?,?,?,?)", clima)
    c.executemany("insert into fct_viagens_dia values (?,?,?,?,?,?,?,?)", fct)


@pytest.fixture
def ml_con():
    """DuckDB controlado com marts temporais mínimos para os testes de ML."""
    c = duckdb.connect(":memory:")
    _criar_marts_temporais(c)
    yield c
    c.close()


def _popular_warehouse(c: duckdb.DuckDBPyConnection) -> None:
    """Cria o warehouse mínimo completo (marts temporais + dimensões + mart diário)."""
    _criar_marts_temporais(c)
    c.execute(
        "create table dim_linha (route_id varchar, route_short_name varchar, "
        "route_long_name varchar, route_type integer, modo varchar)"
    )
    c.execute(
        "insert into dim_linha values "
        "('R1','R1','Linha 1',3,'Ônibus'), ('R2','R2','Linha 2',3,'Ônibus'), "
        "('R3','R3','Metrô 3',1,'Metrô')"
    )
    c.execute(
        "create table dim_parada (stop_id varchar, stop_name varchar, "
        "stop_lat double, stop_lon double)"
    )
    c.execute(
        "insert into dim_parada values "
        "('S1','Parada 1',-23.55,-46.63), ('S2','Parada 2',-23.56,-46.64), "
        "('S3','Sem Coordenada',NULL,NULL)"
    )
    c.execute(
        "create table stg_gtfs__stop_times (stop_time_id varchar, trip_id varchar, "
        "stop_id varchar, stop_sequence integer, arrival_time varchar, departure_time varchar)"
    )
    c.execute(
        "insert into stg_gtfs__stop_times values "
        "('t1-1','t1','S1',1,'05:00:00','05:00:00'), "
        "('t1-2','t1','S2',2,'05:10:00','05:10:00'), "
        "('t2-1','t2','S1',1,'06:00:00','06:00:00')"
    )
    c.execute(
        "create table mart_oferta_diaria (data date, ano integer, mes integer, "
        "iso_dia_semana integer, dia_semana varchar, fim_de_semana boolean, "
        "total_viagens double, n_linhas_ativas integer, headway_med_min double, "
        "precipitacao_total_mm double, temperatura_media_c double, choveu boolean)"
    )
    c.execute(
        """
        insert into mart_oferta_diaria
        select t.data, t.ano, t.mes, t.iso_dia_semana, t.dia_semana, t.fim_de_semana,
               sum(f.n_viagens), count(distinct f.route_id), avg(f.headway_med_min),
               c.precipitacao_total_mm, c.temperatura_media_c, c.choveu
        from fct_viagens_dia f
        join dim_tempo t using (data)
        left join dim_clima c using (data)
        group by t.data, t.ano, t.mes, t.iso_dia_semana, t.dia_semana, t.fim_de_semana,
                 c.precipitacao_total_mm, c.temperatura_media_c, c.choveu
        """
    )


@pytest.fixture
def app_con():
    """DuckDB controlado em memória com o warehouse mínimo para os testes do app."""
    c = duckdb.connect(":memory:")
    _popular_warehouse(c)
    yield c
    c.close()


@pytest.fixture(scope="session", autouse=True)
def _ambiente_app(tmp_path_factory):
    """Prepara um warehouse de teste em arquivo e aponta o app para ele (via env).

    Garante que os testes do app (AppTest) rendam contra um DuckDB determinístico — sem
    depender do ``mobilidade.duckdb`` real nem de um ``.env`` — para cobertura estável
    em local e no CI. Também garante um artefato de modelo para a página de previsões.
    """
    import os

    base = tmp_path_factory.mktemp("warehouse")
    db_path = base / "marts_test.duckdb"
    con = duckdb.connect(str(db_path))
    _popular_warehouse(con)
    con.close()

    os.environ["DATA_INICIO"] = "2025-06-01"
    os.environ["DATA_FIM"] = "2026-05-31"
    os.environ["DUCKDB_PATH"] = str(db_path)

    from ml.serialize import DEFAULT_MODEL_PATH, salvar_modelo, treinar_modelo_final

    if not DEFAULT_MODEL_PATH.exists():
        con = duckdb.connect(str(db_path), read_only=True)
        try:
            modelo, metricas = treinar_modelo_final(con)
        finally:
            con.close()
        salvar_modelo(modelo, metricas)
    yield

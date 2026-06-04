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


@pytest.fixture
def ml_con():
    """DuckDB controlado com marts mínimos para os testes de ML.

    ~6 meses (cruzando o corte 2026-03-01) × 3 linhas, com clima variado, em
    ``fct_viagens_dia`` + ``dim_tempo`` + ``dim_clima``.
    """
    c = duckdb.connect(":memory:")
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
    yield c
    c.close()

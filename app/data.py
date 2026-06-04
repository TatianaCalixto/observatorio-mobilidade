"""Camada de dados do app: leitura dos marts no DuckDB (read-only).

As funções de consulta recebem uma conexão DuckDB e retornam DataFrames — assim são
testáveis sem o runtime do Streamlit. ``get_con`` é a conexão cacheada usada pela UI.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import duckdb
import polars as pl
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def caminho_db() -> Path:
    """Resolve o DuckDB a usar, em ordem: env ``DUCKDB_PATH`` → warehouse local →
    snapshot de demo (``app_data/marts.duckdb``, usado no deploy público)."""
    env = os.environ.get("DUCKDB_PATH")
    if env:
        return Path(env)
    local = PROJECT_ROOT / "mobilidade.duckdb"
    if local.exists():
        return local
    return PROJECT_ROOT / "app_data" / "marts.duckdb"


def conectar(caminho: str | Path | None = None) -> duckdb.DuckDBPyConnection:
    """Abre uma conexão DuckDB read-only para os marts do projeto."""
    if caminho is None:
        caminho = caminho_db()
    return duckdb.connect(str(caminho), read_only=True)


@st.cache_resource(show_spinner=False)
def get_con() -> duckdb.DuckDBPyConnection:
    """Conexão DuckDB cacheada para a UI (uma por sessão do app)."""
    return conectar()


def kpis_gerais(con: duckdb.DuckDBPyConnection) -> dict[str, float]:
    """KPIs de cabeçalho: nº de linhas/paradas, oferta média e headway."""
    n_linhas = con.execute("select count(*) from dim_linha").fetchone()[0]
    n_paradas = con.execute("select count(*) from dim_parada").fetchone()[0]
    row = con.execute(
        """
        select
            round(avg(case when iso_dia_semana <= 5 then total_viagens end), 0),
            round(avg(case when iso_dia_semana >= 6 then total_viagens end), 0),
            round(avg(headway_med_min), 1)
        from mart_oferta_diaria
        """
    ).fetchone()
    return {
        "n_linhas": int(n_linhas),
        "n_paradas": int(n_paradas),
        "oferta_util": row[0],
        "oferta_fim_semana": row[1],
        "headway_med_min": row[2],
    }


def oferta_diaria(
    con: duckdb.DuckDBPyConnection,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> pl.DataFrame:
    """Série diária da rede (mart_oferta_diaria), opcionalmente filtrada por período."""
    where, params = "", []
    if data_inicio is not None and data_fim is not None:
        where = "where data between ? and ?"
        params = [data_inicio, data_fim]
    return con.execute(
        f"""
        select data, total_viagens, n_linhas_ativas, headway_med_min,
               precipitacao_total_mm, temperatura_media_c, choveu
        from mart_oferta_diaria
        {where}
        order by data
        """,
        params,
    ).pl()


def periodo_disponivel(con: duckdb.DuckDBPyConnection) -> tuple[date, date]:
    """Menor e maior data disponível na série diária."""
    row = con.execute("select min(data), max(data) from mart_oferta_diaria").fetchone()
    return row[0], row[1]


def listar_linhas(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Lista as linhas (route_id, nome) para seleção no app."""
    return con.execute(
        "select route_id, route_short_name from dim_linha order by route_short_name"
    ).pl()


def oferta_diaria_linha(
    con: duckdb.DuckDBPyConnection,
    route_id: str,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> pl.DataFrame:
    """Série diária de oferta (partidas/dia e headway) de uma linha específica."""
    where = "where route_id = ?"
    params: list = [route_id]
    if data_inicio is not None and data_fim is not None:
        where += " and data between ? and ?"
        params += [data_inicio, data_fim]
    return con.execute(
        f"""
        select data, n_viagens, headway_med_min
        from fct_viagens_dia
        {where}
        order by data
        """,
        params,
    ).pl()


def oferta_tipica_linha(con: duckdb.DuckDBPyConnection, route_id: str) -> float:
    """Oferta média (partidas/dia) de uma linha — usada como base para a predição."""
    row = con.execute(
        "select avg(n_viagens) from fct_viagens_dia where route_id = ?", [route_id]
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else 0.0

"""Consultas analíticas reutilizáveis (gargalos e sazonalidade) sobre os marts.

As funções recebem uma conexão DuckDB já aberta e retornam ``polars.DataFrame``.
São usadas pelo relatório de insights e testáveis com um DuckDB controlado.
Trabalham sobre ``fct_viagens_dia`` + ``dim_tempo`` + ``dim_linha``.
"""

from __future__ import annotations

from datetime import date

import duckdb
import polars as pl


def linhas_maior_oferta(con: duckdb.DuckDBPyConnection, n: int = 10) -> pl.DataFrame:
    """Linhas com maior oferta média (partidas/dia)."""
    sql = """
        select
            f.route_id,
            any_value(l.route_short_name)      as route_short_name,
            round(avg(f.n_viagens), 1)         as media_viagens_dia,
            round(avg(f.headway_med_min), 1)   as headway_med_min
        from fct_viagens_dia f
        join dim_linha l using (route_id)
        group by f.route_id
        order by media_viagens_dia desc
        limit ?
    """
    return con.execute(sql, [n]).pl()


def linhas_pior_headway(con: duckdb.DuckDBPyConnection, n: int = 10) -> pl.DataFrame:
    """Gargalos de regularidade: linhas com maior headway médio (esperas mais longas)."""
    sql = """
        select
            f.route_id,
            any_value(l.route_short_name)      as route_short_name,
            round(avg(f.headway_med_min), 1)   as headway_med_min,
            round(avg(f.n_viagens), 1)         as media_viagens_dia
        from fct_viagens_dia f
        join dim_linha l using (route_id)
        group by f.route_id
        having avg(f.headway_med_min) is not null
        order by headway_med_min desc
        limit ?
    """
    return con.execute(sql, [n]).pl()


def _periodo(data_inicio: date | None, data_fim: date | None) -> tuple[str, list[date]]:
    if data_inicio is not None and data_fim is not None:
        return "where f.data between ? and ?", [data_inicio, data_fim]
    return "", []


def sazonalidade_dia_semana(
    con: duckdb.DuckDBPyConnection,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> pl.DataFrame:
    """Oferta média da rede por dia da semana (total de partidas / nº de dias daquele dia)."""
    where, params = _periodo(data_inicio, data_fim)
    sql = f"""
        select
            t.iso_dia_semana,
            any_value(t.dia_semana)                                  as dia_semana,
            round(sum(f.n_viagens) / count(distinct f.data), 1)      as media_viagens_dia
        from fct_viagens_dia f
        join dim_tempo t using (data)
        {where}
        group by t.iso_dia_semana
        order by t.iso_dia_semana
    """
    return con.execute(sql, params).pl()


def sazonalidade_mes(
    con: duckdb.DuckDBPyConnection,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> pl.DataFrame:
    """Oferta média da rede por mês."""
    where, params = _periodo(data_inicio, data_fim)
    sql = f"""
        select
            t.ano,
            t.mes,
            round(sum(f.n_viagens) / count(distinct f.data), 1)      as media_viagens_dia
        from fct_viagens_dia f
        join dim_tempo t using (data)
        {where}
        group by t.ano, t.mes
        order by t.ano, t.mes
    """
    return con.execute(sql, params).pl()


def agregado_clima(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Oferta diária média agregada por condição de chuva (sem chuva vs com chuva).

    Consulta ``mart_oferta_diaria``. Como a oferta é PLANEJADA (independente do clima),
    diferenças aqui refletem o confundidor tipo-de-dia (dias de chuva caírem mais em
    úteis/fins de semana), não um efeito causal do clima — ver método no relatório.
    """
    sql = """
        select
            case when choveu then 'com chuva' else 'sem chuva' end as condicao,
            count(*)                              as n_dias,
            round(avg(total_viagens), 0)          as oferta_media,
            round(avg(headway_med_min), 2)        as headway_med_min
        from mart_oferta_diaria
        group by choveu
        order by condicao
    """
    return con.execute(sql).pl()


def correlacao_clima_oferta(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Correlação de Pearson entre variáveis climáticas e a oferta diária total."""
    sql = """
        select
            round(corr(precipitacao_total_mm, total_viagens), 4) as corr_precip_oferta,
            round(corr(temperatura_media_c, total_viagens), 4)   as corr_temp_oferta
        from mart_oferta_diaria
        where precipitacao_total_mm is not null
    """
    return con.execute(sql).pl()

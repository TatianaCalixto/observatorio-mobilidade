"""Preparação da camada do mapa: paradas georreferenciadas com intensidade.

A intensidade é o **movimento** da parada (nº de passagens no GTFS, de
``stg_gtfs__stop_times``), normalizado em [0, 1] — um proxy de importância/demanda na rede.
Paradas sem coordenada são descartadas (não quebram o mapa).
"""

from __future__ import annotations

import duckdb
import polars as pl


def preparar_paradas(con: duckdb.DuckDBPyConnection, limite: int = 3000) -> pl.DataFrame:
    """Retorna as paradas com coordenada e intensidade normalizada (para a camada do mapa).

    Colunas: ``stop_id, stop_name, stop_lat, stop_lon, n_passagens, intensidade``.
    """
    df = con.execute(
        """
        select
            p.stop_id,
            p.stop_name,
            p.stop_lat,
            p.stop_lon,
            count(st.stop_id) as n_passagens
        from dim_parada p
        left join stg_gtfs__stop_times st using (stop_id)
        where p.stop_lat is not null and p.stop_lon is not null
        group by p.stop_id, p.stop_name, p.stop_lat, p.stop_lon
        order by n_passagens desc
        limit ?
        """,
        [limite],
    ).pl()

    if df.height == 0:
        return df.with_columns(pl.lit(0.0).alias("intensidade"))

    maximo = df["n_passagens"].max() or 1
    return df.with_columns((pl.col("n_passagens") / maximo).alias("intensidade"))

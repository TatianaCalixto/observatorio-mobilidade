"""Preparação da camada do mapa: paradas georreferenciadas com intensidade.

A intensidade é o **movimento** da parada (nº de passagens no GTFS, de
``stg_gtfs__stop_times``), normalizado em [0, 1] — um proxy de importância/demanda na rede.
Paradas sem coordenada são descartadas (não quebram o mapa).
"""

from __future__ import annotations

import duckdb
import polars as pl

#: Âncoras da escala perceptual **Viridis** (colorblind-safe), em RGB.
#: Em Python puro para não depender de matplotlib no runtime do app (deploy leve).
_VIRIDIS = [
    (68, 1, 84),
    (72, 40, 120),
    (62, 73, 137),
    (49, 104, 142),
    (38, 130, 142),
    (31, 158, 137),
    (53, 183, 121),
    (110, 206, 88),
    (253, 231, 37),
]


def cor_viridis(t: float) -> list[int]:
    """Mapeia uma intensidade em [0, 1] para uma cor RGB da escala Viridis (interpolada)."""
    t = max(0.0, min(1.0, float(t)))
    n = len(_VIRIDIS) - 1
    pos = t * n
    i = int(pos)
    if i >= n:
        return list(_VIRIDIS[n])
    frac = pos - i
    c0, c1 = _VIRIDIS[i], _VIRIDIS[i + 1]
    return [round(c0[k] + (c1[k] - c0[k]) * frac) for k in range(3)]


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


def adicionar_cores(df: pl.DataFrame) -> pl.DataFrame:
    """Adiciona colunas r/g/b da escala Viridis a partir de ``intensidade`` (para o mapa)."""
    cores = [cor_viridis(t) for t in df["intensidade"].to_list()]
    return df.with_columns(
        pl.Series("r", [c[0] for c in cores], dtype=pl.Int64),
        pl.Series("g", [c[1] for c in cores], dtype=pl.Int64),
        pl.Series("b", [c[2] for c in cores], dtype=pl.Int64),
    )


def preparar_heatmap(df: pl.DataFrame) -> pl.DataFrame:
    """Prepara os dados da camada de calor: coordenadas + ``peso`` (nº de passagens)."""
    return df.select(
        pl.col("stop_lon"),
        pl.col("stop_lat"),
        pl.col("n_passagens").cast(pl.Float64).alias("peso"),
    )

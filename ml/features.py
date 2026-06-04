"""Feature engineering e dataset de ML a partir dos marts (grão: linha × dia).

O **alvo** ``demanda_estimada_sim`` é **SIMULADO** (ver DEC-007): a oferta planejada real
(``n_viagens``) é modulada por clima + tipo-de-dia + ruído gaussiano com **seed fixa**.
Isso porque não há demanda/atraso *realizado* disponível com GTFS estático — a simulação
serve para demonstrar o pipeline de ML de forma reprodutível e ilustrar a pergunta de
negócio (clima/dia/linha → demanda). Os marts e a métrica de verdade permanecem reais.

Sem vazamento temporal: cada linha usa apenas atributos do próprio dia; o split é por data.
"""

from __future__ import annotations

from datetime import date

import duckdb
import numpy as np
import polars as pl

#: Colunas de features (todas conhecidas no momento da previsão).
FEATURE_COLUMNS: list[str] = [
    "n_viagens",
    "iso_dia_semana",
    "mes",
    "fim_de_semana",
    "precipitacao_total_mm",
    "temperatura_media_c",
    "choveu",
]

#: Nome do alvo SIMULADO (rótulo explícito de que é simulado).
TARGET: str = "demanda_estimada_sim"

#: Data de corte do split temporal: treino < corte ≤ validação (últimos ~3 meses).
DATA_CORTE: date = date(2026, 3, 1)

#: Seed padrão para o ruído da simulação (reprodutibilidade).
SEED_PADRAO: int = 42


def _base_query(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Lê a base (linha × dia) dos marts com atributos de tempo e clima."""
    sql = """
        select
            f.route_id,
            f.data,
            f.n_viagens,
            t.iso_dia_semana,
            t.mes,
            cast(t.fim_de_semana as integer)          as fim_de_semana,
            coalesce(c.precipitacao_total_mm, 0.0)     as precipitacao_total_mm,
            coalesce(c.temperatura_media_c, 20.0)      as temperatura_media_c,
            coalesce(cast(c.choveu as integer), 0)     as choveu
        from fct_viagens_dia f
        join dim_tempo t using (data)
        left join dim_clima c using (data)
        order by f.route_id, f.data
    """
    return con.execute(sql).pl()


def simular_demanda(df: pl.DataFrame, seed: int = SEED_PADRAO) -> pl.DataFrame:
    """Adiciona a coluna-alvo SIMULADA ``demanda_estimada_sim`` (determinística por seed).

    demanda = oferta · (1 + 0.25·choveu + 0.003·precip − 0.004·(temp−20)) · (1 + ruído),
    com ruído ~ N(0, 0.05). A ordem das linhas é fixada antes do ruído (reprodutibilidade).
    """
    df = df.sort("route_id", "data")
    rng = np.random.default_rng(seed)
    ruido = rng.normal(0.0, 0.05, df.height)

    base = df["n_viagens"].to_numpy().astype(float)
    choveu = df["choveu"].to_numpy().astype(float)
    precip = df["precipitacao_total_mm"].to_numpy().astype(float)
    temp = df["temperatura_media_c"].to_numpy().astype(float)

    fator_clima = 1.0 + 0.25 * choveu + 0.003 * precip - 0.004 * (temp - 20.0)
    demanda = base * fator_clima * (1.0 + ruido)
    demanda = np.clip(demanda, 0.0, None)

    return df.with_columns(pl.Series(TARGET, np.round(demanda, 1)))


def build_dataset(con: duckdb.DuckDBPyConnection, *, seed: int = SEED_PADRAO) -> pl.DataFrame:
    """Constrói o dataset de ML (features + alvo simulado) a partir dos marts."""
    return simular_demanda(_base_query(con), seed=seed)


def temporal_split(
    df: pl.DataFrame, data_corte: date = DATA_CORTE
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Split temporal: treino (data < corte) e validação (data ≥ corte). Sem vazamento."""
    treino = df.filter(pl.col("data") < data_corte)
    validacao = df.filter(pl.col("data") >= data_corte)
    return treino, validacao

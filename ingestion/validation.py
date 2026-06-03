"""Validação reutilizável de schema das ingestões (colunas obrigatórias + tipos).

Centraliza as regras de schema de cada fonte para que uma mudança no schema de origem
(coluna removida/renomeada, tipo alterado) gere uma falha **clara** — em vez de propagar
dados silenciosamente quebrados para as camadas seguintes.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import polars as pl

#: Colunas obrigatórias da ORIGEM por tabela GTFS (a RAW pode ter colunas extras).
GTFS_REQUIRED_COLUMNS: dict[str, set[str]] = {
    "stops": {"stop_id", "stop_name", "stop_lat", "stop_lon"},
    "routes": {"route_id", "route_short_name", "route_type"},
    "trips": {"route_id", "service_id", "trip_id"},
    "stop_times": {"trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"},
}

#: Schema esperado da saída tipada de clima (camada RAW).
CLIMA_SCHEMA: dict[str, pl.DataType] = {
    "data": pl.Date,
    "estacao": pl.String,
    "precipitacao_mm": pl.Float64,
    "temperatura_c": pl.Float64,
}

#: Schema esperado da saída de população (camada RAW).
POPULACAO_SCHEMA: dict[str, pl.DataType] = {
    "regiao_codigo": pl.String,
    "valor": pl.Int64,
}


class SchemaValidationError(RuntimeError):
    """Erro de validação de schema (coluna obrigatória ausente ou tipo divergente)."""


def validate_required_columns(
    df: pl.DataFrame, required: Iterable[str], *, source: str
) -> pl.DataFrame:
    """Garante que ``df`` contém todas as colunas em ``required``.

    Raises:
        SchemaValidationError: listando claramente as colunas ausentes.
    """
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise SchemaValidationError(
            f"{source}: colunas obrigatórias ausentes: {missing}. Presentes: {df.columns}."
        )
    return df


def validate_schema(
    df: pl.DataFrame, expected: Mapping[str, pl.DataType], *, source: str
) -> pl.DataFrame:
    """Valida presença e tipo das colunas esperadas em ``df``.

    Raises:
        SchemaValidationError: se faltar coluna ou um tipo divergir do esperado.
    """
    validate_required_columns(df, expected.keys(), source=source)
    mismatches = {
        col: (str(df.schema[col]), str(dtype))
        for col, dtype in expected.items()
        if df.schema[col] != dtype
    }
    if mismatches:
        raise SchemaValidationError(
            f"{source}: tipos divergentes (coluna: atual!=esperado): {mismatches}."
        )
    return df

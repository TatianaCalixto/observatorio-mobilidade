"""Carga das camadas RAW (Parquet) no DuckDB de forma idempotente.

Cada Parquet de ``data/raw/`` é materializado como uma tabela ``raw_*`` no
``mobilidade.duckdb`` via ``CREATE OR REPLACE TABLE ... AS SELECT * FROM read_parquet(...)``.
Como é ``CREATE OR REPLACE``, reexecutar não duplica dados — apenas recria a tabela a
partir do Parquet atual. As tabelas ``raw_*`` são a entrada das camadas *staging* do dbt.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from pathlib import Path

logger = logging.getLogger(__name__)

_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DuckDBLoadError(RuntimeError):
    """Erro na carga das camadas RAW no DuckDB."""


def discover_raw_parquets(
    raw_gtfs_dir: Path,
    raw_clima_dir: Path,
    raw_populacao_dir: Path,
) -> dict[str, Path]:
    """Mapeia ``{nome_tabela: caminho_parquet}`` a partir das pastas RAW existentes.

    Convenção: GTFS -> ``raw_gtfs_<tabela>``; clima -> ``raw_clima``;
    população -> ``raw_populacao``.
    """
    mapping: dict[str, Path] = {}
    for parquet in sorted(Path(raw_gtfs_dir).glob("*.parquet")):
        mapping[f"raw_gtfs_{parquet.stem}"] = parquet

    clima = Path(raw_clima_dir) / "clima.parquet"
    if clima.exists():
        mapping["raw_clima"] = clima

    populacao = Path(raw_populacao_dir) / "populacao.parquet"
    if populacao.exists():
        mapping["raw_populacao"] = populacao

    return mapping


def load_raw_to_duckdb(
    duckdb_path: str | Path,
    parquet_map: Mapping[str, str | Path],
) -> dict[str, int]:
    """Carrega cada Parquet como tabela ``raw_*`` no DuckDB (idempotente).

    Args:
        duckdb_path: caminho do arquivo DuckDB (criado se não existir).
        parquet_map: ``{nome_tabela: caminho_parquet}``.

    Returns:
        ``{nome_tabela: nº de linhas}`` após a carga.

    Raises:
        DuckDBLoadError: se um nome de tabela for inválido ou um Parquet não existir.
    """
    import duckdb

    counts: dict[str, int] = {}
    con = duckdb.connect(str(duckdb_path))
    try:
        for table, parquet in parquet_map.items():
            if not _TABLE_NAME_RE.match(table):
                raise DuckDBLoadError(f"Nome de tabela inválido: {table!r}")
            parquet = Path(parquet)
            if not parquet.exists():
                raise DuckDBLoadError(f"Parquet não encontrado: {parquet}")
            # Caminho como literal escapado (vem da config, não de entrada do usuário).
            literal = str(parquet).replace("'", "''")
            con.execute(
                f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_parquet('{literal}')"
            )
            count = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            counts[table] = count
            logger.info("DuckDB carregou %s: %d linhas <- %s", table, count, parquet)
    finally:
        con.close()
    return counts


def run_duckdb_load(
    duckdb_path: str | Path,
    raw_gtfs_dir: Path,
    raw_clima_dir: Path,
    raw_populacao_dir: Path,
) -> dict[str, int]:
    """Descobre os Parquet RAW e carrega tudo no DuckDB. Idempotente."""
    parquet_map = discover_raw_parquets(raw_gtfs_dir, raw_clima_dir, raw_populacao_dir)
    if not parquet_map:
        raise DuckDBLoadError("Nenhum Parquet RAW encontrado para carregar.")
    return load_raw_to_duckdb(duckdb_path, parquet_map)

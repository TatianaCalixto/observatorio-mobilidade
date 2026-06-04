"""Popula um DuckDB com tabelas ``raw_*`` a partir das FIXTURES de teste.

Permite rodar ``dbt build`` (no CI ou em validação local rápida) sem a ingestão real
pesada. É dado mínimo e determinístico, apenas para validar a modelagem — NÃO usar como
dado de produção.

No CI, use uma janela curta (ex.: 1 dia) coberta pela fixture de clima, e passe os mesmos
``data_inicio``/``data_fim`` às vars do dbt.
"""

from __future__ import annotations

import json
import logging
import tempfile
from datetime import date
from pathlib import Path

from ingestion.duckdb_load import run_duckdb_load
from ingestion.gtfs import ingest_gtfs
from ingestion.inmet import ingest_inmet
from ingestion.sidra import ingest_sidra

logger = logging.getLogger(__name__)

#: Diretório de fixtures (tests/fixtures), relativo à raiz do repositório.
FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"


def seed(
    duckdb_path: str | Path,
    data_inicio: date,
    data_fim: date,
    *,
    workdir: str | Path | None = None,
) -> dict[str, int]:
    """Ingere as fixtures e carrega as tabelas ``raw_*`` no DuckDB indicado."""
    work = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="seed_"))
    raw_gtfs = work / "gtfs"
    raw_clima = work / "clima"
    raw_populacao = work / "populacao"

    ingest_gtfs(FIXTURES / "gtfs", raw_gtfs)
    ingest_inmet([FIXTURES / "inmet" / "A701_sample.csv"], raw_clima, data_inicio, data_fim)
    payload = json.loads((FIXTURES / "sidra" / "populacao_sample.json").read_text(encoding="utf-8"))
    ingest_sidra(payload, raw_populacao)

    counts = run_duckdb_load(duckdb_path, raw_gtfs, raw_clima, raw_populacao)
    logger.info("Seed (fixtures) -> %s: %s", duckdb_path, counts)
    return counts


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from ingestion.config import load_settings

    settings = load_settings()
    seed(settings.duckdb_path, settings.data_inicio, settings.data_fim)


if __name__ == "__main__":
    main()

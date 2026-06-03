"""Orquestra a ingestão completa: GTFS + INMET + SIDRA -> RAW Parquet -> DuckDB.

Reprodutível e idempotente. Executável via ``make ingest`` ou
``uv run python -m ingestion.run_all``.
"""

from __future__ import annotations

import logging

from ingestion.config import Settings, load_settings
from ingestion.duckdb_load import run_duckdb_load
from ingestion.gtfs import run_gtfs_ingestion
from ingestion.inmet import run_inmet_ingestion
from ingestion.sidra import run_sidra_ingestion

logger = logging.getLogger(__name__)


def run(settings: Settings) -> dict[str, int]:
    """Roda as três ingestões e a carga no DuckDB. Retorna as contagens das tabelas."""
    settings.ensure_data_dirs()
    logger.info("Janela do projeto: %s a %s", settings.data_inicio, settings.data_fim)

    gtfs = run_gtfs_ingestion(settings.gtfs_sptrans_url, settings.raw_gtfs_dir)
    logger.info("GTFS ingerido: %s", gtfs)

    clima = run_inmet_ingestion(settings.raw_clima_dir, settings.data_inicio, settings.data_fim)
    logger.info("Clima (INMET) ingerido: %d linhas", clima)

    pop = run_sidra_ingestion(settings.raw_populacao_dir)
    logger.info("População (SIDRA) ingerida: %d regiões", pop)

    counts = run_duckdb_load(
        settings.duckdb_path,
        settings.raw_gtfs_dir,
        settings.raw_clima_dir,
        settings.raw_populacao_dir,
    )
    logger.info("DuckDB carregado: %s", counts)
    return counts


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(load_settings())


if __name__ == "__main__":
    main()

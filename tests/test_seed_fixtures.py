"""Testa o seeder de fixtures (ingestion.seed_fixtures) usado pelo CI do dbt."""

from datetime import date
from pathlib import Path

import duckdb

from ingestion.seed_fixtures import seed

JANELA_CI = (date(2025, 6, 1), date(2025, 6, 1))  # 1 dia, coberto pela fixture de clima


def test_seed_cria_tabelas_raw(tmp_path: Path):
    db = tmp_path / "seed.duckdb"
    counts = seed(db, *JANELA_CI, workdir=tmp_path / "raw")

    esperadas = {
        "raw_gtfs_stops",
        "raw_gtfs_routes",
        "raw_gtfs_trips",
        "raw_gtfs_stop_times",
        "raw_gtfs_calendar",
        "raw_gtfs_frequencies",
        "raw_clima",
        "raw_populacao",
    }
    assert esperadas <= set(counts)

    con = duckdb.connect(str(db))
    try:
        tabelas = {r[0] for r in con.execute("show tables").fetchall()}
        assert esperadas <= tabelas
        # 2025-06-01 tem 3 horas na fixture de clima.
        assert con.execute("select count(*) from raw_clima").fetchone()[0] == 3
        assert con.execute("select count(*) from raw_gtfs_calendar").fetchone()[0] == 2
    finally:
        con.close()

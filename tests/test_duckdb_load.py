"""Testes de integração da carga RAW -> DuckDB (ingestion.duckdb_load)."""

from pathlib import Path

import duckdb
import polars as pl
import pytest

from ingestion.duckdb_load import (
    DuckDBLoadError,
    discover_raw_parquets,
    load_raw_to_duckdb,
    run_duckdb_load,
)


def _raw_layout(root: Path) -> tuple[Path, Path, Path]:
    """Cria uma camada RAW mínima (gtfs/clima/populacao) com Parquet pequenos."""
    gtfs, clima, pop = root / "gtfs", root / "clima", root / "populacao"
    for d in (gtfs, clima, pop):
        d.mkdir(parents=True)
    pl.DataFrame({"stop_id": ["1", "2", "3"], "stop_name": ["A", "B", "C"]}).write_parquet(
        gtfs / "stops.parquet"
    )
    pl.DataFrame({"route_id": ["8000-10"], "route_short_name": ["8000-10"]}).write_parquet(
        gtfs / "routes.parquet"
    )
    pl.DataFrame({"data": ["2025-06-01"], "temperatura_c": [18.2]}).write_parquet(
        clima / "clima.parquet"
    )
    pl.DataFrame({"regiao_codigo": ["3550308"], "valor": [11451999]}).write_parquet(
        pop / "populacao.parquet"
    )
    return gtfs, clima, pop


def test_discover_raw_parquets_mapeia_tabelas(tmp_path: Path):
    gtfs, clima, pop = _raw_layout(tmp_path)
    mapping = discover_raw_parquets(gtfs, clima, pop)
    assert set(mapping) == {"raw_gtfs_stops", "raw_gtfs_routes", "raw_clima", "raw_populacao"}


def test_load_cria_tabelas_com_contagens_coerentes(tmp_path: Path):
    gtfs, clima, pop = _raw_layout(tmp_path)
    db = tmp_path / "test.duckdb"
    counts = run_duckdb_load(db, gtfs, clima, pop)
    assert counts == {
        "raw_gtfs_stops": 3,
        "raw_gtfs_routes": 1,
        "raw_clima": 1,
        "raw_populacao": 1,
    }
    # Contagem dentro do DuckDB bate com o Parquet.
    con = duckdb.connect(str(db))
    try:
        tabelas = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        assert {"raw_gtfs_stops", "raw_clima", "raw_populacao"} <= tabelas
        assert con.execute("SELECT count(*) FROM raw_gtfs_stops").fetchone()[0] == 3
    finally:
        con.close()


def test_load_idempotente_nao_duplica(tmp_path: Path):
    gtfs, clima, pop = _raw_layout(tmp_path)
    db = tmp_path / "test.duckdb"
    c1 = run_duckdb_load(db, gtfs, clima, pop)
    c2 = run_duckdb_load(db, gtfs, clima, pop)
    assert c1 == c2
    con = duckdb.connect(str(db))
    try:
        # Reexecutar não duplica linhas (CREATE OR REPLACE).
        assert con.execute("SELECT count(*) FROM raw_gtfs_stops").fetchone()[0] == 3
    finally:
        con.close()


def test_nome_de_tabela_invalido_gera_erro(tmp_path: Path):
    p = tmp_path / "x.parquet"
    pl.DataFrame({"a": [1]}).write_parquet(p)
    with pytest.raises(DuckDBLoadError):
        load_raw_to_duckdb(tmp_path / "db.duckdb", {"raw; DROP TABLE x": p})


def test_parquet_inexistente_gera_erro(tmp_path: Path):
    with pytest.raises(DuckDBLoadError):
        load_raw_to_duckdb(tmp_path / "db.duckdb", {"raw_x": tmp_path / "nao_existe.parquet"})


def test_run_sem_parquets_gera_erro(tmp_path: Path):
    gtfs, clima, pop = tmp_path / "gtfs", tmp_path / "clima", tmp_path / "populacao"
    for d in (gtfs, clima, pop):
        d.mkdir()
    with pytest.raises(DuckDBLoadError):
        run_duckdb_load(tmp_path / "db.duckdb", gtfs, clima, pop)

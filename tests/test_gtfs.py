"""Testes da ingestão GTFS (ingestion.gtfs) com fixture reduzida."""

import zipfile
from pathlib import Path

import polars as pl
import pytest

from ingestion.gtfs import (
    GTFS_TABLES,
    GTFSIngestionError,
    download_gtfs,
    ingest_gtfs,
    read_gtfs_table,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "gtfs"
EXPECTED_COUNTS = {"stops": 3, "routes": 2, "trips": 2, "stop_times": 4}


def test_read_gtfs_table_parsing():
    df = read_gtfs_table(FIXTURE_DIR, "stops")
    assert df.height == 3
    assert df.columns == ["stop_id", "stop_name", "stop_lat", "stop_lon"]
    # Camada RAW: tudo como texto (sem inferência de tipo).
    assert all(dt == pl.String for dt in df.dtypes)
    assert df["stop_id"].to_list() == ["70001", "70002", "70003"]


def test_ingest_gtfs_grava_todas_as_tabelas(tmp_path: Path):
    counts = ingest_gtfs(FIXTURE_DIR, tmp_path)
    assert counts == EXPECTED_COUNTS
    for table in GTFS_TABLES:
        assert (tmp_path / f"{table}.parquet").is_file()


def test_ingest_gtfs_schema_preservado(tmp_path: Path):
    ingest_gtfs(FIXTURE_DIR, tmp_path)
    df = pl.read_parquet(tmp_path / "stop_times.parquet")
    assert df.columns == [
        "trip_id",
        "arrival_time",
        "departure_time",
        "stop_id",
        "stop_sequence",
    ]
    assert all(dt == pl.String for dt in df.dtypes)


def test_ingest_gtfs_idempotente(tmp_path: Path):
    counts1 = ingest_gtfs(FIXTURE_DIR, tmp_path)
    arquivos1 = sorted(p.name for p in tmp_path.glob("*.parquet"))
    dados1 = pl.read_parquet(tmp_path / "stops.parquet")

    counts2 = ingest_gtfs(FIXTURE_DIR, tmp_path)
    arquivos2 = sorted(p.name for p in tmp_path.glob("*.parquet"))
    dados2 = pl.read_parquet(tmp_path / "stops.parquet")

    # Mesmos arquivos (sem duplicar), mesmas contagens e mesmos dados.
    esperados = ["routes.parquet", "stop_times.parquet", "stops.parquet", "trips.parquet"]
    assert arquivos1 == arquivos2 == esperados
    assert counts1 == counts2 == EXPECTED_COUNTS
    assert dados1.equals(dados2)


def test_read_gtfs_table_de_zip(tmp_path: Path):
    zip_path = tmp_path / "gtfs.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for table in GTFS_TABLES:
            zf.write(FIXTURE_DIR / f"{table}.txt", arcname=f"{table}.txt")
    df = read_gtfs_table(zip_path, "routes")
    assert df.height == 2
    assert "route_id" in df.columns


def test_tabela_ausente_gera_erro(tmp_path: Path):
    (tmp_path / "stops.txt").write_text("stop_id\n1\n", encoding="utf-8")
    with pytest.raises(GTFSIngestionError):
        read_gtfs_table(tmp_path, "routes")


def test_origem_invalida_gera_erro(tmp_path: Path):
    arquivo = tmp_path / "qualquer.csv"
    arquivo.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(GTFSIngestionError):
        read_gtfs_table(arquivo, "stops")


def test_download_gtfs_url_vazia_gera_erro(tmp_path: Path):
    with pytest.raises(GTFSIngestionError):
        download_gtfs("", tmp_path / "gtfs.zip")

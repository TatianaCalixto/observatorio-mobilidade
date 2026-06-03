"""Testa a orquestração da ingestão completa (ingestion.run_all) sem rede."""

from datetime import date
from pathlib import Path

import ingestion.run_all as run_all
from ingestion.config import Settings


def _fake_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_inicio=date(2025, 6, 1),
        data_fim=date(2026, 5, 31),
        data_dir=tmp_path,
        raw_dir=tmp_path / "raw",
        staging_dir=tmp_path / "staging",
        raw_gtfs_dir=tmp_path / "raw" / "gtfs",
        raw_clima_dir=tmp_path / "raw" / "clima",
        raw_populacao_dir=tmp_path / "raw" / "populacao",
        duckdb_path=tmp_path / "db.duckdb",
        gtfs_sptrans_url="http://example/gtfs.zip",
        inmet_base_url="",
        sidra_base_url="http://example/sidra",
    )


def test_run_orquestra_fontes_na_ordem(tmp_path: Path, monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        run_all, "run_gtfs_ingestion", lambda url, d: calls.append("gtfs") or {"stops": 1}
    )
    monkeypatch.setattr(run_all, "run_inmet_ingestion", lambda d, i, f: calls.append("inmet") or 10)
    monkeypatch.setattr(run_all, "run_sidra_ingestion", lambda d: calls.append("sidra") or 5)
    monkeypatch.setattr(
        run_all,
        "run_duckdb_load",
        lambda db, g, c, p: calls.append("duck") or {"raw_gtfs_stops": 1},
    )

    counts = run_all.run(_fake_settings(tmp_path))

    assert calls == ["gtfs", "inmet", "sidra", "duck"]
    assert counts == {"raw_gtfs_stops": 1}
    # ensure_data_dirs foi chamado (pastas RAW criadas)
    assert (tmp_path / "raw" / "gtfs").is_dir()

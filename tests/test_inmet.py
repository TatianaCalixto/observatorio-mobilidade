"""Testes da ingestão INMET (ingestion.inmet) com fixture de CSV histórico."""

from datetime import date
from pathlib import Path

import polars as pl
import pytest

from ingestion.inmet import (
    OUTPUT_COLUMNS,
    INMETIngestionError,
    ingest_inmet,
    parse_inmet_csv,
)

FIXTURE = Path(__file__).parent / "fixtures" / "inmet" / "A701_sample.csv"
JANELA = (date(2025, 6, 1), date(2026, 5, 31))


def test_parse_inmet_extrai_metadados_e_metricas():
    df = parse_inmet_csv(FIXTURE)
    assert df.columns == list(OUTPUT_COLUMNS)
    assert df["estacao"].unique().to_list() == ["A701"]
    assert df["uf"].unique().to_list() == ["SP"]
    # Linha 2025-06-01 01:00 -> precip 1.2 / temp 16.8
    linha = df.filter((pl.col("data") == date(2025, 6, 1)) & (pl.col("hora_utc") == "0100 UTC"))
    assert linha["precipitacao_mm"].item() == pytest.approx(1.2)
    assert linha["temperatura_c"].item() == pytest.approx(16.8)


def test_parse_inmet_tipagem_correta():
    df = parse_inmet_csv(FIXTURE)
    assert df.schema["data"] == pl.Date
    assert df.schema["precipitacao_mm"] == pl.Float64
    assert df.schema["temperatura_c"] == pl.Float64


def test_parse_inmet_trata_ausencia_como_nulo():
    df = parse_inmet_csv(FIXTURE)
    linha = df.filter((pl.col("data") == date(2025, 6, 1)) & (pl.col("hora_utc") == "0200 UTC"))
    assert linha["precipitacao_mm"].item() is None
    assert linha["temperatura_c"].item() is None


def test_ingest_inmet_filtra_pela_janela(tmp_path: Path):
    n = ingest_inmet([FIXTURE], tmp_path, *JANELA)
    # Exclui 2025-05-31 (antes) e 2026-06-01 (depois); mantém as 4 linhas na janela.
    assert n == 4
    df = pl.read_parquet(tmp_path / "clima.parquet")
    assert df["data"].min() == date(2025, 6, 1)
    assert df["data"].max() == date(2026, 5, 31)


def test_ingest_inmet_idempotente(tmp_path: Path):
    n1 = ingest_inmet([FIXTURE], tmp_path, *JANELA)
    dados1 = pl.read_parquet(tmp_path / "clima.parquet")
    n2 = ingest_inmet([FIXTURE], tmp_path, *JANELA)
    dados2 = pl.read_parquet(tmp_path / "clima.parquet")
    arquivos = sorted(p.name for p in tmp_path.glob("*.parquet"))
    assert n1 == n2 == 4
    assert arquivos == ["clima.parquet"]
    assert dados1.equals(dados2)


def test_parse_inmet_sem_cabecalho_gera_erro():
    with pytest.raises(INMETIngestionError):
        parse_inmet_csv("REGIÃO:;SE\nUF:;SP\nsem cabecalho de dados aqui\n")


def test_ingest_inmet_sem_fontes_gera_erro(tmp_path: Path):
    with pytest.raises(INMETIngestionError):
        ingest_inmet([], tmp_path, *JANELA)

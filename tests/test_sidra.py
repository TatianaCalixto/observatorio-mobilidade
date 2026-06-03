"""Testes da ingestão IBGE/SIDRA (ingestion.sidra) com resposta mockada."""

from pathlib import Path

import polars as pl
import pytest

from ingestion.sidra import (
    OUTPUT_COLUMNS,
    SidraIngestionError,
    build_sidra_url,
    ingest_sidra,
    parse_sidra_json,
)

# Resposta SIDRA mockada: cabeçalho de rótulos + 2 municípios (Censo 2022).
MOCK_PAYLOAD = [
    {
        "NC": "Nível Territorial (Código)",
        "NN": "Nível Territorial",
        "D1C": "Município (Código)",
        "D1N": "Município",
        "MC": "Unidade de Medida (Código)",
        "MN": "Unidade de Medida",
        "V": "Valor",
    },
    {
        "NC": "6",
        "NN": "Município",
        "D1C": "3550308",
        "D1N": "São Paulo - SP",
        "MC": "45",
        "MN": "Pessoas",
        "V": "11451245",
    },
    {
        "NC": "6",
        "NN": "Município",
        "D1C": "3509502",
        "D1N": "Campinas - SP",
        "MC": "45",
        "MN": "Pessoas",
        "V": "...",
    },
]


def test_parse_sidra_schema_e_valores():
    df = parse_sidra_json(MOCK_PAYLOAD)
    assert df.columns == list(OUTPUT_COLUMNS)
    assert df.height == 2
    assert df.schema["valor"] == pl.Int64
    assert df["regiao_codigo"].to_list() == ["3550308", "3509502"]
    assert df["valor"].to_list() == [11451245, None]  # "..." vira nulo


def test_parse_sidra_payload_vazio_gera_erro():
    with pytest.raises(SidraIngestionError):
        parse_sidra_json([])


def test_parse_sidra_so_cabecalho_gera_erro():
    with pytest.raises(SidraIngestionError):
        parse_sidra_json([MOCK_PAYLOAD[0]])


def test_ingest_sidra_grava_parquet(tmp_path: Path):
    n = ingest_sidra(MOCK_PAYLOAD, tmp_path)
    assert n == 2
    df = pl.read_parquet(tmp_path / "populacao.parquet")
    assert df.columns == list(OUTPUT_COLUMNS)


def test_ingest_sidra_idempotente(tmp_path: Path):
    n1 = ingest_sidra(MOCK_PAYLOAD, tmp_path)
    dados1 = pl.read_parquet(tmp_path / "populacao.parquet")
    n2 = ingest_sidra(MOCK_PAYLOAD, tmp_path)
    dados2 = pl.read_parquet(tmp_path / "populacao.parquet")
    arquivos = sorted(p.name for p in tmp_path.glob("*.parquet"))
    assert n1 == n2 == 2
    assert arquivos == ["populacao.parquet"]
    assert dados1.equals(dados2)


def test_build_sidra_url():
    url = build_sidra_url(4714, 6, "3550308", 93, 2022)
    assert url == "https://apisidra.ibge.gov.br/values/t/4714/n6/3550308/v/93/p/2022"

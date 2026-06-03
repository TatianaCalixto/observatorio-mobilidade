"""Suíte consolidada de validação de ingestão: schema por fonte + idempotência."""

from datetime import date
from pathlib import Path

import polars as pl
import pytest

from ingestion.gtfs import GTFS_TABLES, ingest_gtfs
from ingestion.inmet import ingest_inmet, parse_inmet_csv
from ingestion.sidra import ingest_sidra, parse_sidra_json
from ingestion.validation import (
    CLIMA_SCHEMA,
    POPULACAO_SCHEMA,
    SchemaValidationError,
    validate_required_columns,
    validate_schema,
)

FIXTURES = Path(__file__).parent / "fixtures"
GTFS_FIX = FIXTURES / "gtfs"
INMET_FIX = FIXTURES / "inmet" / "A701_sample.csv"
JANELA = (date(2025, 6, 1), date(2026, 5, 31))
SIDRA_PAYLOAD = [
    {"NN": "Nível", "D1C": "Mun (Cod)", "D1N": "Município", "MN": "Unidade", "V": "Valor"},
    {
        "NN": "Município",
        "D1C": "3550308",
        "D1N": "São Paulo - SP",
        "MN": "Pessoas",
        "V": "11451999",
    },
]


# --- utilitários de validação ---------------------------------------------------------
def test_validate_required_columns_ok():
    df = pl.DataFrame({"a": [1], "b": [2]})
    assert validate_required_columns(df, {"a"}, source="x") is df


def test_validate_required_columns_ausente_gera_erro():
    df = pl.DataFrame({"a": [1]})
    with pytest.raises(SchemaValidationError) as exc:
        validate_required_columns(df, {"a", "b"}, source="fonte")
    assert "b" in str(exc.value)


def test_validate_schema_tipo_divergente_gera_erro():
    df = pl.DataFrame({"valor": [1.0]})  # Float64, esperado Int64
    with pytest.raises(SchemaValidationError):
        validate_schema(df, {"valor": pl.Int64}, source="pop")


# --- schema por fonte -----------------------------------------------------------------
def test_schema_gtfs_valido(tmp_path: Path):
    ingest_gtfs(GTFS_FIX, tmp_path)
    for table in GTFS_TABLES:
        pl.read_parquet(tmp_path / f"{table}.parquet")  # não levanta


def test_schema_gtfs_origem_alterada_falha_claramente(tmp_path: Path):
    # stops.txt SEM a coluna obrigatória stop_lat -> deve falhar na ingestão.
    (tmp_path / "stops.txt").write_text("stop_id,stop_name,stop_lon\n1,A,-46.6\n", encoding="utf-8")
    for table in ("routes", "trips", "stop_times"):
        (tmp_path / f"{table}.txt").write_bytes((GTFS_FIX / f"{table}.txt").read_bytes())
    with pytest.raises(SchemaValidationError) as exc:
        ingest_gtfs(tmp_path, tmp_path / "out")
    assert "stop_lat" in str(exc.value)


def test_schema_clima_valido_e_quebrado():
    df = parse_inmet_csv(INMET_FIX)
    validate_schema(df, CLIMA_SCHEMA, source="clima")  # ok
    quebrado = df.with_columns(pl.col("data").cast(pl.String))
    with pytest.raises(SchemaValidationError):
        validate_schema(quebrado, CLIMA_SCHEMA, source="clima")


def test_schema_populacao_valido_e_quebrado():
    df = parse_sidra_json(SIDRA_PAYLOAD)
    validate_schema(df, POPULACAO_SCHEMA, source="populacao")  # ok
    quebrado = df.with_columns(pl.col("valor").cast(pl.Float64))
    with pytest.raises(SchemaValidationError):
        validate_schema(quebrado, POPULACAO_SCHEMA, source="populacao")


# --- idempotência consolidada ---------------------------------------------------------
def test_idempotencia_consolidada_das_fontes(tmp_path: Path):
    resultados = {}
    for fonte, primeira, segunda in (
        (
            "gtfs",
            ingest_gtfs(GTFS_FIX, tmp_path / "gtfs"),
            ingest_gtfs(GTFS_FIX, tmp_path / "gtfs"),
        ),
        (
            "clima",
            ingest_inmet([INMET_FIX], tmp_path / "clima", *JANELA),
            ingest_inmet([INMET_FIX], tmp_path / "clima", *JANELA),
        ),
        (
            "populacao",
            ingest_sidra(SIDRA_PAYLOAD, tmp_path / "pop"),
            ingest_sidra(SIDRA_PAYLOAD, tmp_path / "pop"),
        ),
    ):
        resultados[fonte] = (primeira, segunda)
        assert primeira == segunda, f"{fonte} não é idempotente"

    # Nenhuma fonte gerou arquivos duplicados (1 parquet de clima/pop; 4 do gtfs).
    assert len(list((tmp_path / "gtfs").glob("*.parquet"))) == len(GTFS_TABLES)
    assert len(list((tmp_path / "clima").glob("*.parquet"))) == 1
    assert len(list((tmp_path / "pop").glob("*.parquet"))) == 1

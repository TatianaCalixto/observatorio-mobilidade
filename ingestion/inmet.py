"""Ingestão de dados climáticos do INMET para a camada RAW em Parquet.

Fonte: arquivos CSV históricos do INMET (portal de dados históricos), um por estação/ano.
Formato peculiar:

* As **8 primeiras linhas** são metadados da estação (``REGIÃO``, ``UF``, ``ESTAÇÃO``,
  ``CODIGO (WMO)``, ``LATITUDE`` …), no formato ``CHAVE:;valor``.
* Em seguida vem o cabeçalho dos dados (linha que começa com ``Data;``) e as medições
  **horárias**, com separador ``;`` e **vírgula decimal**. Ausências aparecem como vazio
  ou ``-9999``.

Esta ingestão extrai data, hora, estação e as métricas de interesse (precipitação e
temperatura), tipando-as e limitando à janela temporal do projeto. Diferente do GTFS
(camada RAW como texto), aqui a tarefa pede colunas **tipadas** (data + métricas).
"""

from __future__ import annotations

import logging
import tempfile
import unicodedata
import zipfile
from collections.abc import Iterable
from datetime import date
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

#: Estação automática canônica de São Paulo (Mirante de Santana).
ESTACAO_SP_PADRAO = "A701"

#: Sentinela de ausência usada pelo INMET.
MISSING_SENTINELS = {"", "-9999", "-9999.0", "null"}

#: Schema de saída da camada RAW de clima.
OUTPUT_COLUMNS = (
    "data",
    "hora_utc",
    "estacao",
    "uf",
    "precipitacao_mm",
    "temperatura_c",
)


class INMETIngestionError(RuntimeError):
    """Erro na ingestão do INMET (formato inesperado, coluna ausente)."""


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).upper().strip()


def _read_text(content: str | bytes | Path) -> str:
    if isinstance(content, str):
        return content
    data = content.read_bytes() if isinstance(content, Path) else content
    # Arquivos reais do INMET são latin-1; fixtures/outros podem ser utf-8.
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def _split_metadata_and_data(text: str) -> tuple[dict[str, str], str]:
    """Separa as linhas de metadados do bloco de dados (a partir do cabeçalho 'Data;')."""
    lines = text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if _strip_accents(line).startswith("DATA;"):
            header_idx = i
            break
    if header_idx is None:
        raise INMETIngestionError("Cabeçalho de dados ('Data;...') não encontrado no CSV INMET.")

    metadata: dict[str, str] = {}
    for line in lines[:header_idx]:
        if ";" in line:
            key, _, value = line.partition(";")
            metadata[_strip_accents(key.rstrip(":"))] = value.strip()

    data_block = "\n".join(lines[header_idx:])
    return metadata, data_block


def _find_column(columns: Iterable[str], *needles: str) -> str | None:
    """Retorna a primeira coluna cujo nome (sem acento) contém todos os ``needles``."""
    for col in columns:
        normalized = _strip_accents(col)
        if all(_strip_accents(n) in normalized for n in needles):
            return col
    return None


def _to_float(col: str) -> pl.Expr:
    return (
        pl.col(col)
        .str.strip_chars()
        .replace(list(MISSING_SENTINELS), [None] * len(MISSING_SENTINELS))
        .str.replace(",", ".")
        .cast(pl.Float64, strict=False)
    )


def parse_inmet_csv(content: str | bytes | Path) -> pl.DataFrame:
    """Parseia um CSV histórico do INMET em um DataFrame tipado e horário.

    Returns:
        DataFrame com colunas :data:`OUTPUT_COLUMNS` (``data`` como Date, métricas Float).

    Raises:
        INMETIngestionError: se o cabeçalho ou colunas essenciais não forem encontrados.
    """
    text = _read_text(content)
    metadata, data_block = _split_metadata_and_data(text)

    raw = pl.read_csv(
        data_block.encode("utf-8"),
        separator=";",
        infer_schema_length=0,
        truncate_ragged_lines=True,
    )

    col_data = _find_column(raw.columns, "DATA")
    col_hora = _find_column(raw.columns, "HORA")
    col_precip = _find_column(raw.columns, "PRECIPITA")
    col_temp = _find_column(raw.columns, "TEMPERATURA DO AR", "BULBO SECO") or _find_column(
        raw.columns, "TEMPERATURA DO AR"
    )
    if col_data is None or col_precip is None or col_temp is None:
        raise INMETIngestionError(
            "Colunas essenciais ausentes no CSV INMET "
            f"(data={col_data!r}, precip={col_precip!r}, temp={col_temp!r})."
        )

    estacao = metadata.get("CODIGO (WMO)") or metadata.get("CODIGO") or ""
    uf = metadata.get("UF") or ""

    df = raw.select(
        pl.col(col_data)
        .str.replace_all("/", "-")
        .str.to_date("%Y-%m-%d", strict=False)
        .alias("data"),
        (pl.col(col_hora) if col_hora else pl.lit(None)).alias("hora_utc"),
        pl.lit(estacao).alias("estacao"),
        pl.lit(uf).alias("uf"),
        _to_float(col_precip).alias("precipitacao_mm"),
        _to_float(col_temp).alias("temperatura_c"),
    )
    return df


def ingest_inmet(
    sources: Iterable[str | bytes | Path],
    dest_dir: str | Path,
    data_inicio: date,
    data_fim: date,
    *,
    filename: str = "clima.parquet",
) -> int:
    """Parseia CSVs do INMET, filtra pela janela [data_inicio, data_fim] e grava Parquet.

    Idempotente: grava um único ``<dest_dir>/<filename>``, sobrescrevendo. Linhas sem data
    válida ou fora da janela são descartadas.

    Returns:
        Número de linhas (horárias) gravadas.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    frames = [parse_inmet_csv(src) for src in sources]
    if not frames:
        raise INMETIngestionError("Nenhuma fonte INMET fornecida.")

    df = pl.concat(frames, how="vertical")
    df = df.filter(
        pl.col("data").is_not_null()
        & (pl.col("data") >= data_inicio)
        & (pl.col("data") <= data_fim)
    ).sort("data", "hora_utc")

    out_path = dest_dir / filename
    df.write_parquet(out_path)
    logger.info("INMET: %d linhas (%s..%s) -> %s", df.height, data_inicio, data_fim, out_path)
    return df.height


def download_inmet_year(year: int, dest_zip: str | Path, *, timeout: float = 180.0) -> Path:
    """Baixa o zip histórico anual do INMET (todas as estações) para ``dest_zip``.

    URL padrão: ``https://portal.inmet.gov.br/uploads/dadoshistoricos/{year}.zip``.
    Separado do parsing (testável sem rede).
    """
    from ingestion.http import download_file

    url = f"https://portal.inmet.gov.br/uploads/dadoshistoricos/{year}.zip"
    return download_file(url, dest_zip, timeout=timeout)


def extract_station_csv(zip_path: str | Path, station: str = ESTACAO_SP_PADRAO) -> bytes:
    """Extrai o CSV de uma estação (por código, ex.: ``A701``) de um zip anual do INMET."""
    with zipfile.ZipFile(zip_path) as zf:
        matches = [n for n in zf.namelist() if station in n and n.upper().endswith(".CSV")]
        if not matches:
            raise INMETIngestionError(f"Estação {station} não encontrada em {zip_path}.")
        return zf.read(matches[0])


def run_inmet_ingestion(
    raw_clima_dir: str | Path,
    data_inicio: date,
    data_fim: date,
    *,
    station: str = ESTACAO_SP_PADRAO,
    workdir: str | Path | None = None,
) -> int:
    """Pipeline real: baixa os zips anuais que cobrem a janela, extrai a estação e ingere.

    Reprodutível: cobre todos os anos entre ``data_inicio`` e ``data_fim``, baixa cada zip,
    extrai o CSV da estação e grava o Parquet de clima filtrado à janela. Idempotente.
    """
    work = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="inmet_"))
    work.mkdir(parents=True, exist_ok=True)

    csvs: list[bytes] = []
    for year in range(data_inicio.year, data_fim.year + 1):
        zip_path = download_inmet_year(year, work / f"{year}.zip")
        csvs.append(extract_station_csv(zip_path, station))

    return ingest_inmet(csvs, raw_clima_dir, data_inicio, data_fim)

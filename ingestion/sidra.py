"""Ingestão de população (IBGE/SIDRA) para a camada RAW em Parquet.

A API SIDRA (``https://apisidra.ibge.gov.br``) devolve um JSON em que o **primeiro
elemento é um cabeçalho** (rótulos legíveis das colunas) e os demais são as linhas de
dados, com chaves padronizadas:

* ``NC`` / ``NN``  -> nível territorial (código / nome)
* ``D1C`` / ``D1N`` -> primeira dimensão (território, ao usar ``/n{nivel}/{geo}``)
* ``MC`` / ``MN``  -> unidade de medida
* ``V``            -> valor (string; ``"..."`` / ``"-"`` indicam ausência)

Esta ingestão normaliza isso para um schema estável, com a **chave de região**
(``regiao_codigo``, o código IBGE) usada para casar com os marts adiante.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from urllib.parse import quote

import polars as pl

logger = logging.getLogger(__name__)

#: Sentinelas de ausência usadas pela SIDRA.
MISSING_SENTINELS = {"...", "-", "..", "X", ""}

#: Schema de saída da camada RAW de população.
OUTPUT_COLUMNS = ("nivel", "regiao_codigo", "regiao_nome", "valor", "unidade")


class SidraIngestionError(RuntimeError):
    """Erro na ingestão da SIDRA (payload inesperado)."""


def parse_sidra_json(payload: Sequence[Mapping[str, str]]) -> pl.DataFrame:
    """Converte o JSON da SIDRA (cabeçalho + linhas) em um DataFrame tipado.

    Args:
        payload: lista de dicts; ``payload[0]`` é o cabeçalho de rótulos e é descartado.

    Returns:
        DataFrame com colunas :data:`OUTPUT_COLUMNS` (``valor`` como Int64).

    Raises:
        SidraIngestionError: se o payload estiver vazio ou sem linhas de dados.
    """
    if not payload or len(payload) < 2:
        raise SidraIngestionError(
            "Payload SIDRA vazio ou sem linhas de dados (esperado cabeçalho + dados)."
        )

    registros = payload[1:]  # descarta o cabeçalho de rótulos
    rows = [
        {
            "nivel": r.get("NN"),
            "regiao_codigo": r.get("D1C"),
            "regiao_nome": r.get("D1N"),
            "valor_raw": r.get("V"),
            "unidade": r.get("MN"),
        }
        for r in registros
    ]

    df = pl.DataFrame(
        rows,
        schema={
            c: pl.String for c in ("nivel", "regiao_codigo", "regiao_nome", "valor_raw", "unidade")
        },
    )
    df = df.with_columns(
        pl.col("valor_raw")
        .str.strip_chars()
        .replace(list(MISSING_SENTINELS), [None] * len(MISSING_SENTINELS))
        .cast(pl.Int64, strict=False)
        .alias("valor")
    ).select(OUTPUT_COLUMNS)
    return df


def build_sidra_url(
    table: str | int,
    level: str | int,
    geo: str,
    variable: str | int,
    period: str | int,
    *,
    base_url: str = "https://apisidra.ibge.gov.br",
) -> str:
    """Monta a URL da API SIDRA (``/values/t/{t}/n{nivel}/{geo}/v/{var}/p/{periodo}``).

    ``geo`` pode conter espaços (ex.: ``"in n3 35"`` = municípios da UF 35); eles são
    codificados para ``%20``.
    """
    geo_enc = quote(str(geo), safe="")
    return f"{base_url}/values/t/{table}/n{level}/{geo_enc}/v/{variable}/p/{period}"


def fetch_sidra(url: str, *, timeout: float = 60.0) -> list[dict[str, str]]:
    """Consulta a API SIDRA e devolve o JSON (lista de dicts)."""
    import httpx

    from ingestion.http import USER_AGENT

    with httpx.Client(
        timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json()


def ingest_sidra(
    payload: Sequence[Mapping[str, str]],
    dest_dir: str | Path,
    *,
    filename: str = "populacao.parquet",
) -> int:
    """Parseia o payload SIDRA e grava o Parquet de população (idempotente).

    Returns:
        Número de linhas (regiões) gravadas.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    df = parse_sidra_json(payload)
    out_path = dest_dir / filename
    df.write_parquet(out_path)
    logger.info("SIDRA: %d regioes -> %s", df.height, out_path)
    return df.height


def run_sidra_ingestion(
    dest_dir: str | Path,
    *,
    table: str | int = 4714,
    level: str | int = 6,
    geo: str = "in n3 35",
    variable: str | int = 93,
    period: str | int = 2022,
    base_url: str = "https://apisidra.ibge.gov.br",
) -> int:
    """Pipeline real: consulta a SIDRA e grava o Parquet de população. Idempotente.

    Default: população residente (Censo 2022, variável 93) por município (nível 6) do
    estado de São Paulo (``in n3 35``).
    """
    url = build_sidra_url(table, level, geo, variable, period, base_url=base_url)
    payload = fetch_sidra(url)
    return ingest_sidra(payload, dest_dir)

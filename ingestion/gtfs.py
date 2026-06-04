"""Ingestão do GTFS estático (SPTrans) para a camada RAW em Parquet.

O GTFS é um conjunto de arquivos texto (CSV) dentro de um ``.zip``. Aqui ingerimos as
tabelas principais usadas pelo projeto (paradas, linhas, viagens e horários planejados),
gravando cada uma como Parquet em ``data/raw/gtfs/``.

Princípios da camada RAW:

* **Fidelidade**: todas as colunas são lidas como texto (sem inferência de tipo). A
  tipagem acontece depois, na camada *staging* do dbt. Isso evita que IDs como
  ``route_id`` virem números e percam zeros à esquerda.
* **Idempotência**: a gravação sobrescreve o Parquet de cada tabela (um arquivo por
  tabela). Reexecutar não duplica dados.

O *download* do feed real (``download_gtfs``) depende da URL/credencial da fonte e é
separado do parsing/gravação (que é testável com uma fixture reduzida, sem rede).
"""

from __future__ import annotations

import io
import logging
import tempfile
import zipfile
from collections.abc import Iterable
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

#: Tabelas do GTFS ingeridas pelo projeto. ``calendar`` e ``frequencies`` sustentam o
#: modelo de oferta planejada (datar viagens e derivar nº de partidas/headway) — ver DEC-006.
GTFS_TABLES: tuple[str, ...] = (
    "stops",
    "routes",
    "trips",
    "stop_times",
    "calendar",
    "frequencies",
)


class GTFSIngestionError(RuntimeError):
    """Erro na ingestão do GTFS (arquivo ausente ou ilegível)."""


def _read_csv_text(data: bytes | str) -> pl.DataFrame:
    """Lê um CSV GTFS com todas as colunas como texto (fidelidade da camada RAW)."""
    buffer = data.encode("utf-8") if isinstance(data, str) else data
    return pl.read_csv(io.BytesIO(buffer), infer_schema_length=0)


def read_gtfs_table(source: str | Path, table: str) -> pl.DataFrame:
    """Lê uma tabela GTFS (``<table>.txt``) de um diretório ou de um ``.zip``.

    Args:
        source: diretório com os ``.txt`` do GTFS, ou caminho de um ``.zip``.
        table: nome da tabela sem extensão (ex.: ``"stops"``).

    Raises:
        GTFSIngestionError: se a tabela não existir na origem.
    """
    source = Path(source)
    filename = f"{table}.txt"

    if source.is_dir():
        path = source / filename
        if not path.exists():
            raise GTFSIngestionError(f"Tabela GTFS ausente: {path}")
        return _read_csv_text(path.read_bytes())

    if source.is_file() and source.suffix == ".zip":
        with zipfile.ZipFile(source) as zf:
            if filename not in zf.namelist():
                raise GTFSIngestionError(f"Tabela GTFS ausente no zip: {filename}")
            return _read_csv_text(zf.read(filename))

    raise GTFSIngestionError(
        f"Origem GTFS inválida: {source} (esperado diretório com .txt ou arquivo .zip)."
    )


def ingest_gtfs(
    source: str | Path,
    dest_dir: str | Path,
    tables: Iterable[str] = GTFS_TABLES,
) -> dict[str, int]:
    """Lê as tabelas GTFS da origem e grava cada uma como Parquet em ``dest_dir``.

    Idempotente: cada tabela é gravada em ``<dest_dir>/<table>.parquet``, sobrescrevendo
    a versão anterior. Reexecutar não cria arquivos novos nem duplica linhas.

    Args:
        source: diretório com ``.txt`` do GTFS, ou caminho de um ``.zip``.
        dest_dir: diretório de destino da camada RAW (ex.: ``data/raw/gtfs``).
        tables: tabelas a ingerir (default: :data:`GTFS_TABLES`).

    Returns:
        Mapa ``{tabela: nº de linhas}`` ingeridas.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    from ingestion.validation import GTFS_REQUIRED_COLUMNS, validate_required_columns

    counts: dict[str, int] = {}
    for table in tables:
        df = read_gtfs_table(source, table)
        if table in GTFS_REQUIRED_COLUMNS:
            validate_required_columns(df, GTFS_REQUIRED_COLUMNS[table], source=f"gtfs:{table}")
        out_path = dest_dir / f"{table}.parquet"
        df.write_parquet(out_path)
        counts[table] = df.height
        logger.info("GTFS %s: %d linhas -> %s", table, df.height, out_path)

    logger.info("GTFS ingestão concluída: %s", counts)
    return counts


def download_gtfs(url: str, dest_zip: str | Path, *, timeout: float = 60.0) -> Path:
    """Baixa o feed GTFS (``.zip``) de ``url`` para ``dest_zip``.

    Separado do parsing porque depende da URL/credencial da fonte (SPTrans). Importa
    ``httpx`` localmente para manter o parsing testável sem dependência de rede.

    Raises:
        GTFSIngestionError: se a URL estiver vazia/não configurada.
    """
    if not url:
        raise GTFSIngestionError("URL do GTFS não configurada (GTFS_SPTRANS_URL vazio no .env).")
    from ingestion.http import download_file

    return download_file(url, dest_zip, timeout=timeout)


def run_gtfs_ingestion(
    url: str,
    dest_dir: str | Path,
    *,
    tables: Iterable[str] = GTFS_TABLES,
    workdir: str | Path | None = None,
) -> dict[str, int]:
    """Pipeline real: baixa o feed GTFS de ``url`` e ingere as tabelas em ``dest_dir``.

    Idempotente (a gravação sobrescreve cada Parquet). Retorna ``{tabela: nº de linhas}``.
    """
    work = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="gtfs_"))
    work.mkdir(parents=True, exist_ok=True)
    zip_path = download_gtfs(url, work / "gtfs.zip")
    return ingest_gtfs(zip_path, dest_dir, tables)

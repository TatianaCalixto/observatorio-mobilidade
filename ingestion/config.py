"""Configuração central do projeto (paths das camadas, URLs das fontes, janela de datas).

Os valores vêm de variáveis de ambiente / arquivo ``.env`` (carregado via
``python-dotenv``). As únicas variáveis **obrigatórias** são a janela temporal do
projeto (``DATA_INICIO`` / ``DATA_FIM``); as demais têm defaults sensatos derivados da
raiz do repositório. Veja ``.env.example`` para a lista completa.

Uso típico::

    from ingestion.config import load_settings
    settings = load_settings()          # lê o .env da raiz
    print(settings.data_inicio, settings.raw_gtfs_dir)

Em testes, passe um mapping explícito para isolar do ambiente do processo::

    load_settings(env={"DATA_INICIO": "2025-06-01", "DATA_FIM": "2026-05-31"})
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import dotenv_values

#: Raiz do repositório (dois níveis acima deste arquivo: ingestion/config.py -> raiz).
PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: Caminho padrão do arquivo ``.env`` na raiz do projeto.
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"

#: Mirror público do GTFS da SPTrans (Mobility Database, sem token) — ver DEC-005.
GTFS_SPTRANS_MIRROR = (
    "https://storage.googleapis.com/storage/v1/b/mdb-latest/o/"
    "br-sao-paulo-sao-paulo-transporte-sptrans-gtfs-8.zip?alt=media"
)


class ConfigError(RuntimeError):
    """Erro de configuração: variável obrigatória ausente ou valor inválido."""


@dataclass(frozen=True)
class Settings:
    """Configuração imutável do projeto, derivada do ambiente/``.env``."""

    # Janela temporal (obrigatória)
    data_inicio: date
    data_fim: date

    # Caminhos das camadas de dados
    data_dir: Path
    raw_dir: Path
    staging_dir: Path
    raw_gtfs_dir: Path
    raw_clima_dir: Path
    raw_populacao_dir: Path
    duckdb_path: Path

    # URLs/identificadores das fontes (resolvidos nas tarefas de ingestão)
    gtfs_sptrans_url: str
    inmet_base_url: str
    sidra_base_url: str

    def ensure_data_dirs(self) -> None:
        """Cria as pastas das camadas RAW/staging se ainda não existirem."""
        for d in (
            self.raw_dir,
            self.staging_dir,
            self.raw_gtfs_dir,
            self.raw_clima_dir,
            self.raw_populacao_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)


def _require(env: Mapping[str, str | None], key: str) -> str:
    value = env.get(key)
    if value is None or str(value).strip() == "":
        raise ConfigError(
            f"Variável obrigatória ausente ou vazia: {key}. Defina-a no .env (ver .env.example)."
        )
    return str(value).strip()


def _parse_date(value: str, key: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ConfigError(f"{key} deve estar no formato AAAA-MM-DD (recebido: {value!r}).") from exc


def _resolve_env(
    env: Mapping[str, str | None] | None,
    env_file: str | os.PathLike[str] | None,
) -> Mapping[str, str | None]:
    """Monta o mapping de configuração sem mutar ``os.environ``.

    Precedência: variáveis do processo (``os.environ``) sobre o arquivo ``.env``.
    Se ``env`` for fornecido explicitamente, ele é usado como única fonte (testes).
    """
    if env is not None:
        return env
    path = Path(env_file) if env_file is not None else DEFAULT_ENV_FILE
    file_values = dotenv_values(path) if path.exists() else {}
    return {**file_values, **os.environ}


def load_settings(
    *,
    env: Mapping[str, str | None] | None = None,
    env_file: str | os.PathLike[str] | None = None,
) -> Settings:
    """Carrega e valida a configuração do projeto.

    Args:
        env: mapping explícito de variáveis (usado em testes; ignora ``.env``).
        env_file: caminho de um ``.env`` alternativo (default: ``.env`` da raiz).

    Raises:
        ConfigError: quando uma variável obrigatória está ausente ou um valor é inválido.
    """
    cfg = _resolve_env(env, env_file)

    data_inicio = _parse_date(_require(cfg, "DATA_INICIO"), "DATA_INICIO")
    data_fim = _parse_date(_require(cfg, "DATA_FIM"), "DATA_FIM")
    if data_fim < data_inicio:
        raise ConfigError(
            f"DATA_FIM ({data_fim}) não pode ser anterior a DATA_INICIO ({data_inicio})."
        )

    data_dir = Path(cfg.get("DATA_DIR") or (PROJECT_ROOT / "data"))
    raw_dir = data_dir / "raw"
    staging_dir = data_dir / "staging"
    duckdb_path = Path(cfg.get("DUCKDB_PATH") or (PROJECT_ROOT / "mobilidade.duckdb"))

    return Settings(
        data_inicio=data_inicio,
        data_fim=data_fim,
        data_dir=data_dir,
        raw_dir=raw_dir,
        staging_dir=staging_dir,
        raw_gtfs_dir=raw_dir / "gtfs",
        raw_clima_dir=raw_dir / "clima",
        raw_populacao_dir=raw_dir / "populacao",
        duckdb_path=duckdb_path,
        gtfs_sptrans_url=str(cfg.get("GTFS_SPTRANS_URL") or GTFS_SPTRANS_MIRROR).strip(),
        inmet_base_url=str(cfg.get("INMET_BASE_URL") or "").strip(),
        sidra_base_url=str(cfg.get("SIDRA_BASE_URL") or "https://apisidra.ibge.gov.br").strip(),
    )

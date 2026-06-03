"""Testes da configuração central (ingestion.config)."""

from datetime import date
from pathlib import Path

import pytest

from ingestion.config import (
    GTFS_SPTRANS_MIRROR,
    ConfigError,
    Settings,
    load_settings,
)

VALID_ENV = {"DATA_INICIO": "2025-06-01", "DATA_FIM": "2026-05-31"}


def test_load_settings_valida_janela_temporal():
    settings = load_settings(env=dict(VALID_ENV))
    assert isinstance(settings, Settings)
    assert settings.data_inicio == date(2025, 6, 1)
    assert settings.data_fim == date(2026, 5, 31)


def test_paths_das_camadas_sao_derivados():
    settings = load_settings(env=dict(VALID_ENV))
    assert settings.raw_dir == settings.data_dir / "raw"
    assert settings.staging_dir == settings.data_dir / "staging"
    assert settings.raw_gtfs_dir == settings.data_dir / "raw" / "gtfs"
    assert settings.raw_clima_dir == settings.data_dir / "raw" / "clima"
    assert settings.raw_populacao_dir == settings.data_dir / "raw" / "populacao"
    assert settings.duckdb_path.name == "mobilidade.duckdb"


def test_defaults_das_urls_das_fontes():
    settings = load_settings(env=dict(VALID_ENV))
    assert settings.sidra_base_url == "https://apisidra.ibge.gov.br"
    assert settings.gtfs_sptrans_url == GTFS_SPTRANS_MIRROR
    assert settings.inmet_base_url == ""


def test_gtfs_url_pode_ser_sobrescrita():
    env = {**VALID_ENV, "GTFS_SPTRANS_URL": "https://example.com/custom.zip"}
    settings = load_settings(env=env)
    assert settings.gtfs_sptrans_url == "https://example.com/custom.zip"


def test_data_dir_customizado_redireciona_paths(tmp_path: Path):
    env = {**VALID_ENV, "DATA_DIR": str(tmp_path / "dados")}
    settings = load_settings(env=env)
    assert settings.data_dir == tmp_path / "dados"
    assert settings.raw_gtfs_dir == tmp_path / "dados" / "raw" / "gtfs"


@pytest.mark.parametrize("faltante", ["DATA_INICIO", "DATA_FIM"])
def test_variavel_obrigatoria_ausente_gera_erro_claro(faltante: str):
    env = {k: v for k, v in VALID_ENV.items() if k != faltante}
    with pytest.raises(ConfigError) as exc:
        load_settings(env=env)
    assert faltante in str(exc.value)


def test_variavel_obrigatoria_vazia_gera_erro():
    env = {**VALID_ENV, "DATA_INICIO": "   "}
    with pytest.raises(ConfigError):
        load_settings(env=env)


def test_data_em_formato_invalido_gera_erro():
    env = {**VALID_ENV, "DATA_INICIO": "01/06/2025"}
    with pytest.raises(ConfigError) as exc:
        load_settings(env=env)
    assert "DATA_INICIO" in str(exc.value)


def test_data_fim_anterior_a_inicio_gera_erro():
    env = {"DATA_INICIO": "2026-05-31", "DATA_FIM": "2025-06-01"}
    with pytest.raises(ConfigError):
        load_settings(env=env)


def test_carrega_de_arquivo_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Garante que o ambiente do processo não interfira no teste do arquivo.
    for key in ("DATA_INICIO", "DATA_FIM", "DATA_DIR", "DUCKDB_PATH"):
        monkeypatch.delenv(key, raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("DATA_INICIO=2025-06-01\nDATA_FIM=2026-05-31\n", encoding="utf-8")
    settings = load_settings(env_file=env_file)
    assert settings.data_inicio == date(2025, 6, 1)
    assert settings.data_fim == date(2026, 5, 31)


def test_ensure_data_dirs_cria_pastas(tmp_path: Path):
    env = {**VALID_ENV, "DATA_DIR": str(tmp_path / "data")}
    settings = load_settings(env=env)
    settings.ensure_data_dirs()
    assert settings.raw_gtfs_dir.is_dir()
    assert settings.raw_clima_dir.is_dir()
    assert settings.raw_populacao_dir.is_dir()
    assert settings.staging_dir.is_dir()

"""Flow Prefect do Observatório de Mobilidade: ingestão → dbt build → treino.

Reconstrói marts e modelo de ponta a ponta. Tasks de rede têm retries. As etapas
delegam a funções de módulo (``_ingestao`` / ``_dbt_build`` / ``_treino``) para que o
teste possa rodar o flow em **modo reduzido** (injetando stubs) sem rede.

Rodar local: ``uv run python -m orchestration.flow`` (ou via deployment — ver
``orchestration.deployment``).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from prefect import flow, get_run_logger, task

from ingestion.config import Settings, load_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _ingestao(settings: Settings) -> dict[str, int]:  # pragma: no cover - rede
    """Ingestão completa (GTFS + INMET + SIDRA) e carga no DuckDB."""
    from ingestion.run_all import run

    return run(settings)


def _dbt_build() -> None:  # pragma: no cover - subprocess dbt
    """Build dos modelos dbt (staging → intermediate → marts) + testes."""
    subprocess.run(
        [
            sys.executable,
            "-m",
            "dbt.cli.main",
            "build",
            "--project-dir",
            "transform",
            "--profiles-dir",
            "transform",
        ],
        cwd=str(PROJECT_ROOT),
        check=True,
    )


def _treino(settings: Settings) -> str:  # pragma: no cover - treino real
    """Treina (baseline + XGBoost), registra no MLflow e serializa o modelo."""
    import duckdb

    from ml.serialize import salvar_modelo, treinar_modelo_final
    from ml.train import treinar

    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    try:
        treinar(con)
        modelo, metricas = treinar_modelo_final(con)
    finally:
        con.close()
    return str(salvar_modelo(modelo, metricas))


@task(retries=3, retry_delay_seconds=10, log_prints=True)
def task_ingestao(settings: Settings) -> dict[str, int]:
    get_run_logger().info("Ingestão das fontes públicas...")
    return _ingestao(settings)


@task(retries=2, retry_delay_seconds=5, log_prints=True)
def task_dbt_build() -> None:
    get_run_logger().info("dbt build (marts)...")
    _dbt_build()


@task(retries=1, log_prints=True)
def task_treino(settings: Settings) -> str:
    get_run_logger().info("Treino e serialização do modelo...")
    return _treino(settings)


@flow(name="observatorio-pipeline")
def pipeline(settings: Settings | None = None) -> dict[str, Any]:
    """Pipeline completo: ingestão → dbt build → treino. Retorna um resumo."""
    settings = settings or load_settings()
    contagens = task_ingestao(settings)
    task_dbt_build()
    caminho_modelo = task_treino(settings)
    return {"ingestao": contagens, "modelo": caminho_modelo}


if __name__ == "__main__":
    print(pipeline())

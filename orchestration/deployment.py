"""Deployment/schedule do pipeline Prefect.

Define um deployment do flow ``pipeline`` com agendamento **diário** (cron). Para servir
o deployment localmente (e executar runs agendados/manuais)::

    uv run python -m orchestration.deployment        # serve com schedule diário

Disparo manual (com o serve acima rodando em outro terminal)::

    uv run prefect deployment run 'observatorio-pipeline/diario'

Ver ``docs/orquestracao.md``.
"""

from __future__ import annotations

from typing import Any

from orchestration.flow import pipeline

#: Cron do schedule diário (04:00, fuso do servidor).
CRON_DIARIO = "0 4 * * *"
NOME_DEPLOYMENT = "diario"


def criar_deployment() -> Any:
    """Cria o deployment do flow com schedule diário (cron)."""
    return pipeline.to_deployment(name=NOME_DEPLOYMENT, cron=CRON_DIARIO)


def servir() -> None:  # pragma: no cover - processo de longa duração
    """Serve o deployment localmente (bloqueante): executa runs agendados e manuais."""
    pipeline.serve(name=NOME_DEPLOYMENT, cron=CRON_DIARIO)


if __name__ == "__main__":  # pragma: no cover
    servir()

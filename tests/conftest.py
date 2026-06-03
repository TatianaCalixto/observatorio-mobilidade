"""Configuração compartilhada da suíte de testes.

A raiz do repositório é exposta para imports via ``pythonpath = ["."]`` no
``pyproject.toml`` ([tool.pytest.ini_options]). Fixtures comuns vão aqui.
"""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Caminho absoluto da raiz do projeto."""
    return PROJECT_ROOT

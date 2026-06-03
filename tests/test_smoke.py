"""Teste smoke: garante que o ambiente e os pacotes do projeto importam."""

import importlib

import pytest

PROJECT_PACKAGES = ["ingestion", "ml", "app", "analysis"]
CORE_DEPENDENCIES = ["duckdb", "pandas", "polars", "pyarrow", "requests", "httpx", "dotenv"]


@pytest.mark.parametrize("package", PROJECT_PACKAGES)
def test_project_packages_importable(package: str) -> None:
    """Cada pacote do projeto deve ser importável (layout flat na raiz)."""
    module = importlib.import_module(package)
    assert module is not None


@pytest.mark.parametrize("dependency", CORE_DEPENDENCIES)
def test_core_dependencies_importable(dependency: str) -> None:
    """As dependências base da stack devem estar instaladas no ambiente."""
    module = importlib.import_module(dependency)
    assert module is not None

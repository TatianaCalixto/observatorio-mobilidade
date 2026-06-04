"""Teste do flow Prefect (orchestration.flow) em modo reduzido (sem rede)."""

import pytest
from prefect.testing.utilities import prefect_test_harness

import orchestration.flow as flow_mod


@pytest.fixture(scope="module", autouse=True)
def _prefect_harness():
    with prefect_test_harness():
        yield


def test_flow_executa_etapas_na_ordem(monkeypatch):
    ordem: list[str] = []
    monkeypatch.setattr(flow_mod, "load_settings", lambda: "settings-stub")
    monkeypatch.setattr(
        flow_mod, "_ingestao", lambda s: ordem.append("ingestao") or {"raw_gtfs_stops": 1}
    )
    monkeypatch.setattr(flow_mod, "_dbt_build", lambda: ordem.append("dbt"))
    monkeypatch.setattr(flow_mod, "_treino", lambda s: ordem.append("treino") or "modelo.joblib")

    resultado = flow_mod.pipeline()  # settings=None -> usa load_settings (mockado)

    assert ordem == ["ingestao", "dbt", "treino"]
    assert resultado["ingestao"] == {"raw_gtfs_stops": 1}
    assert resultado["modelo"] == "modelo.joblib"

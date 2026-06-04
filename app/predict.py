"""Carregamento do modelo serializado e predição para a UI.

O alvo previsto é a **demanda SIMULADA** (DEC-007) — a página deve sinalizar isso.
``carregar_artefato`` é cacheado pela UI; as funções de feature/predição são testáveis.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl
import streamlit as st

from ml.serialize import DEFAULT_MODEL_PATH, carregar_modelo
from ml.serialize import prever as _prever

#: Snapshot do modelo usado no deploy público (quando o artefato local não existe).
DEPLOY_MODEL_PATH = DEFAULT_MODEL_PATH.parents[2] / "app_data" / "modelo_demanda.joblib"


def carregar_artefato(caminho: str | Path | None = None) -> dict[str, Any]:
    """Carrega o artefato do modelo (joblib). Usa o snapshot de deploy como fallback."""
    if caminho is None:
        caminho = DEFAULT_MODEL_PATH if DEFAULT_MODEL_PATH.exists() else DEPLOY_MODEL_PATH
    return carregar_modelo(caminho)


@st.cache_resource(show_spinner=False)
def get_artefato() -> dict[str, Any]:
    """Artefato do modelo cacheado para a UI."""
    return carregar_artefato()


def montar_features(
    *,
    n_viagens: float,
    iso_dia_semana: int,
    mes: int,
    precipitacao: float,
    temperatura: float,
    choveu: bool,
) -> dict[str, float]:
    """Monta o dicionário de features na convenção do dataset de ML."""
    return {
        "n_viagens": float(n_viagens),
        "iso_dia_semana": int(iso_dia_semana),
        "mes": int(mes),
        "fim_de_semana": 1 if iso_dia_semana >= 6 else 0,
        "precipitacao_total_mm": float(precipitacao),
        "temperatura_media_c": float(temperatura),
        "choveu": 1 if choveu else 0,
    }


def prever_demanda(artefato: dict[str, Any], features: dict[str, float]) -> float:
    """Prevê a demanda (simulada) para uma entrada de features. Retorna float."""
    return float(_prever(artefato, features)[0])


def pontos_sensibilidade(
    artefato: dict[str, Any],
    *,
    n_viagens: float,
    iso_dia_semana: int,
    mes: int,
    temperatura: float,
    precipitacoes: list[float],
) -> pl.DataFrame:
    """Curva de sensibilidade: demanda (simulada) prevista variando a precipitação.

    Mantém as demais features fixas. Retorna colunas ``precipitacao`` e ``demanda``.
    """
    linhas = []
    for p in precipitacoes:
        feats = montar_features(
            n_viagens=n_viagens,
            iso_dia_semana=iso_dia_semana,
            mes=mes,
            precipitacao=p,
            temperatura=temperatura,
            choveu=p > 0,
        )
        linhas.append({"precipitacao": float(p), "demanda": prever_demanda(artefato, feats)})
    return pl.DataFrame(linhas)

"""Carregamento do modelo serializado e predição para a UI.

O alvo previsto é a **demanda SIMULADA** (DEC-007) — a página deve sinalizar isso.
``carregar_artefato`` é cacheado pela UI; as funções de feature/predição são testáveis.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from ml.serialize import DEFAULT_MODEL_PATH, carregar_modelo
from ml.serialize import prever as _prever


def carregar_artefato(caminho: str | Path | None = None) -> dict[str, Any]:
    """Carrega o artefato do modelo (joblib)."""
    return carregar_modelo(caminho or DEFAULT_MODEL_PATH)


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

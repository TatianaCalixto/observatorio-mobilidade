"""Unit tests dos helpers de gráfico (app.charts): entrada → spec Vega-Lite."""

import polars as pl

from app.charts import (
    PALETA,
    grafico_barra,
    grafico_linha,
    grafico_sensibilidade,
    preparar_sazonalidade,
)


def test_grafico_sensibilidade_quantitativo():
    df = pl.DataFrame({"precipitacao": [0.0, 10.0, 20.0], "demanda": [100.0, 90.0, 80.0]})
    spec = grafico_sensibilidade(
        df, "precipitacao", "demanda", titulo_x="Precipitação (mm)", titulo_y="Demanda"
    ).to_dict()
    assert "layer" in spec
    enc = spec["layer"][0]["encoding"]
    assert enc["x"]["field"] == "precipitacao" and enc["x"]["type"] == "quantitative"
    assert enc["x"]["axis"]["title"] == "Precipitação (mm)"


def test_preparar_sazonalidade_ordem_seg_a_dom_e_tipo_dia():
    df = pl.DataFrame(
        {"iso_dia_semana": [7, 1, 6, 3], "media_viagens_dia": [50.0, 100.0, 60.0, 100.0]}
    )
    out = preparar_sazonalidade(df)
    assert out["iso_dia_semana"].to_list() == [1, 3, 6, 7]  # Seg → Dom
    assert out["dia"].to_list() == ["Seg", "Qua", "Sáb", "Dom"]
    assert out["tipo_dia"].to_list() == [
        "Dia útil",
        "Dia útil",
        "Fim de semana",
        "Fim de semana",
    ]


def _serie():
    return pl.DataFrame(
        {"data": ["2025-06-01", "2025-06-02"], "total": [100.0, 80.0]}
    ).with_columns(pl.col("data").str.to_date())


def test_grafico_linha_area_mais_linha_com_eixos():
    spec = grafico_linha(_serie(), "data", "total", titulo_y="Viagens/dia").to_dict()
    assert "layer" in spec and len(spec["layer"]) == 2
    assert {camada["mark"]["type"] for camada in spec["layer"]} == {"area", "line"}
    enc = spec["layer"][0]["encoding"]
    assert enc["x"]["field"] == "data" and enc["x"]["type"] == "temporal"
    assert enc["y"]["field"] == "total"
    assert enc["y"]["axis"]["title"] == "Viagens/dia"
    # tooltip formatado presente
    assert any(t.get("format") == ",.0f" for t in enc["tooltip"])


def test_grafico_barra_cor_semantica():
    df = pl.DataFrame({"condicao": ["com chuva", "sem chuva"], "oferta": [80.0, 100.0]})
    spec = grafico_barra(
        df,
        "condicao",
        "oferta",
        titulo_y="Oferta",
        cor_por="condicao",
        cor_dominio=["com chuva", "sem chuva"],
        cor_faixa=[PALETA["com_chuva"], PALETA["sem_chuva"]],
    ).to_dict()
    assert spec["mark"]["type"] == "bar"
    enc = spec["encoding"]
    assert enc["x"]["field"] == "condicao"
    assert enc["color"]["scale"]["domain"] == ["com chuva", "sem chuva"]
    assert enc["color"]["scale"]["range"] == [PALETA["com_chuva"], PALETA["sem_chuva"]]


def test_grafico_barra_ordem_e_rotulos():
    df = pl.DataFrame({"dia": ["Seg", "Dom"], "v": [10.0, 5.0]})
    spec = grafico_barra(
        df, "dia", "v", titulo_y="V", ordem_x=["Seg", "Dom"], rotulos=True
    ).to_dict()
    assert "layer" in spec  # barras + rótulos de texto
    enc = spec["layer"][0]["encoding"]
    assert enc["x"]["sort"] == ["Seg", "Dom"]
    assert {camada["mark"]["type"] for camada in spec["layer"]} == {"bar", "text"}

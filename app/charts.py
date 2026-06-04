"""Módulo central de gráficos do app (Altair) + paleta semântica.

Escolha de biblioteca: **Altair** — declarativo, já vem com o Streamlit
(``st.altair_chart``) e o gráfico vira um *spec* (Vega-Lite) facilmente testável via
``chart.to_dict()``. Decisão registrada em DEC-008 / ADR-007.

Os helpers padronizam eixos rotulados (com unidade), tooltip formatado e as cores da
marca, e são consumidos por todas as páginas (Visão Geral, KPIs, Previsões).
"""

from __future__ import annotations

import altair as alt
import polars as pl

#: Paleta semântica fixa do app (cor com significado).
PALETA = {
    "marca": "#0E7C7B",  # teal/petróleo — cor principal
    "com_chuva": "#2A6F97",  # azul = com chuva
    "sem_chuva": "#E9A23B",  # âmbar = sem chuva
    "dia_util": "#0E7C7B",  # teal = dia útil
    "fim_de_semana": "#C46A1B",  # âmbar-queimado = fim de semana
    "grade": "#E3E9EA",
}


#: Rótulos PT e ordem dos dias da semana (Seg→Dom) por iso_dia_semana.
DIAS_PT = {1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb", 7: "Dom"}
ORDEM_DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def _pandas(df: pl.DataFrame | object):
    return df.to_pandas() if isinstance(df, pl.DataFrame) else df


def preparar_sazonalidade(df: pl.DataFrame) -> pl.DataFrame:
    """Prepara a sazonalidade para o gráfico: rótulo PT (Seg→Dom) + tipo de dia, ordenado.

    Entrada: colunas ``iso_dia_semana`` e ``media_viagens_dia``. Saída adiciona ``dia``
    (rótulo PT) e ``tipo_dia`` (``Dia útil``/``Fim de semana``), ordenada Seg→Dom.
    """
    return df.with_columns(
        pl.col("iso_dia_semana").replace_strict(DIAS_PT, return_dtype=pl.String).alias("dia"),
        pl.when(pl.col("iso_dia_semana") <= 5)
        .then(pl.lit("Dia útil"))
        .otherwise(pl.lit("Fim de semana"))
        .alias("tipo_dia"),
    ).sort("iso_dia_semana")


def grafico_linha(
    df: pl.DataFrame,
    x: str,
    y: str,
    *,
    titulo_y: str,
    titulo_x: str = "Data",
    formato_y: str = ",.0f",
) -> alt.LayerChart:
    """Série temporal: área preenchida + linha na cor da marca, eixos e tooltip formatados."""
    base = alt.Chart(_pandas(df)).encode(
        x=alt.X(f"{x}:T", axis=alt.Axis(title=titulo_x, format="%b/%Y")),
        y=alt.Y(f"{y}:Q", axis=alt.Axis(title=titulo_y, format="~s")),
        tooltip=[
            alt.Tooltip(f"{x}:T", title=titulo_x, format="%d/%m/%Y"),
            alt.Tooltip(f"{y}:Q", title=titulo_y, format=formato_y),
        ],
    )
    area = base.mark_area(opacity=0.15, color=PALETA["marca"])
    linha = base.mark_line(color=PALETA["marca"], strokeWidth=2)
    return alt.layer(area, linha).properties(height=320)


def grafico_sensibilidade(
    df: pl.DataFrame, x: str, y: str, *, titulo_x: str, titulo_y: str
) -> alt.LayerChart:
    """Curva quantitativa (área + linha com pontos) — ex.: demanda × precipitação."""
    base = alt.Chart(_pandas(df)).encode(
        x=alt.X(f"{x}:Q", axis=alt.Axis(title=titulo_x)),
        y=alt.Y(f"{y}:Q", axis=alt.Axis(title=titulo_y, format="~s")),
        tooltip=[
            alt.Tooltip(f"{x}:Q", title=titulo_x),
            alt.Tooltip(f"{y}:Q", title=titulo_y, format=",.0f"),
        ],
    )
    area = base.mark_area(opacity=0.15, color=PALETA["com_chuva"])
    linha = base.mark_line(color=PALETA["com_chuva"], strokeWidth=2, point=True)
    return alt.layer(area, linha).properties(height=260)


def grafico_barra(
    df: pl.DataFrame,
    x: str,
    y: str,
    *,
    titulo_y: str,
    titulo_x: str = "",
    ordem_x: list[str] | None = None,
    cor_por: str | None = None,
    cor_dominio: list[str] | None = None,
    cor_faixa: list[str] | None = None,
    formato_y: str = ",.0f",
    rotulos: bool = False,
) -> alt.Chart | alt.LayerChart:
    """Barras com cor semântica opcional (``cor_por`` + escala domínio→faixa) e rótulos."""
    if cor_por and cor_dominio and cor_faixa:
        cor = alt.Color(
            f"{cor_por}:N",
            scale=alt.Scale(domain=cor_dominio, range=cor_faixa),
            legend=alt.Legend(title=None, orient="top"),
        )
    else:
        cor = alt.value(PALETA["marca"])

    base = alt.Chart(_pandas(df)).encode(
        x=alt.X(f"{x}:N", sort=ordem_x, axis=alt.Axis(title=titulo_x, labelAngle=0)),
        y=alt.Y(f"{y}:Q", axis=alt.Axis(title=titulo_y, format="~s")),
        tooltip=[
            alt.Tooltip(f"{x}:N", title=titulo_x or x),
            alt.Tooltip(f"{y}:Q", title=titulo_y, format=formato_y),
        ],
    )
    barras = base.mark_bar(color=PALETA["marca"], cornerRadiusEnd=3).encode(color=cor)
    if not rotulos:
        return barras.properties(height=320)

    texto = base.mark_text(dy=-6, color=PALETA["marca"]).encode(
        text=alt.Text(f"{y}:Q", format=formato_y)
    )
    return alt.layer(barras, texto).properties(height=320)

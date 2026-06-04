"""Gera o relatório de insights a partir dos marts (reproduzível).

Lê o DuckDB (somente leitura), coleta os números via ``analysis.queries``, gera gráficos
(PNG em ``docs/img/``) e escreve ``analysis/relatorio_insights.md``. Re-rodar produz os
mesmos números (determinístico).

Uso: ``uv run python -m analysis.gerar_relatorio``
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from analysis.queries import (
    agregado_clima,
    correlacao_clima_oferta,
    linhas_maior_oferta,
    linhas_pior_headway,
    sazonalidade_dia_semana,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMG_DIR = PROJECT_ROOT / "docs" / "img"
RELATORIO = PROJECT_ROOT / "analysis" / "relatorio_insights.md"


def coletar_numeros(con: duckdb.DuckDBPyConnection) -> dict:
    """Coleta os números do relatório a partir dos marts. Determinístico."""
    saz = sazonalidade_dia_semana(con)
    oferta_por_iso = {row["iso_dia_semana"]: row["media_viagens_dia"] for row in saz.to_dicts()}
    util = next((v for k, v in oferta_por_iso.items() if k <= 5), None)
    sab = oferta_por_iso.get(6)
    dom = oferta_por_iso.get(7)

    n_linhas = con.execute("select count(*) from dim_linha").fetchone()[0]
    n_paradas = con.execute("select count(*) from dim_parada").fetchone()[0]
    periodo = con.execute("select min(data), max(data) from dim_tempo").fetchone()

    return {
        "n_linhas": n_linhas,
        "n_paradas": n_paradas,
        "periodo": (str(periodo[0]), str(periodo[1])),
        "oferta_util": util,
        "oferta_sabado": sab,
        "oferta_domingo": dom,
        "sazonalidade": saz.to_dicts(),
        "gargalos": linhas_pior_headway(con, n=5).to_dicts(),
        "maior_oferta": linhas_maior_oferta(con, n=5).to_dicts(),
        "clima": agregado_clima(con).to_dicts(),
        "correlacao": correlacao_clima_oferta(con).to_dicts()[0],
    }


def _tabela_md(linhas: list[dict], colunas: list[tuple[str, str]]) -> str:
    cabecalho = "| " + " | ".join(c[1] for c in colunas) + " |"
    sep = "|" + "|".join("---" for _ in colunas) + "|"
    corpo = ["| " + " | ".join(str(linha[c[0]]) for c in colunas) + " |" for linha in linhas]
    return "\n".join([cabecalho, sep, *corpo])


def render_markdown(n: dict) -> str:
    corr = n["correlacao"]
    o_util = f"{n['oferta_util']:,.0f}"
    o_sab = f"{n['oferta_sabado']:,.0f}"
    o_dom = f"{n['oferta_domingo']:,.0f}"
    pct_dom = f"{(1 - n['oferta_domingo'] / n['oferta_util']) * 100:.0f}"
    cp = corr["corr_precip_oferta"]
    ct = corr["corr_temp_oferta"]

    tbl_saz = _tabela_md(
        n["sazonalidade"],
        [("dia_semana", "Dia"), ("media_viagens_dia", "Oferta média/dia")],
    )
    tbl_garg = _tabela_md(
        n["gargalos"],
        [
            ("route_short_name", "Linha"),
            ("headway_med_min", "Headway médio (min)"),
            ("media_viagens_dia", "Oferta média/dia"),
        ],
    )
    tbl_maior = _tabela_md(
        n["maior_oferta"],
        [
            ("route_short_name", "Linha"),
            ("media_viagens_dia", "Oferta média/dia"),
            ("headway_med_min", "Headway médio (min)"),
        ],
    )
    tbl_clima = _tabela_md(
        n["clima"],
        [
            ("condicao", "Condição"),
            ("n_dias", "Dias"),
            ("oferta_media", "Oferta média/dia"),
            ("headway_med_min", "Headway médio (min)"),
        ],
    )

    return f"""# Relatório de insights — Observatório de Mobilidade

> Reproduzível: gerado por `analysis/gerar_relatorio.py` a partir dos marts dbt.
> Período analisado: **{n["periodo"][0]} a {n["periodo"][1]}** ·
> **{n["n_linhas"]}** linhas · **{n["n_paradas"]}** paradas.

## Pergunta de negócio

> Dá para prever atrasos/demanda no transporte público a partir de fatores como dia da
> semana, clima e linha — e onde estão os principais gargalos da rede?

Como a fonte é o **GTFS estático** (serviço planejado, sem realizado), a métrica central é
a **oferta planejada** — nº de partidas/dia por linha e *headway* (regularidade). Ver
[`docs/metrica_oferta.md`](../docs/metrica_oferta.md).

## Insight 1 — A oferta cai no fim de semana (dia da semana **prediz** a oferta)

A rede planeja **{o_util}** partidas em dias úteis, **{o_sab}** no sábado e
**{o_dom}** no domingo (≈ {pct_dom}% a menos que no dia útil).

![Oferta por dia da semana](../docs/img/oferta_dia_semana.png)

{tbl_saz}

## Insight 2 — Gargalos de regularidade: linhas com *headway* de até 60 min

As piores esperas estão em linhas periféricas/noturnas (headway ~60 min):

{tbl_garg}

No extremo oposto, o **metrô** concentra a alta frequência (headways de poucos minutos):

{tbl_maior}

## Insight 3 — O clima **não** prediz a oferta planejada

Correlação entre clima e oferta diária é praticamente nula:
**precipitação × oferta = {cp}**, **temperatura × oferta = {ct}**.

{tbl_clima}

![Oferta por condição de chuva](../docs/img/oferta_clima.png)

Isso é **esperado e honesto**: o serviço planejado não muda com o tempo. O clima
afetaria a **demanda/atraso realizado** — que não está disponível com GTFS estático.

## Resposta à pergunta de negócio

| Fator | Prediz a oferta planejada? |
|---|---|
| **Linha** | **Sim** — é o maior determinante da oferta/headway. |
| **Dia da semana** | **Sim** — útil > sábado > domingo. |
| **Clima** | **Não** — correlação ≈ 0 com o planejado (afetaria o realizado). |

**Gargalos:** linhas periféricas/noturnas com headway de ~60 min concentram as piores
esperas; o metrô é o oposto (altíssima frequência).
"""


def gerar_graficos(con: duckdb.DuckDBPyConnection, img_dir: Path) -> None:  # pragma: no cover
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    img_dir.mkdir(parents=True, exist_ok=True)

    saz = sazonalidade_dia_semana(con).to_dicts()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([r["dia_semana"] for r in saz], [r["media_viagens_dia"] for r in saz], color="#2a6f97")
    ax.set_title("Oferta planejada média por dia da semana")
    ax.set_ylabel("Partidas/dia")
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(img_dir / "oferta_dia_semana.png", dpi=110)
    plt.close(fig)

    clima = agregado_clima(con).to_dicts()
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar([r["condicao"] for r in clima], [r["oferta_media"] for r in clima], color="#468faf")
    ax.set_title("Oferta planejada média: sem chuva vs com chuva")
    ax.set_ylabel("Partidas/dia")
    fig.tight_layout()
    fig.savefig(img_dir / "oferta_clima.png", dpi=110)
    plt.close(fig)


def main() -> None:
    from ingestion.config import load_settings

    settings = load_settings()
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    try:
        numeros = coletar_numeros(con)
        gerar_graficos(con, IMG_DIR)
    finally:
        con.close()
    RELATORIO.write_text(render_markdown(numeros), encoding="utf-8")
    print(f"Relatório gerado: {RELATORIO}")


if __name__ == "__main__":
    main()
